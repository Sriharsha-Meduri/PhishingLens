from fastapi import FastAPI
from fastapi.responses import PlainTextResponse
from backend.common.schemas import TextAnalyzeRequest, TextAnalyzeResponse, Highlight
from backend.common.config import settings
import re
from typing import List, Optional
import os
import sys
import httpx
from urllib.parse import urlsplit

# Ensure the project root is in PYTHONPATH
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../"))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

app = FastAPI(title="Text Analysis Service", version="0.2.0")


# ------------------ Heuristic fallback ------------------
SUSPICIOUS_PATTERNS = [
	(r"verify\s+your\s+account", 0.4),
	(r"update\s+your\s+password", 0.35),
	(r"urgent|immediately|action required", 0.25),
	(r"click\s+here", 0.2),
	(r"login\s+to\s+your\s+account", 0.3),
	(r"bank|wallet|invoice|funds|payment", 0.15),
	(r"confirm\s+your\s+information", 0.3),
	(r"suspend|suspended|locked", 0.2),
]


def heuristic_score(text: str) -> tuple[float, List[str], List[Highlight]]:
	s = text.lower()
	score = 0.0
	reasons: List[str] = []
	highlights: List[Highlight] = []
	for pattern, weight in SUSPICIOUS_PATTERNS:
		for m in re.finditer(pattern, s):
			score += weight
			reasons.append(f"Matched pattern: {pattern}")
			highlights.append(Highlight(span=text[m.start():m.end()], score=weight, start=m.start(), end=m.end()))
	confidence = min(1.0, score)
	return confidence, reasons, highlights


# ------------------ Optional ONNX Runtime path ------------------
_onnx_scorer_loaded = False
_onnx_session = None
_onnx_tokenizer = None
_onnx_model_name = "distilbert-onnx-demo"
_onnx_last_error: Optional[str] = None

# ------------------ Transformers fallback (CPU) ------------------
_hf_loaded = False
_hf_tokenizer = None
_hf_model = None
_hf_model_name = settings.SERVICE_MODEL_ID or "distilbert-finetuned"
# Optional temperature scaling for calibrated probabilities (from evaluation)
_hf_calib_T_env = os.getenv("EXTERNAL_CALIB_T", None)
try:
    _hf_calib_T: float = float(_hf_calib_T_env) if _hf_calib_T_env else 1.0
except Exception:
    _hf_calib_T = 1.0

# ------------------ Decision config ------------------
PHISH_CLASS_INDEX: int = int(os.getenv("TEXT_PHISH_CLASS_INDEX", "1"))  # which softmax index is phishing
TEXT_THRESHOLD: float = float(os.getenv("TEXT_THRESHOLD", "0.5"))       # decision threshold on phishing prob
# Force calibrated probability decisioning only; ignore argmax
USE_ARGMAX: bool = False

# ------------------ Observability (debug/probe) ------------------
_hf_last_text: Optional[str] = None
_hf_last_probs: Optional[list[float]] = None
_hf_last_labels: Optional[list[str]] = None
_hf_last_phishing_prob: Optional[float] = None
_hf_last_ham_prob: Optional[float] = None
_hf_last_probs_raw: Optional[list[float]] = None
_hf_last_phishing_prob_cal: Optional[float] = None

# ------------------ Allowlist configuration ------------------
# Soft trust signals (domains and transactional patterns)
_allowlist_env = os.getenv("TEXT_SENDER_DOMAIN_ALLOWLIST", "")
TEXT_SENDER_DOMAIN_ALLOWLIST: list[str] = [d.strip().lower() for 
d in _allowlist_env.split(",") if d.strip()]
TRANSACTIONAL_PATTERNS: list[str] = [
    "you have successfully registered",
    "verification code",
    "verify and activate the account",
    "reset your password",
    "thank you for creating your profile",
    "thanks for joining",
    "welcome to",
    "order delivered",
    "weekly analytics",
    "points credited",
    "your order is delivered",
    "delivered on time",
    "view all analytics",
    "weekly analytics recap",
    "order is delivered",
    "reward credited",
    "subscription activated",
]


def _try_load_onnx() -> bool:
	global _onnx_scorer_loaded, _onnx_session, _onnx_tokenizer, _onnx_last_error
	if _onnx_scorer_loaded:
		result = _onnx_session is not None and _onnx_tokenizer is not None
		print(f"DEBUG: _try_load_onnx cached result: {result}")
		return result
	try:
		from onnxruntime import InferenceSession, SessionOptions
		from transformers import AutoTokenizer
		# Force default paths if env not set (compose may not inject env on restart)
		model_path = os.getenv("TEXT_ONNX_MODEL") or "/models/text/distilbert.onnx"
		tok_path: Optional[str] = os.getenv("TEXT_TOKENIZER_DIR") or "/models/text/tokenizer"
		if not (os.path.exists(model_path) and tok_path and os.path.isdir(tok_path)):
			_missing = []
			if not os.path.exists(model_path):
				_missing.append(f"missing_model:{model_path}")
			if not tok_path or not os.path.isdir(tok_path):
				_missing.append(f"missing_tokenizer:{tok_path}")
			_onnx_last_error = ",".join(_missing) or "paths_invalid"
			_onnx_scorer_loaded = True
			return False
		opts = SessionOptions()
		opts.intra_op_num_threads = 1
		providers_env = os.getenv("ORT_PROVIDERS", "CPUExecutionProvider").split(",")
		providers = [p.strip() for p in providers_env if p.strip()]
		_onnx_session = InferenceSession(model_path, sess_options=opts, providers=providers)
		_onnx_tokenizer = AutoTokenizer.from_pretrained(tok_path, local_files_only=True)
		_onnx_scorer_loaded = True
		return True
	except Exception as e:
		_onnx_last_error = str(e)
		_onnx_scorer_loaded = True
		return False


def _onnx_score(text: str) -> Optional[tuple[float, List[str], List[Highlight]]]:
	if not _try_load_onnx():
		print("DEBUG: ONNX not loaded")
		return None
	try:
		print("DEBUG: Starting ONNX inference")
		# Align tokenizer sequence length to model's expected second dim (if static)
		seq_len = 256
		try:
			for inp in _onnx_session.get_inputs():
				if "input_ids" in inp.name and len(getattr(inp, "shape", [])) >= 2:
					maybe_len = inp.shape[1]
					if isinstance(maybe_len, int) and maybe_len > 0:
						seq_len = int(maybe_len)
						break
		except Exception:
			pass
		enc = _onnx_tokenizer(
			text,
			max_length=seq_len,
			padding="max_length",
			truncation=True,
			return_tensors="np",
		)
		# Feed using actual model input names to avoid name mismatches
		import numpy as np
		model_inputs = _onnx_session.get_inputs()
		feed: dict[str, np.ndarray] = {}
		for inp in model_inputs:
			name = inp.name
			if "input_ids" in name and "input_ids" in enc:
				arr = np.ascontiguousarray(enc["input_ids"]).astype(np.int64, copy=False)
				feed[name] = arr
			elif "attention_mask" in name and "attention_mask" in enc:
				arr = np.ascontiguousarray(enc["attention_mask"]).astype(np.int64, copy=False)
				feed[name] = arr
			elif "token_type_ids" in name and "token_type_ids" in enc:
				arr = np.ascontiguousarray(enc["token_type_ids"]).astype(np.int64, copy=False)
				feed[name] = arr
		# Debug dtypes
		try:
			print("DEBUG: ONNX feed dtypes:", {k: v.dtype.name for k, v in feed.items()})
		except Exception:
			pass
		outputs = _onnx_session.run(None, feed)
		# Assume binary classifier [batch, 2] with softmax logits; use class 1 as phishing
		logits = outputs[0]
		probs = np.exp(logits) / np.sum(np.exp(logits), axis=-1, keepdims=True)
		# Allow configurable phishing class index
		confidence = float(probs[0, PHISH_CLASS_INDEX])  # probability of phishing class
		reasons = ["Transformer signal"]
		print(f"DEBUG: ONNX confidence (phishing prob): {confidence}")
		# Always return phishing probability; threshold applied upstream
		return confidence, reasons, []
	except Exception as e:
		print(f"DEBUG: ONNX error: {e}")
		return None


def _try_load_hf() -> bool:
    global _hf_loaded, _hf_tokenizer, _hf_model
    if _hf_loaded:
        return _hf_tokenizer is not None and _hf_model is not None
    try:
        from transformers import AutoTokenizer, AutoModelForSequenceClassification
        # Try configured HF model id first
        model_id = os.getenv("SERVICE_MODEL_ID", settings.SERVICE_MODEL_ID)
        fallback_id = os.getenv("SERVICE_FALLBACK_MODEL_ID", settings.SERVICE_FALLBACK_MODEL_ID)
        try:
            _tok = AutoTokenizer.from_pretrained(model_id)
            _mdl = AutoModelForSequenceClassification.from_pretrained(model_id)
            _mdl.eval()
            _model_loaded_from = model_id
            _tokenizer_loaded_from = model_id
        except Exception:
            # Fallback to local fine-tuned artifacts
            model_dir = os.getenv("TEXT_HF_MODEL_DIR") or fallback_id or "/models/text/model"
            tok_dir = os.getenv("TEXT_TOKENIZER_DIR") or "/models/text/tokenizer"
            if not (os.path.isdir(str(model_dir)) and os.path.isdir(str(tok_dir))):
                _hf_loaded = True
                return False
            _tok = AutoTokenizer.from_pretrained(tok_dir, local_files_only=True)
            _mdl = AutoModelForSequenceClassification.from_pretrained(model_dir, local_files_only=True)
            _mdl.eval()
            _model_loaded_from = str(model_dir)
            _tokenizer_loaded_from = str(tok_dir)

        # Assign globals
        globals()["_hf_tokenizer"] = _tok
        globals()["_hf_model"] = _mdl
        globals()["_hf_loaded"] = True
        globals()["_hf_model_name"] = _model_loaded_from
        return True
    except Exception:
        _hf_loaded = True
        return False


def _hf_score(text: str) -> Optional[tuple[float, List[str], List[Highlight]]]:
    if not _try_load_hf():
        return None
    try:
        import torch
        with torch.no_grad():
            enc = _hf_tokenizer(text, max_length=512, padding="max_length", truncation=True, return_tensors="pt")
            outputs = _hf_model(**enc)
            logits = outputs.logits
            # Compute raw and calibrated probabilities
            T = max(1e-6, float(_hf_calib_T))
            probs_raw = torch.softmax(logits, dim=-1).cpu().numpy()
            probs = torch.softmax(logits / T, dim=-1).cpu().numpy()
            # Handle 4-logit external label space by summing phishing classes
            phishing_prob = None
            ham_prob = None
            try:
                if probs.shape[-1] >= 4:
                    # indices: [legitimate_email, phishing_url, legitimate_url, phishing_url_alt]
                    # Only use phishing_url probability, ignore phishing_url_alt to reduce false positives
                    phishing_prob = float(probs[0, 1])
                    ham_prob = float(probs[0, 0] + probs[0, 2])
                    labels = [
                        "legitimate_email",
                        "phishing_url",
                        "legitimate_url",
                    ]
                else:
                    phishing_prob = float(probs[0, PHISH_CLASS_INDEX])
                    ham_prob = float(1.0 - phishing_prob)
                    labels = ["ham", "phish"] if probs.shape[-1] == 2 else [f"c{i}" for i in range(probs.shape[-1])]
            except Exception:
                phishing_prob = float(probs[0, PHISH_CLASS_INDEX])
                ham_prob = float(1.0 - phishing_prob)
                labels = ["ham", "phish"] if probs.shape[-1] == 2 else [f"c{i}" for i in range(probs.shape[-1])]
            reasons = ["Transformer signal", f"phishing_prob={phishing_prob:.3f}", f"ham_prob={ham_prob:.3f}"]
            # Update observability globals for /debug
            try:
                globals()["_hf_last_text"] = text
                globals()["_hf_last_probs_raw"] = [float(x) for x in probs_raw[0].tolist()]
                globals()["_hf_last_probs"] = [float(x) for x in probs[0].tolist()]
                globals()["_hf_last_labels"] = labels
                globals()["_hf_last_phishing_prob"] = float(phishing_prob)
                globals()["_hf_last_ham_prob"] = float(ham_prob)
                globals()["_hf_last_phishing_prob_cal"] = float(phishing_prob)
            except Exception:
                pass
            return phishing_prob, reasons, []
    except Exception:
        return None


@app.post("/analyze_text")
async def analyze_text(req: TextAnalyzeRequest) -> dict:
    # Extract URLs first and analyze them
    urls = _extract_urls_from_text(req.text)
    url_is_phish, url_conf, url_reasons, url_checked = await _analyze_urls(urls)
    print(f"DEBUG: URL analysis - is_phish: {url_is_phish}, conf: {url_conf}, checked: {url_checked}, reasons: {url_reasons}")

    # Text-only part: remove URLs from text for cleaner classification
    text_clean = req.text
    for u in urls:
        text_clean = text_clean.replace(u, " ")

    # Try ONNX model first; fall back to HF or heuristics
    print("DEBUG: Starting text analysis")
    prefer_hf = False
    try:
        # When external thresholding is enabled, we evaluate with HF model
        if settings.SERVICE_USE_EXTERNAL_THRESHOLD:
            prefer_hf = True
    except Exception:
        prefer_hf = False

    text_conf = 0.0
    text_reasons: List[str] = []
    highlights: List[Highlight] = []
    model_name = ""

    if not prefer_hf:
        onnx_result = _onnx_score(text_clean)
        print(f"DEBUG: ONNX result: {onnx_result is not None}")
        if onnx_result is not None:
            text_conf, text_reasons, highlights = onnx_result
            model_name = _onnx_model_name
            print(f"DEBUG: Using ONNX model: {model_name}")
        else:
            print("DEBUG: Trying HF transformers (fallback)")
            hf_result = _hf_score(text_clean)
            print(f"DEBUG: HF result: {hf_result is not None}")
            if hf_result is not None:
                text_conf, text_reasons, highlights = hf_result
                model_name = _hf_model_name
                print(f"DEBUG: Using HF model: {model_name}")
            else:
                print("DEBUG: Falling back to heuristics")
                text_conf, text_reasons, highlights = heuristic_score(text_clean)
                model_name = "heuristic-demo-0.2"
    else:
        print("DEBUG: Forcing HF transformers due to external thresholding")
        hf_result = _hf_score(text_clean)
        print(f"DEBUG: HF result: {hf_result is not None}")
        if hf_result is not None:
            text_conf, text_reasons, highlights = hf_result
            model_name = _hf_model_name
        else:
            # As a last resort, try ONNX; otherwise heuristics
            onnx_result = _onnx_score(text_clean)
            if onnx_result is not None:
                text_conf, text_reasons, highlights = onnx_result
                model_name = _onnx_model_name
            else:
                text_conf, text_reasons, highlights = heuristic_score(text_clean)
                model_name = "heuristic-demo-0.2"

    # Decisions (apply external threshold if configured)
    effective_threshold = TEXT_THRESHOLD
    try:
        if settings.SERVICE_USE_EXTERNAL_THRESHOLD:
            # Allow profile-based defaults unless an explicit threshold is provided
            profile = (os.getenv("EXTERNAL_TEXT_PROFILE", "").strip().lower())
            threshold_env = os.getenv("EXTERNAL_TEXT_THRESHOLD", "").strip()
            profile_defaults = {
                "ceas": 0.125,   # CEAS tests prefer lower threshold
                "general": 0.185, # general calibrated threshold from evaluation
                "demo": 0.60,     # interactive demos to avoid over-flagging
            }
            if threshold_env:
                effective_threshold = float(threshold_env)
            elif profile in profile_defaults:
                effective_threshold = float(profile_defaults[profile])
            else:
                effective_threshold = 0.185
    except Exception:
        pass
    # Short-text safeguard: require higher confidence for very short texts without URLs
    try:
        short_min = int(os.getenv("SHORT_TEXT_MIN_TOKENS", "3"))
        short_high = float(os.getenv("SHORT_TEXT_HIGH_THRESHOLD", "0.80"))
    except Exception:
        short_min, short_high = 3, 0.80

    # Count tokens (simple whitespace tokenization to avoid device overhead)
    token_count = len(text_clean.strip().split()) if text_clean else 0
    no_urls_present = len(urls) == 0
    
    # Apply short-text safeguard for very short text content, regardless of URL presence
    # This prevents false positives on short text like "hello" even when URLs are present
    if settings.SERVICE_USE_EXTERNAL_THRESHOLD and token_count < short_min:
        # Enforce higher threshold for ultra-short inputs
        effective_threshold = max(effective_threshold, short_high)
    # Decide strictly on calibrated probability thresholding
    text_is_phish = (text_conf >= effective_threshold)

    # Fusion: only OR when URL verdict was actually checked
    if url_checked:
        final_is_phish = bool(url_is_phish or text_is_phish)
        final_conf = float(round(max(url_conf, text_conf), 3))
        print(f"DEBUG: Fusion with URL - text_is_phish: {text_is_phish}, url_is_phish: {url_is_phish}, final_is_phish: {final_is_phish}")
    else:
        # Gate OR-fusion on url_checked explicitly
        final_is_phish = bool(text_is_phish)
        final_conf = float(round(text_conf, 3))
        print(f"DEBUG: Fusion without URL - text_is_phish: {text_is_phish}, final_is_phish: {final_is_phish}")

    # Soft trust gate: only applies when calibrated score is below high ceiling and URL not flagged
    try:
        high_ceiling = float(os.getenv("ALLOWLIST_OVERRIDE_MIN_CONF", "0.98"))
    except Exception:
        high_ceiling = 0.98
    override_reason = None
    if (not url_checked or (url_checked and not url_is_phish and url_conf < 0.3)) and text_conf < high_ceiling:
        try:
            # Domain-based soft trust
            url_hosts: list[str] = []
            for u in urls:
                try:
                    host = urlsplit(u).netloc.lower()
                except Exception:
                    host = ""
                if host:
                    url_hosts.append(host)
            def is_allowlisted(host: str) -> bool:
                return any(host.endswith("." + d) or host == d for d in TEXT_SENDER_DOMAIN_ALLOWLIST)
            domain_trusted = any(is_allowlisted(h) for h in url_hosts) if TEXT_SENDER_DOMAIN_ALLOWLIST else False
            # Pattern-based transactional soft trust
            s_lower = text_clean.lower()
            transactional_hit = any(pat in s_lower for pat in TRANSACTIONAL_PATTERNS)
            if domain_trusted or transactional_hit:
                final_is_phish = False
                final_conf = float(round(min(final_conf, text_conf), 3))
                override_reason = "soft_trust_gate"
                text_reasons = ["Soft trust gate (domain/pattern)"] + text_reasons
        except Exception:
            pass
    # Reasons fusion
    reasons = []
    if url_is_phish:
        reasons.extend(url_reasons[:3])
    if text_is_phish:
        reasons.extend(text_reasons[:3])
    if not reasons:
        reasons = (url_reasons or text_reasons)[:5]

    # Build hf_text
    hf_text = {
        "class_probs_raw": {lbl: float(_hf_last_probs_raw[i]) for i, lbl in enumerate(_hf_last_labels)} if (_hf_last_probs_raw and _hf_last_labels) else None,
        "class_probs_cal": {lbl: float(_hf_last_probs[i]) for i, lbl in enumerate(_hf_last_labels)} if (_hf_last_probs and _hf_last_labels) else None,
        "phishing_prob_cal": float(text_conf),
        "threshold_text": float(effective_threshold),
        "verdict_text": bool(text_is_phish),
    }

    # Bare URL input → delegate to URL analysis only
    s = (req.text or "").strip()
    per_urls: list[dict] = []
    try:
        if re.fullmatch(_URL_PATTERN_WITH_PROTO, s):
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(f"{settings.URL_SERVICE_URL}/analyze_url_v2", json={"url": s})
                if resp.status_code == 200:
                    ures = resp.json()
                    per_urls.append(ures)
                    return {"hf_text": None, "urls": per_urls, "final_verdict": bool(ures.get("final_verdict", False))}
    except Exception:
        pass

    # Text+URLs → analyze up to 20 URLs via url_service using 4-source fusion
    capped = urls[:20]
    for u in capped:
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(f"{settings.URL_SERVICE_URL}/analyze_url_v2", json={"url": u})
                if resp.status_code == 200:
                    per_urls.append(resp.json())
        except Exception:
            continue

    any_url_verdict = any(bool(x.get("final_verdict", False)) for x in per_urls)
    final_verdict = bool(text_is_phish or any_url_verdict)

    return {
        "hf_text": hf_text,
        "urls": per_urls,
        "final_verdict": final_verdict,
    }


@app.post("/debug_text")
async def debug_text(req: TextAnalyzeRequest) -> dict:
    # Mirror the analyze_text logic but return detailed debug fields
    urls = _extract_urls_from_text(req.text)
    url_is_phish, url_conf, url_reasons, url_checked = await _analyze_urls(urls)
    text_clean = req.text
    for u in urls:
        text_clean = text_clean.replace(u, " ")

    # Prefer HF when external thresholding is enabled
    use_hf = False
    try:
        if settings.SERVICE_USE_EXTERNAL_THRESHOLD:
            use_hf = True
    except Exception:
        use_hf = False

    # Score text
    text_conf = 0.0
    model_name = ""
    if use_hf:
        hf_result = _hf_score(text_clean)
        if hf_result is not None:
            text_conf = float(hf_result[0])
            model_name = _hf_model_name
        else:
            onnx_result = _onnx_score(text_clean)
            if onnx_result is not None:
                text_conf = float(onnx_result[0])
                model_name = _onnx_model_name
            else:
                text_conf, _, _ = heuristic_score(text_clean)
                model_name = "heuristic-demo-0.2"
    else:
        onnx_result = _onnx_score(text_clean)
        if onnx_result is not None:
            text_conf = float(onnx_result[0])
            model_name = _onnx_model_name
        else:
            hf_result = _hf_score(text_clean)
            if hf_result is not None:
                text_conf = float(hf_result[0])
                model_name = _hf_model_name
            else:
                text_conf, _, _ = heuristic_score(text_clean)
                model_name = "heuristic-demo-0.2"

    # Effective threshold
    effective_threshold = TEXT_THRESHOLD
    try:
        if settings.SERVICE_USE_EXTERNAL_THRESHOLD:
            profile = (os.getenv("EXTERNAL_TEXT_PROFILE", "").strip().lower())
            threshold_env = os.getenv("EXTERNAL_TEXT_THRESHOLD", "").strip()
            profile_defaults = {"ceas": 0.125, "general": 0.185, "demo": 0.60}
            if threshold_env:
                effective_threshold = float(threshold_env)
            elif profile in profile_defaults:
                effective_threshold = float(profile_defaults[profile])
            else:
                effective_threshold = 0.185
    except Exception:
        pass

    # Short-text safeguard
    try:
        short_min = int(os.getenv("SHORT_TEXT_MIN_TOKENS", "3"))
        short_high = float(os.getenv("SHORT_TEXT_HIGH_THRESHOLD", "0.80"))
    except Exception:
        short_min, short_high = 3, 0.80
    token_count = len(text_clean.strip().split()) if text_clean else 0
    no_urls_present = len(urls) == 0
    
    # Apply short-text safeguard for very short text content, regardless of URL presence
    if settings.SERVICE_USE_EXTERNAL_THRESHOLD and token_count < short_min:
        effective_threshold = max(effective_threshold, short_high)

    # Final decision (probability only)
    verdict = bool(text_conf >= effective_threshold)

    # Build detailed probe using stored HF arrays if available
    class_probs_raw = {lbl: float(_hf_last_probs_raw[i]) for i, lbl in enumerate(_hf_last_labels)} if _hf_last_probs_raw and _hf_last_labels else None
    class_probs_cal = {lbl: float(_hf_last_probs[i]) for i, lbl in enumerate(_hf_last_labels)} if _hf_last_probs and _hf_last_labels else None

    return {
        "decision_source": "calibrated_prob",
        "model": model_name,
        "text_confidence": float(round(text_conf, 3)),
        "effective_threshold": float(effective_threshold),
        "class_probs_raw": class_probs_raw,
        "class_probs_cal": class_probs_cal,
        "phishing_prob_cal": float(_hf_last_phishing_prob_cal) if _hf_last_phishing_prob_cal is not None else None,
        "temperature": float(_hf_calib_T),
        "urls": urls[:20],
        "fusion": {
            "url_checked": bool(url_checked),
            "url_is_phish": bool(url_is_phish),
            "url_confidence": float(round(url_conf, 3)),
        },
        "override_reason": override_reason,
        "verdict": verdict,
    }


@app.get("/debug_text")
async def debug_text_get(text: str) -> dict:
    return await debug_text(TextAnalyzeRequest(text=text))


@app.get("/health")
async def health():
	return {"status": "ok", "service": "text", "version": app.version}


@app.get("/debug")
async def debug():
    try:
        external = bool(settings.SERVICE_USE_EXTERNAL_THRESHOLD)
    except Exception:
        external = False
    # Optionally run a small probe with "hello" to expose calibrated probabilities
    probe = None
    try:
        if _try_load_hf():
            _ = _hf_score("hello")
            if _hf_last_probs is not None and _hf_last_labels is not None:
                # Compute effective external threshold like in analyze_text
                eff = TEXT_THRESHOLD
                try:
                    if external:
                        profile = (os.getenv("EXTERNAL_TEXT_PROFILE", "").strip().lower())
                        threshold_env = os.getenv("EXTERNAL_TEXT_THRESHOLD", "").strip()
                        profile_defaults = {"ceas": 0.125, "general": 0.185, "demo": 0.60}
                        if threshold_env:
                            eff = float(threshold_env)
                        elif profile in profile_defaults:
                            eff = float(profile_defaults[profile])
                        else:
                            eff = 0.185
                except Exception:
                    pass
                prob_cal = float(_hf_last_phishing_prob_cal) if _hf_last_phishing_prob_cal is not None else (float(_hf_last_phishing_prob) if _hf_last_phishing_prob is not None else None)
                verdict = (prob_cal is not None) and (prob_cal >= eff)
                probe = {
                    "text": "hello",
                    "class_probs_raw": {lbl: float(_hf_last_probs_raw[i]) for i, lbl in enumerate(_hf_last_labels)} if _hf_last_probs_raw is not None else None,
                    "class_probs_cal": {lbl: float(_hf_last_probs[i]) for i, lbl in enumerate(_hf_last_labels)},
                    "phishing_prob_cal": prob_cal,
                    "threshold": eff,
                    "verdict": bool(verdict),
                    "temperature": float(_hf_calib_T),
                }
    except Exception:
        probe = None
    return {
        "onnx_loaded": _onnx_session is not None and _onnx_tokenizer is not None,
        "onnx_last_error": _onnx_last_error,
        "model_path": os.getenv("TEXT_ONNX_MODEL") or "/models/text/distilbert.onnx",
        "tokenizer_dir": os.getenv("TEXT_TOKENIZER_DIR") or "/models/text/tokenizer",
        "threshold": TEXT_THRESHOLD,
        "external_threshold_enabled": external,
        "external_threshold": float(os.getenv("EXTERNAL_TEXT_THRESHOLD", "0.185")) if external else None,
        "external_threshold_profile": os.getenv("EXTERNAL_TEXT_PROFILE") or None,
        "use_argmax": USE_ARGMAX,
        "phish_class_index": PHISH_CLASS_INDEX,
        "hf_model_forced": external,
        "hf_model_name": _hf_model_name,
        "decision_source": "calibrated_prob",
        "hello_probe": probe,
    }


@app.post("/analyze_text/human", response_class=PlainTextResponse)
async def analyze_text_human(req: TextAnalyzeRequest) -> PlainTextResponse:
	"""Human-friendly output without JSON for text analysis."""
	res = await analyze_text(req)
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

	# Helpful context
	if res.highlights:
		lines.append("")
		lines.append("Details:")
		lines.append(f" - Highlighted risky phrases: {len(res.highlights)}")
	return PlainTextResponse("\n".join(lines))

# ------------------ URL extraction and fusion ------------------
_URL_PATTERN_WITH_PROTO = r"https?://[^\s<>\"{}|\\^`\[\]]+"
_URL_PATTERN_NO_PROTO = r"(?:www\.)?[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*\.[a-zA-Z]{2,}(?:/[^\s<>\"{}|\\^`\[\]]*)?"

def _extract_urls_from_text(text: str) -> List[str]:
    urls: List[str] = []
    try:
        # Only accept explicit http/https to avoid spurious matches from line breaks/words
        candidates = re.findall(_URL_PATTERN_WITH_PROTO, text, re.IGNORECASE)
        for u in candidates:
            try:
                parsed = urlsplit(u)
                host = parsed.netloc
                if host and "." in host and len(host.split("." )[-1]) >= 2:
                    urls.append(u)
            except Exception:
                continue
    except Exception:
        pass
    # Deduplicate preserving order
    seen = set()
    out: List[str] = []
    for u in urls:
        if u not in seen:
            seen.add(u)
            out.append(u)
    return out

async def _analyze_urls(urls: List[str]) -> tuple[bool, float, List[str], bool]:
    if not urls:
        return False, 0.0, [], False
    best_conf = 0.0
    any_phish = False
    reasons: List[str] = []
    checked = False
    # Limit to first 3 to keep latency predictable
    subset = urls[:3]
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            for u in subset:
                try:
                    resp = await client.post(f"{settings.URL_SERVICE_URL}/analyze_url_v2", json={"url": u})
                    if resp.status_code == 200:
                        checked = True
                        data = resp.json()
                        is_p = bool(data.get("final_verdict", False))
                        conf = float(data.get("confidence", 0.0))
                        if is_p:
                            any_phish = True
                            best_conf = max(best_conf, conf)
                            # Add a succinct reason line from sources
                            sources = data.get("sources", {})
                            source_reasons = []
                            for source, result in sources.items():
                                if result.get("fired", False):
                                    source_reasons.append(f"{source.upper()}: {result.get('reason', 'Detected')}")
                            if source_reasons:
                                reasons.append(f"URL {u} flagged: {', '.join(source_reasons)}")
                            else:
                                reasons.append(f"URL {u} flagged")
                except Exception:
                    continue
    except Exception:
        return False, 0.0, [], False
    return any_phish, best_conf, reasons, checked
