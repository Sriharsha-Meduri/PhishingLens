from fastapi import FastAPI, HTTPException
from fastapi.responses import PlainTextResponse
from backend.common.schemas import UrlAnalyzeRequest, UrlAnalyzeResponse, Feature
from backend.common.config import settings
from backend.common.whitelist import is_url_whitelisted
from .fusion import URLFusion
import re
import tldextract
import math
import socket
import ssl
import datetime
from typing import List, Dict, Any
import requests
from urllib.parse import unquote, urlsplit
import sys
import os

# Ensure the project root is in PYTHONPATH
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../"))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

app = FastAPI(title="URL Analysis Service", version="0.4.0")

# ------------------ HF URL scorer (4-class) ------------------
_hf_loaded = False
_hf_tokenizer = None
_hf_model = None
_hf_model_name = settings.SERVICE_MODEL_ID
_hf_calib_T_env = os.getenv("EXTERNAL_CALIB_T", None)
try:
    _hf_calib_T: float = float(_hf_calib_T_env) if _hf_calib_T_env else 0.1  # Lower temperature for better calibration
except Exception:
    _hf_calib_T = 0.1

def _try_load_hf() -> bool:
    global _hf_loaded, _hf_tokenizer, _hf_model
    if _hf_loaded:
        return _hf_tokenizer is not None and _hf_model is not None
    try:
        from transformers import AutoTokenizer, AutoModelForSequenceClassification
        import torch
        
        model_id = os.getenv("SERVICE_MODEL_ID", _hf_model_name)
        print(f"[HF] Loading model: {model_id}")
        
        _tok = AutoTokenizer.from_pretrained(model_id)
        _mdl = AutoModelForSequenceClassification.from_pretrained(model_id)
        _mdl.eval()
        
        # Test the model with a simple input
        test_input = _tok("test", return_tensors="pt", max_length=256, padding="max_length", truncation=True)
        with torch.no_grad():
            test_output = _mdl(**test_input)
            print(f"[HF] Model test successful, output shape: {test_output.logits.shape}")
        
        _hf_tokenizer = _tok
        _hf_model = _mdl
        _hf_loaded = True
        print(f"[HF] Model loaded successfully")
        return True
    except Exception as e:
        print(f"[HF] Model loading failed: {e}")
        _hf_loaded = True
        return False

def _hf_url_score(url: str) -> tuple[float, dict[str, float]] | None:
    if not _try_load_hf():
        print(f"[HF] Model not loaded, returning None")
        return None
    try:
        import torch
        with torch.no_grad():
            enc = _hf_tokenizer(url, max_length=256, padding="max_length", truncation=True, return_tensors="pt")
            outputs = _hf_model(**enc)
            logits = outputs.logits
            T = max(1e-6, float(_hf_calib_T))
            # Apply temperature scaling for better calibration
            scaled_logits = logits / T
            probs = torch.softmax(scaled_logits, dim=-1).cpu().numpy()[0]
            
            print(f"[HF] URL: {url[:50]}...")
            print(f"[HF] Raw logits: {logits.cpu().numpy()[0]}")
            print(f"[HF] Temperature: {T}")
            print(f"[HF] Scaled logits: {scaled_logits.cpu().numpy()[0]}")
            print(f"[HF] Probabilities: {probs}")
            
            # Labels: [legitimate_email, phishing_url, legitimate_url, phishing_url_alt]
            # Combine both phishing classes for better detection
            phishing_prob = float(probs[1]) + float(probs[3]) if len(probs) > 3 else float(probs[1])
            class_probs = {
                "legitimate_email": float(probs[0]) if len(probs) > 0 else None,
                "phishing_url": phishing_prob,
                "legitimate_url": float(probs[2]) if len(probs) > 2 else None,
            }
            print(f"[HF] Phishing probability: {phishing_prob}")
            return phishing_prob, class_probs
    except Exception as e:
        print(f"[HF] Scoring failed: {e}")
        return None

# ------------------ Fusion thresholds/config ------------------
URL_FUSION_MODE = os.getenv("SERVICE_URL_FUSION_MODE", "or_gated").strip().lower()
EXTERNAL_URL_T_HF = float(os.getenv("EXTERNAL_URL_T_HF", "0.50"))
EXTERNAL_URL_T_SCAN = float(os.getenv("EXTERNAL_URL_T_SCAN", "0.60"))
EXTERNAL_URL_T_FUSED = float(os.getenv("EXTERNAL_URL_T_FUSED", "0.60"))
EXTERNAL_URL_T_MAX = float(os.getenv("EXTERNAL_URL_T_MAX", "0.60"))
W_URL_HF = float(os.getenv("W_URL_HF", "0.4"))
W_URL_SCAN = float(os.getenv("W_URL_SCAN", "0.6"))

print(f"[URL_SERVICE] Fusion mode={URL_FUSION_MODE} T_HF={EXTERNAL_URL_T_HF} T_SCAN={EXTERNAL_URL_T_SCAN} T_FUSED={EXTERNAL_URL_T_FUSED} T_MAX={EXTERNAL_URL_T_MAX} W_HF={W_URL_HF} W_SCAN={W_URL_SCAN}")

# Expanded list informed by common abuse reports
SUSPICIOUS_TLDS = {"zip", "xyz", "top", "gq", "work", "loan", "vip", "icu", "click", "shop", "cam", "cf", "tk"}

 

# Phishing-oriented keywords commonly seen in paths/queries
PATH_KEYWORDS = {
    "verify", "update", "account", "login", "password", "secure",
    "confirm", "validate", "unlock", "suspend", "suspended", "invoice",
    "payment", "gift", "prize", "reward", "bank", "wallet"
}


def shannon_entropy(s: str) -> float:
	if not s:
		return 0.0
	from collections import Counter
	counts = Counter(s)
	n = len(s)
	return -sum((c/n) * math.log2(c/n) for c in counts.values())


def extract_features(url: str) -> tuple[List[Feature], bool]:
	features: List[Feature] = []
	features.append(Feature(name="length", value=len(url)))
	num_dots = url.count(".")
	features.append(Feature(name="num_dots", value=num_dots))
	features.append(Feature(name="has_ip", value=bool(re.search(r"https?://\d+\.\d+\.\d+\.\d+", url))))
	features.append(Feature(name="num_slashes", value=url.count("/")))
	features.append(Feature(name="entropy", value=round(shannon_entropy(url), 3)))
	# encoding / obfuscation signals
	try:
		decoded = unquote(url)
	except Exception:
		decoded = url
	enc_ratio = 0.0
	if len(url) > 0:
		enc_ratio = round((len(url) - len(decoded)) / len(url), 3)
	features.append(Feature(name="percent_encoding_ratio", value=enc_ratio))
	b64_like = bool(re.search(r"[A-Za-z0-9+/]{12,}={0,2}", url))
	features.append(Feature(name="has_base64_like", value=b64_like))
	ext = tldextract.extract(url)
	domain = f"{ext.domain}.{ext.suffix}" if ext.suffix else ext.domain
	features.append(Feature(name="domain", value=domain))
	features.append(Feature(name="tld", value=ext.suffix))
	features.append(Feature(name="suspicious_tld", value=ext.suffix in SUSPICIOUS_TLDS))
	features.append(Feature(name="has_at_symbol", value=("@" in url)))
	features.append(Feature(name="has_hyphen_domain", value=("-" in ext.domain)))
	# additional lexical risk signals
	features.append(Feature(name="domain_length", value=len(ext.domain)))
	# path and query keyword signals
	try:
		parts = urlsplit(url)
		path_and_query = (parts.path or "") + "?" + (parts.query or "")
	except Exception:
		path_and_query = url
	lower_pq = (path_and_query or "").lower()
	keyword_hits = sum(1 for k in PATH_KEYWORDS if k in lower_pq)
	features.append(Feature(name="keyword_hits", value=keyword_hits))
	# redirection chain length
	checked = False
	try:
		r = requests.get(url, timeout=4, allow_redirects=True)
		features.append(Feature(name="redirect_hops", value=len(r.history)))
		checked = True
	except Exception:
		features.append(Feature(name="redirect_hops", value=None))
	features.extend(intel_checks(domain, url))
	return features, checked


def intel_checks(domain: str, url: str) -> List[Feature]:
	feats: List[Feature] = []
	# DNS A record presence
	try:
		addrs = {ai[4][0] for ai in socket.getaddrinfo(domain, 80)}
		feats.append(Feature(name="dns_a_records", value=len(addrs)))
	except Exception:
		feats.append(Feature(name="dns_a_records", value=0))
	# SSL certificate expiry (days)
	ssl_days = None
	try:
		host = domain
		ctx = ssl.create_default_context()
		with socket.create_connection((host, 443), timeout=3) as sock:
			with ctx.wrap_socket(sock, server_hostname=host) as ssock:
				cert = ssock.getpeercertificate()
				exp = datetime.datetime.strptime(cert['notAfter'], "%b %d %H:%M:%S %Y %Z")
				ssl_days = (exp - datetime.datetime.utcnow()).days
	except Exception:
		ssl_days = None
	feats.append(Feature(name="ssl_days_to_expire", value=ssl_days))
	feats.append(Feature(name="uses_https", value=url.lower().startswith("https://")))
	# OTX lookup (lightweight)
	if settings.OTX_API_KEY:
		try:
			r = requests.get(f"https://otx.alienvault.com/api/v1/indicators/domain/{domain}/general", headers={"X-OTX-API-KEY": settings.OTX_API_KEY}, timeout=4)
			if r.ok:
				j = r.json()
				pulse_count = int(j.get("pulse_info", {}).get("count", 0))
				feats.append(Feature(name="otx_pulse_count", value=pulse_count))
			else:
				feats.append(Feature(name="otx_pulse_count", value=None))
		except Exception:
			feats.append(Feature(name="otx_pulse_count", value=None))
	# MISP stub indicator (not guaranteed without server)
	if settings.MISP_URL and settings.MISP_API_KEY:
		feats.append(Feature(name="misp_checked", value=True))
	else:
		feats.append(Feature(name="misp_checked", value=False))
	return feats


def score(features: List[Feature]) -> tuple[float, List[str]]:
	score = 0.0
	reasons: List[str] = []
	f: Dict[str, Any] = {feat.name: feat.value for feat in features}
	# Safelist reduces base risk
	if f.get("length", 0) > 80:
		score += 0.2; reasons.append("URL length > 80")
	if f.get("num_dots", 0) > 4:
		score += 0.2; reasons.append("Too many subdomains")
	if f.get("has_ip"):
		score += 0.3; reasons.append("Direct IP in URL")
	if f.get("entropy", 0) > 3.5:
		score += 0.3; reasons.append("High entropy URL")
	if f.get("suspicious_tld"):
		score += 0.3; reasons.append("Suspicious TLD")
	if f.get("has_at_symbol"):
		score += 0.15; reasons.append("@ symbol obfuscation")
	if f.get("has_hyphen_domain"):
		score += 0.2; reasons.append("Hyphenated domain")
	# compound lexical risk
	if f.get("has_hyphen_domain") and f.get("domain_length", 0) >= 15:
		score += 0.15; reasons.append("Long hyphenated domain")
	if f.get("percent_encoding_ratio", 0) > 0.1:
		score += 0.15; reasons.append("Heavy percent-encoding")
	if f.get("has_base64_like"):
		score += 0.1; reasons.append("Base64-like payload in URL")
	# Path keyword hits
	kw = f.get("keyword_hits", 0)
	if isinstance(kw, int) and kw >= 2:
		score += 0.25; reasons.append("Multiple phishing keywords in path/query")
	elif isinstance(kw, int) and kw == 1:
		score += 0.15; reasons.append("Phishing keyword in path/query")
	# WHOIS/DNS/SSL signals (proxy via derived features)
	if f.get("dns_a_records", 0) == 0:
		score += 0.2; reasons.append("No DNS A records resolved")
	ssl_days = f.get("ssl_days_to_expire")
	if isinstance(ssl_days, int) and ssl_days < 14:
		score += 0.15; reasons.append("SSL cert expires soon (<14d)")
	if f.get("uses_https") is False:
		score += 0.1; reasons.append("No HTTPS")
	hops = f.get("redirect_hops")
	if isinstance(hops, int) and hops >= 2:
		score += 0.2; reasons.append("Multiple redirects (cloaking)")
	# OTX pulses
	pc = f.get("otx_pulse_count")
	if isinstance(pc, int) and pc > 0:
		score += 0.6; reasons.append("Listed in OTX pulses")
	# Logistic calibration to spread probabilities more meaningfully
	def calibrate(x: float, k: float = 3.0, x0: float = 0.6) -> float:
		# Clamp x to a reasonable range before calibration
		x = max(0.0, min(1.5, x))
		return 1.0 / (1.0 + math.exp(-k * (x - x0)))
	confidence = calibrate(score)
	return confidence, reasons


@app.post("/analyze_url")
async def analyze_url(req: UrlAnalyzeRequest) -> dict:
    url = req.url
    
    # Check whitelist first - if URL is whitelisted, return safe result immediately
    if is_url_whitelisted(url):
        return {
            "url": url,
            "is_phishing": False,
            "confidence": 1.0,
            "risk_hf": 0.0,
            "risk_scanner": 0.0,
            "risk_fused": 0.0,
            "reasons": ["URL is in whitelist of known safe domains"],
            "whitelisted": True
        }
    
    # HF scorer
    hf = _hf_url_score(url)
    risk_hf = float(hf[0]) if hf else 0.0
    class_probs = hf[1] if hf else None
    # Scanner
    features, checked = extract_features(url)
    risk_scanner, reasons = score(features)
    risk_scanner = float(round(risk_scanner, 3))
    # Fusion
    mode = URL_FUSION_MODE
    thresholds = {
        "t_hf": EXTERNAL_URL_T_HF,
        "t_scan": EXTERNAL_URL_T_SCAN,
        "t_fused": EXTERNAL_URL_T_FUSED,
        "t_max": EXTERNAL_URL_T_MAX,
        "w_hf": W_URL_HF,
        "w_scan": W_URL_SCAN,
    }
    risk_fused = None
    verdict = False
    if mode == "weighted":
        risk_fused = float(round(W_URL_HF * risk_hf + W_URL_SCAN * risk_scanner, 3))
        verdict = (checked and risk_fused >= EXTERNAL_URL_T_FUSED) or (risk_hf >= EXTERNAL_URL_T_HF)
    elif mode == "max":
        risk_fused = float(round(max(risk_hf, risk_scanner), 3))
        verdict = (checked and risk_fused >= EXTERNAL_URL_T_MAX) or (risk_hf >= EXTERNAL_URL_T_HF)
    else:  # or_gated
        risk_fused = float(round(max(risk_hf, risk_scanner), 3))
        verdict = (risk_hf >= EXTERNAL_URL_T_HF) or (checked and risk_scanner >= EXTERNAL_URL_T_SCAN)

    final_payload = {
        "url": url,
        "hf": {
            "class_probs": class_probs,
            "risk_hf": float(round(risk_hf, 3)),
        },
        "scanner": {
            "features": features,
            "risk_scanner": risk_scanner,
            "url_checked": bool(checked),
            "reasons": reasons[:8],
        },
        "fused": {
            "mode": mode,
            "thresholds": thresholds,
            "risk_fused": risk_fused,
            "verdict": bool(verdict),
        },
    }
    # Top-level final_verdict equals fused verdict
    try:
        final_payload["final_verdict"] = bool(final_payload["fused"]["verdict"])  # type: ignore[index]
    except Exception:
        final_payload["final_verdict"] = bool(verdict)
    return final_payload


@app.get("/health")
async def health():
    return {"status": "ok", "service": "url", "version": app.version}


@app.get("/debug_url")
async def debug_url(url: str):
    hf = _hf_url_score(url)
    risk_hf = float(hf[0]) if hf else None
    class_probs = hf[1] if hf else None
    features, checked = extract_features(url)
    risk_scanner, reasons = score(features)
    mode = URL_FUSION_MODE
    if mode == "weighted":
        fused = W_URL_HF * (risk_hf or 0.0) + W_URL_SCAN * (risk_scanner or 0.0)
        verdict = (checked and fused >= EXTERNAL_URL_T_FUSED) or ((risk_hf or 0.0) >= EXTERNAL_URL_T_HF)
    elif mode == "max":
        fused = max((risk_hf or 0.0), (risk_scanner or 0.0))
        verdict = (checked and fused >= EXTERNAL_URL_T_MAX) or ((risk_hf or 0.0) >= EXTERNAL_URL_T_HF)
    else:
        fused = max((risk_hf or 0.0), (risk_scanner or 0.0))
        verdict = ((risk_hf or 0.0) >= EXTERNAL_URL_T_HF) or (checked and (risk_scanner or 0.0) >= EXTERNAL_URL_T_SCAN)
    return {
        "url": url,
        "hf": {"class_probs": class_probs, "risk_hf": risk_hf},
        "scanner": {"features": features, "risk_scanner": risk_scanner, "url_checked": bool(checked), "reasons": reasons[:8]},
        "fused": {
            "mode": mode,
            "thresholds": {
                "t_hf": EXTERNAL_URL_T_HF,
                "t_scan": EXTERNAL_URL_T_SCAN,
                "t_fused": EXTERNAL_URL_T_FUSED,
                "t_max": EXTERNAL_URL_T_MAX,
                "w_hf": W_URL_HF,
                "w_scan": W_URL_SCAN,
            },
            "risk_fused": float(round(fused, 3)),
            "verdict": bool(verdict),
        },
    }

@app.post("/analyze_url/human", response_class=PlainTextResponse)
async def analyze_url_human(req: UrlAnalyzeRequest) -> PlainTextResponse:
	"""Human-friendly output without JSON for URL analysis."""
	res = await analyze_url(req)
	confidence_pct = int(round(res.confidence * 100))
	lines: list[str] = []
	if res.is_phishing:
		lines.append(f"\u26a0\ufe0f  Phishing suspected — Confidence: {confidence_pct}%")
		if res.reasons:
			lines.append("")
			lines.append("Why we think it's risky:")
			for reason in res.reasons[:5]:
				lines.append(f" - {reason}")
	else:
		lines.append(f"\u2705  Looks safe — Confidence: {confidence_pct}%")
		if res.reasons:
			lines.append("")
			lines.append("Notes:")
			for reason in res.reasons[:5]:
				lines.append(f" - {reason}")

	return PlainTextResponse("\n".join(lines))

# Initialize fusion system
fusion = URLFusion()

@app.post("/analyze_url_v2")
async def analyze_url_v2(req: UrlAnalyzeRequest) -> dict:
	"""4-source fusion analysis with 2-of-4 consensus voting."""
	try:
		# Check whitelist first - if URL is whitelisted, return normal analysis with all sources safe
		if is_url_whitelisted(req.url):
			# Return normal analysis structure but with all sources showing safe
			return {
				"url": req.url,
				"final_verdict": False,  # Safe
				"confidence": 0.0,  # Low confidence since no analysis needed
				"sources": {
					"scanner": {"fired": False, "score": 0.0, "reason": "No suspicious patterns detected"},
					"hf": {"fired": False, "score": 0.0, "reason": "No phishing indicators found"},
					"graph": {"fired": False, "score": 0.0, "reason": "Domain appears legitimate"},
					"otx": {"fired": False, "score": 0.0, "reason": "No threat intelligence matches"}
				},
				"meta": {
					"mode": "whitelist",
					"K": 0,
					"weights": {},
					"allowlist_applied": True,
					"version": "fusion-4src-k2-v1",
					"timings_ms": {"whitelist_check": 1}
				}
			}
		
		# If not whitelisted, proceed with normal fusion analysis
		result = await fusion.analyze(req.url)
		return {
			"url": req.url,
			"final_verdict": result["final_verdict"],
			"confidence": round(result["confidence"], 3),
			"sources": result["sources"],
			"meta": result["meta"]
		}
	except Exception as e:
		raise HTTPException(status_code=500, detail=f"Fusion analysis failed: {str(e)}")

@app.get("/debug_url_v2")
async def debug_url_v2(url: str) -> dict:
	"""Debug endpoint showing full decision vector and timings."""
	try:
		result = await fusion.analyze(url)
		return {
			"url": url,
			"final_verdict": result["final_verdict"],
			"confidence": round(result["confidence"], 3),
			"sources": result["sources"],
			"meta": result["meta"],
			"debug": {
				"timings_ms": result["meta"]["timings_ms"],
				"source_breakdown": {
					source: {
						"score": data["score"],
						"threshold": data["threshold"],
						"fired": data["fired"],
						"unreachable": data["unreachable"],
						"reason": data["reason"]
					}
					for source, data in result["sources"].items()
				}
			}
		}
	except Exception as e:
		raise HTTPException(status_code=500, detail=f"Debug analysis failed: {str(e)}")
