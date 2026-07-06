"""
PhishingLens - consolidated detection API.

A single FastAPI process that runs the two core detectors (text + URL) behind one
clean, explainable contract. This is the deploy-friendly entrypoint (fits a free
CPU host); the full microservice stack lives under backend/ for local docker-compose.

Endpoints:
  GET  /health          -> service + model status
  POST /analyze         -> { content, mode? } auto-detects URL vs text
  POST /analyze_text    -> { text }
  POST /analyze_url     -> { url }

Unified response (see AnalyzeResponse): verdict, risk_score (0-100), confidence,
explainable signals, per-URL breakdown, and the model that produced it.
"""
from __future__ import annotations

import math
import os
import re
from collections import Counter
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import unquote, urlsplit

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# --------------------------------------------------------------------------- #
# Configuration
# --------------------------------------------------------------------------- #
MODEL_ID = os.getenv("MODEL_ID", "cybersectony/phishing-email-detection-distilbert_v2.4.1")
# Optional local model dir (used in dev to avoid re-downloading the hub weights).
LOCAL_MODEL_DIR = os.getenv("LOCAL_MODEL_DIR", "")
LOCAL_TOKENIZER_DIR = os.getenv("LOCAL_TOKENIZER_DIR", "")

# Decision thresholds (calibrated defaults; override via env).
TEXT_THRESHOLD = float(os.getenv("TEXT_THRESHOLD", "0.50"))
URL_THRESHOLD = float(os.getenv("URL_THRESHOLD", "0.50"))
SUSPICIOUS_LOW = float(os.getenv("SUSPICIOUS_LOW", "0.35"))  # band between safe and phishing
# The DistilBERT model is reliable on longer text but erratic on short/casual input
# (it confidently mis-scores short benign messages), so only trust it past this length.
MODEL_MIN_WORDS = int(os.getenv("MODEL_MIN_WORDS", "18"))

# Network probing (DNS/redirect) is off by default so the API stays fast and
# safe on a shared host. Lexical + model signals need no network.
ENABLE_NETWORK_CHECKS = os.getenv("ENABLE_NETWORK_CHECKS", "false").lower() in {"1", "true", "yes"}

MAX_URLS_PER_TEXT = int(os.getenv("MAX_URLS_PER_TEXT", "10"))

# --------------------------------------------------------------------------- #
# Model (lazy-loaded, graceful fallback to heuristics)
# --------------------------------------------------------------------------- #
_model = None
_tokenizer = None
_model_state = {"loaded": False, "name": None, "error": None}

# cybersectony label space: [legitimate_email, phishing_url, legitimate_url, phishing_url_alt]
_PHISH_IDX = (1, 3)
_LEGIT_IDX = (0, 2)


def _load_model() -> bool:
    """Load the DistilBERT classifier once. Returns True if usable."""
    global _model, _tokenizer
    if _model_state["loaded"]:
        return _model is not None
    try:
        import torch  # noqa: F401
        from transformers import AutoModelForSequenceClassification, AutoTokenizer

        tok_src = LOCAL_TOKENIZER_DIR or LOCAL_MODEL_DIR or MODEL_ID
        mdl_src = LOCAL_MODEL_DIR or MODEL_ID
        local_only = bool(LOCAL_MODEL_DIR)
        _tokenizer = AutoTokenizer.from_pretrained(tok_src, local_files_only=local_only)
        _model = AutoModelForSequenceClassification.from_pretrained(mdl_src, local_files_only=local_only)
        _model.eval()
        _model_state.update(loaded=True, name=mdl_src, error=None)
        return True
    except Exception as exc:  # pragma: no cover - defensive
        _model_state.update(loaded=True, name=None, error=str(exc))
        return False


def _model_scores(text: str) -> Optional[Dict[str, float]]:
    """Return {phishing, legit, raw_probs...} from the transformer, or None."""
    if not _load_model():
        return None
    try:
        import torch

        with torch.no_grad():
            enc = _tokenizer(text, max_length=256, padding="max_length", truncation=True, return_tensors="pt")
            logits = _model(**enc).logits
            probs = torch.softmax(logits, dim=-1).cpu().numpy()[0]
        n = len(probs)
        phishing = float(sum(probs[i] for i in _PHISH_IDX if i < n))
        legit = float(sum(probs[i] for i in _LEGIT_IDX if i < n))
        # 2-class fallback if the head is binary
        if n == 2:
            phishing, legit = float(probs[1]), float(probs[0])
        return {"phishing": phishing, "legit": legit, "probs": [float(x) for x in probs]}
    except Exception:
        return None


# --------------------------------------------------------------------------- #
# Heuristic text signals (used alongside / instead of the model)
# --------------------------------------------------------------------------- #
_TEXT_PATTERNS: List[Tuple[str, float, str]] = [
    (r"verify\s+your\s+account", 0.30, "Asks you to 'verify your account'"),
    (r"update\s+your\s+(password|payment|billing)", 0.30, "Requests a password/billing update"),
    (r"urgent|immediately|action required|within \d+ hours", 0.22, "Creates false urgency"),
    (r"suspend(ed)?|locked|deactivat", 0.22, "Threatens account suspension"),
    (r"click\s+(here|below|the link)", 0.18, "Generic 'click here' call to action"),
    (r"confirm\s+your\s+(identity|information|details)", 0.25, "Asks to confirm personal details"),
    (r"(gift\s+card|prize|winner|lottery|reward)", 0.25, "Prize/reward lure"),
    (r"(bank|paypal|wallet|invoice|wire transfer|bitcoin)", 0.15, "Financial pressure language"),
    (r"dear\s+(customer|user|account holder)", 0.15, "Impersonal generic greeting"),
    (r"(reply|share|send|provide|confirm)\s+(with\s+)?(your\s+)?(pin|otp|one[- ]?time)", 0.35, "Asks you to share a PIN/OTP"),
    (r"(parcel|package|shipment|courier).{0,50}(customs|held|redeliver|reschedul|unpaid|pending.{0,15}fee|small\s+fee)", 0.42, "Parcel/delivery-fee scam pattern"),
    (r"(you\s+have\s+won|you'?re\s+a\s+winner|congratulations.{0,25}won)", 0.30, "'You have won' lure"),
    (r"(tax\s+refund|claim\s+your\s+refund|rebate|refund\s+is\s+pending)", 0.22, "Refund/rebate lure"),
]


def _text_heuristics(text: str) -> Tuple[float, List[Dict[str, Any]]]:
    s = text.lower()
    score = 0.0
    signals: List[Dict[str, Any]] = []
    for pattern, weight, label in _TEXT_PATTERNS:
        if re.search(pattern, s):
            score += weight
            signals.append({"name": label, "severity": "medium", "weight": weight})
    return min(1.0, score), signals


# --------------------------------------------------------------------------- #
# URL lexical scanner (fast, no network)
# --------------------------------------------------------------------------- #
SUSPICIOUS_TLDS = {"zip", "xyz", "top", "gq", "work", "loan", "vip", "icu", "click",
                   "shop", "cam", "cf", "tk", "rest", "fit", "country", "kim", "men"}
PATH_KEYWORDS = {"verify", "update", "account", "login", "signin", "password", "secure",
                 "confirm", "validate", "unlock", "suspend", "invoice", "payment", "gift",
                 "prize", "reward", "bank", "wallet", "webscr", "recover"}
BRAND_TOKENS = {"paypal", "apple", "microsoft", "google", "amazon", "netflix", "facebook",
                "instagram", "whatsapp", "bank", "hdfc", "icici", "sbi", "coinbase", "binance"}


def _shannon_entropy(s: str) -> float:
    if not s:
        return 0.0
    counts = Counter(s)
    n = len(s)
    return -sum((c / n) * math.log2(c / n) for c in counts.values())


def _url_lexical(url: str) -> Tuple[float, List[Dict[str, Any]], Dict[str, Any]]:
    """Return (risk 0-1, signals, features) from lexical analysis only."""
    import tldextract

    signals: List[Dict[str, Any]] = []
    score = 0.0

    try:
        parts = urlsplit(url if "://" in url else "http://" + url)
        host = parts.netloc.lower()
        path_q = (parts.path or "") + "?" + (parts.query or "")
    except Exception:
        host, path_q = url.lower(), ""

    ext = tldextract.extract(url)
    domain = ext.domain or ""
    tld = ext.suffix or ""
    subdomain = ext.subdomain or ""

    def add(weight: float, name: str, severity: str = "medium"):
        nonlocal score
        score += weight
        signals.append({"name": name, "severity": severity, "weight": weight})

    if re.search(r"\d+\.\d+\.\d+\.\d+", host):
        add(0.35, "Uses a raw IP address instead of a domain", "high")
    if "@" in url:
        add(0.30, "Contains an '@' - hides the real destination", "high")
    if len(url) > 90:
        add(0.15, "Unusually long URL")
    if host.count(".") >= 4:
        add(0.20, "Excessive subdomains")
    if tld in SUSPICIOUS_TLDS:
        add(0.25, f"Suspicious top-level domain (.{tld})", "high")
    if "-" in domain and len(domain) >= 12:
        add(0.15, "Long hyphenated domain (look-alike pattern)")
    ent = _shannon_entropy(url)
    if ent > 4.0:
        add(0.15, "High-entropy / random-looking URL")
    try:
        dec = unquote(url)
        if len(url) - len(dec) > 6:
            add(0.15, "Heavy percent-encoding (obfuscation)")
    except Exception:
        pass
    kw = sum(1 for k in PATH_KEYWORDS if k in path_q.lower())
    if kw >= 2:
        add(0.22, "Multiple credential/verification keywords in the path", "high")
    elif kw == 1:
        add(0.12, "Credential/verification keyword in the path")
    # Brand token in subdomain/path but not the registered domain -> impersonation
    hay = (subdomain + " " + path_q).lower()
    dom_l = domain.lower()
    brand_hit = next((b for b in BRAND_TOKENS if b in hay and b not in dom_l), None)
    if brand_hit:
        add(0.30, f"Impersonates a known brand ('{brand_hit}') outside its real domain", "high")
    # Brand token baked into a look-alike registered domain (paypal-support.com, paypalsecure.com)
    lookalike = next((b for b in BRAND_TOKENS if b in dom_l and dom_l != b), None)
    if lookalike:
        add(0.28, f"Look-alike domain containing '{lookalike}'", "high")
    if parts.scheme == "http" and host:
        add(0.08, "No HTTPS", "low")

    features = {
        "domain": f"{domain}.{tld}" if tld else domain,
        "tld": tld,
        "length": len(url),
        "entropy": round(ent, 2),
        "keyword_hits": kw,
        "num_subdomains": host.count("."),
    }
    # Logistic squash so the score spreads sensibly across 0-1
    risk = 1.0 / (1.0 + math.exp(-4.0 * (score - 0.45)))
    return risk, signals, features


# --------------------------------------------------------------------------- #
# URL extraction from free text
# --------------------------------------------------------------------------- #
_URL_RE = re.compile(r"https?://[^\s<>\"'{}|\\^`\[\]]+", re.IGNORECASE)
_BARE_DOMAIN_RE = re.compile(
    r"\b(?:www\.)?[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?(?:\.[a-z0-9-]{1,63})+\.[a-z]{2,}\b",
    re.IGNORECASE,
)


def _extract_urls(text: str) -> List[str]:
    urls = list(dict.fromkeys(_URL_RE.findall(text)))
    return urls[:MAX_URLS_PER_TEXT]


def _looks_like_url(s: str) -> bool:
    s = s.strip()
    if _URL_RE.fullmatch(s):
        return True
    if " " in s:
        return False
    return bool(_BARE_DOMAIN_RE.fullmatch(s))


# --------------------------------------------------------------------------- #
# Verdict assembly
# --------------------------------------------------------------------------- #
def _verdict(risk: float, threshold: float) -> str:
    if risk >= threshold:
        return "phishing"
    if risk >= SUSPICIOUS_LOW:
        return "suspicious"
    return "safe"


def analyze_url(url: str) -> "AnalyzeResponse":
    url = url.strip()
    lex_risk, lex_signals, features = _url_lexical(url)
    # NOTE: the DistilBERT model is an email/text classifier that over-predicts
    # phishing on bare URLs (it flags github.com/google.com as phishing). So URL
    # verdicts rely on the interpretable lexical scanner. The transformer still
    # powers text/email analysis, including URLs seen *in context* inside a message.
    risk = lex_risk
    model_name = "lexical-forensics"
    verdict = _verdict(risk, URL_THRESHOLD)
    return AnalyzeResponse(
        type="url",
        input=url,
        verdict=verdict,
        is_phishing=(verdict == "phishing"),
        risk_score=round(risk * 100, 1),
        confidence=round((risk if verdict != "safe" else 1 - risk), 3),
        model=model_name,
        signals=_dedupe_signals(lex_signals) or [{"name": "No strong phishing indicators found",
                                                  "severity": "low", "weight": 0.0}],
        features=features,
    )


def analyze_text(text: str) -> "AnalyzeResponse":
    text = text.strip()
    urls = _extract_urls(text)

    body = text
    for u in urls:
        body = body.replace(u, " ")
    body = body.strip()

    # If the input is essentially just a bare URL, judge it with the URL lens.
    # The DistilBERT email model over-predicts phishing on bare URLs (it would flag
    # netflix.com / github.com as phishing), so never run it on URL-only input.
    if not body and len(urls) == 1:
        return analyze_url(urls[0])

    url_results = [analyze_url(u) for u in urls]
    worst_url = max((r.risk_score / 100 for r in url_results), default=0.0)

    ms = _model_scores(body) if body else None
    model_risk = ms["phishing"] if ms else None
    heur_risk, heur_signals = _text_heuristics(text)

    # Heuristics + embedded-URL analysis are always reliable. The DistilBERT score
    # is only trusted when it is *confident* (>= 0.85): on short, out-of-domain
    # casual text it sits near 0.55 for both benign and phishing, so a mid-range
    # score is noise and must not drive a phishing verdict on its own.
    word_count = len(body.split()) if body else 0
    risk = max(heur_risk, worst_url)
    model_name = "DistilBERT (cybersectony v2.4.1)" if model_risk is not None else "heuristic"
    if model_risk is not None and model_risk >= 0.85 and word_count >= MODEL_MIN_WORDS:
        risk = max(risk, model_risk)
        heur_signals.insert(0, {"name": f"AI model flags this message as phishing ({model_risk*100:.0f}%)",
                                "severity": "high", "weight": model_risk})
    verdict = _verdict(risk, TEXT_THRESHOLD)

    signals = _dedupe_signals(heur_signals)
    for r in url_results:
        if r.is_phishing:
            signals.append({"name": f"Contains a phishing link: {r.input}", "severity": "high", "weight": 0.9})
    if not signals:
        signals = [{"name": "No strong phishing indicators found", "severity": "low", "weight": 0.0}]

    return AnalyzeResponse(
        type="text",
        input=text if len(text) <= 500 else text[:500] + "…",
        verdict=verdict,
        is_phishing=(verdict == "phishing"),
        risk_score=round(risk * 100, 1),
        confidence=round((risk if verdict != "safe" else 1 - risk), 3),
        model=model_name,
        signals=signals,
        urls=[r.model_dump() for r in url_results] or None,
    )


def _dedupe_signals(signals: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen, out = set(), []
    for s in sorted(signals, key=lambda x: -x.get("weight", 0)):
        if s["name"] in seen:
            continue
        seen.add(s["name"])
        out.append(s)
    return out[:8]


# --------------------------------------------------------------------------- #
# Domain intelligence (the "graph" lens): DNS presence + WHOIS age.
# Best-effort with tight timeouts; WHOIS may be blocked on some hosts (degrades).
# --------------------------------------------------------------------------- #
def _domain_intel(domain: str) -> Tuple[float, List[Dict[str, Any]], Dict[str, Any]]:
    import socket

    signals: List[Dict[str, Any]] = []
    feats: Dict[str, Any] = {}
    delta = 0.0
    if not domain or "." not in domain:
        return 0.0, signals, feats

    old_to = socket.getdefaulttimeout()
    socket.setdefaulttimeout(4)
    try:
        try:
            socket.getaddrinfo(domain, None)
            feats["dns"] = "resolves"
        except Exception:
            feats["dns"] = "no records"
            delta += 0.25
            signals.append({"name": "Domain has no DNS records (does not resolve)",
                            "severity": "high", "weight": 0.25})
        try:
            import datetime
            import whois
            created = whois.whois(domain).creation_date
            if isinstance(created, list):
                created = created[0] if created else None
            if isinstance(created, datetime.datetime):
                age = (datetime.datetime.now() - created).days
                feats["domain_age_days"] = age
                if age < 30:
                    delta += 0.35
                    signals.append({"name": f"Domain registered only {age} days ago (very new)",
                                    "severity": "high", "weight": 0.35})
                elif age < 180:
                    delta += 0.15
                    signals.append({"name": f"Relatively new domain ({age} days old)",
                                    "severity": "medium", "weight": 0.15})
                else:
                    signals.append({"name": f"Established domain (~{max(1, age // 365)} yr old)",
                                    "severity": "low", "weight": 0.0})
        except Exception:
            pass
    finally:
        socket.setdefaulttimeout(old_to)
    return delta, signals, feats


def analyze_domain(url_or_domain: str) -> "AnalyzeResponse":
    import tldextract

    ext = tldextract.extract(url_or_domain)
    domain = f"{ext.domain}.{ext.suffix}" if ext.suffix else url_or_domain.strip()
    seed = url_or_domain if "://" in url_or_domain else "http://" + domain
    lex_risk, lex_signals, features = _url_lexical(seed)
    delta, d_signals, d_feats = _domain_intel(domain)
    risk = min(1.0, lex_risk + delta)
    features.update(d_feats)
    verdict = _verdict(risk, URL_THRESHOLD)
    signals = _dedupe_signals(lex_signals + d_signals) or [
        {"name": "No strong phishing indicators found", "severity": "low", "weight": 0.0}]
    return AnalyzeResponse(
        type="domain", input=domain, verdict=verdict, is_phishing=(verdict == "phishing"),
        risk_score=round(risk * 100, 1), confidence=round((risk if verdict != "safe" else 1 - risk), 3),
        model="domain-intelligence", signals=signals, features=features,
    )


# --------------------------------------------------------------------------- #
# Image analysis (the "visual" lens): OCR the image, then reuse text/URL detection.
# Catches phishing screenshots (fake login pages, scam-SMS images).
# --------------------------------------------------------------------------- #
def _ocr_image(image_bytes: bytes) -> str:
    from io import BytesIO

    import pytesseract
    from PIL import Image

    img = Image.open(BytesIO(image_bytes))
    if img.mode != "RGB":
        img = img.convert("RGB")
    return pytesseract.image_to_string(img)


def analyze_image(image_base64: str) -> "AnalyzeResponse":
    import base64

    def _bail(msg: str, risk: float = 0.0):
        return AnalyzeResponse(type="image", input=f"({msg})", verdict="safe", is_phishing=False,
                               risk_score=risk, confidence=0.6, model="image-ocr",
                               signals=[{"name": msg, "severity": "low", "weight": 0.0}])
    try:
        raw = base64.b64decode(image_base64.split(",")[-1])
    except Exception:
        return _bail("Could not decode image")
    try:
        text = _ocr_image(raw).strip()
    except Exception as exc:
        return _bail(f"OCR unavailable: {str(exc)[:80]}")
    if not text:
        return _bail("No readable text found in image", risk=5.0)

    res = analyze_text(text)
    res.type = "image"
    res.model = "image-ocr + " + (res.model or "")
    res.input = "OCR: " + (text[:300] + "…" if len(text) > 300 else text)
    res.signals = [{"name": f"Read {len(text.split())} words of text from the image (OCR)",
                    "severity": "low", "weight": 0.0}] + res.signals
    return res


# --------------------------------------------------------------------------- #
# API schema
# --------------------------------------------------------------------------- #
class AnalyzeRequest(BaseModel):
    content: str = Field(..., description="Text, email, SMS, or URL to analyze")
    mode: str = Field("auto", description="auto | text | url")


class TextRequest(BaseModel):
    text: str


class UrlRequest(BaseModel):
    url: str


class DomainRequest(BaseModel):
    domain: str


class ImageRequest(BaseModel):
    image_base64: str


class AnalyzeResponse(BaseModel):
    type: str
    input: str
    verdict: str                      # phishing | suspicious | safe
    is_phishing: bool
    risk_score: float                 # 0-100
    confidence: float                 # 0-1 in the stated verdict
    model: Optional[str] = None
    signals: List[Dict[str, Any]] = []
    features: Optional[Dict[str, Any]] = None
    urls: Optional[List[Dict[str, Any]]] = None


# --------------------------------------------------------------------------- #
# App
# --------------------------------------------------------------------------- #
app = FastAPI(title="PhishingLens API", version="2.0.0",
              description="Multi-modal phishing detection - text + URL core.")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "phishinglens",
        "version": app.version,
        "model_loaded": _model_state["loaded"] and _model is not None,
        "model": _model_state["name"],
        "model_error": _model_state["error"],
    }


@app.post("/analyze", response_model=AnalyzeResponse)
def analyze(req: AnalyzeRequest):
    mode = req.mode.lower()
    if mode == "url" or (mode == "auto" and _looks_like_url(req.content)):
        return analyze_url(req.content)
    return analyze_text(req.content)


@app.post("/analyze_text", response_model=AnalyzeResponse)
def analyze_text_ep(req: TextRequest):
    return analyze_text(req.text)


@app.post("/analyze_url", response_model=AnalyzeResponse)
def analyze_url_ep(req: UrlRequest):
    return analyze_url(req.url)


@app.post("/analyze_domain", response_model=AnalyzeResponse)
def analyze_domain_ep(req: DomainRequest):
    return analyze_domain(req.domain)


@app.post("/analyze_image", response_model=AnalyzeResponse)
def analyze_image_ep(req: ImageRequest):
    return analyze_image(req.image_base64)


@app.on_event("startup")
def _warm():
    # Warm the model in the background-ish (first call otherwise pays the load cost).
    try:
        _load_model()
    except Exception:
        pass
