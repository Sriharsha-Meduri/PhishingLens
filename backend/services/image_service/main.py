from fastapi import FastAPI
from fastapi.responses import PlainTextResponse
from backend.common.schemas import ImageAnalyzeRequest, ImageAnalyzeResponse
from pydantic import BaseModel
from typing import Dict, List, Optional, Any
import base64
import io
import logging
from PIL import Image
import numpy as np
import cv2
import os
import requests
import re
import httpx
import sys
import time
import logging

# Import new modules
from .brand_detector import brand_detector
from .visual_checks import visual_checker
from .preprocessor import preprocessor
from .url_extractor import url_extractor

# Ensure the project root is in PYTHONPATH
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../"))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

try:
	import onnxruntime as ort
except Exception:
	ort = None

# OCR availability flag
_ocr_available = False
_tess_last_error = None

logger = logging.getLogger("image_service")
app = FastAPI(title="Image Analysis Service", version="0.2.0")

# Feature flags
FEATURE_BRAND_DETECTION = os.getenv("FEATURE_BRAND_DETECTION", "false").lower() == "true"
FEATURE_VISUAL_CHECKS = os.getenv("FEATURE_VISUAL_CHECKS", "false").lower() == "true"
FEATURE_URL_EXTRACTION = os.getenv("FEATURE_URL_EXTRACTION", "false").lower() == "true"
FEATURE_URL_FUSION_INTEGRATION = os.getenv("FEATURE_URL_FUSION_INTEGRATION", "false").lower() == "true"
TIMEOUT_MS = int(os.getenv("TIMEOUT_MS", "1200"))

# Enhanced response schemas
class ImageAnalyzeV2Response(BaseModel):
    label: str  # "phishing" or "benign"
    confidence: float
    detected_brands: List[str]
    visual_reasons: List[str]
    extracted_urls: List[str]
    url_analysis_results: List[Dict[str, Any]]
    timings_ms: Dict[str, float]
    meta: Dict[str, Any]
    # Frontend-expected fields
    is_phishing: Optional[bool] = None
    final_verdict: Optional[bool] = None

# Telemetry counters
telemetry = {
    "images_processed": 0,
    "brand_hits": 0,
    "visual_form_hits": 0,
    "url_extracted": 0,
    "url_fusion_calls": 0,
    "degraded_runs": 0
}


def load_image(req: ImageAnalyzeRequest) -> Image.Image | None:
	if req.image_base64:
		try:
			data = base64.b64decode(req.image_base64)
			return Image.open(io.BytesIO(data)).convert("RGB")
		except Exception:
			return None
	if req.image_url:
		try:
			r = requests.get(req.image_url, timeout=8)
			r.raise_for_status()
			return Image.open(io.BytesIO(r.content)).convert("RGB")
		except Exception:
			return None
	return None


def extract_text_with_ocr(img: Image.Image) -> str:
	"""Extract text from image using OCR."""
	global _ocr_available, _tess_last_error
	try:
		import pytesseract
		# Allow explicit Tesseract path via env var
		_tess_cmd = os.getenv("TESSERACT_CMD") or os.getenv("PYTESSERACT_CMD")
		# Auto-detect common Windows install paths if not provided
		if not _tess_cmd and os.name == "nt":
			_candidates = [
				"C:\\Program Files\\Tesseract-OCR\\tesseract.exe",
				"C:\\Program Files (x86)\\Tesseract-OCR\\tesseract.exe",
			]
			for c in _candidates:
				if os.path.exists(c):
					_tess_cmd = c
					break
		if _tess_cmd:
			pytesseract.pytesseract.tesseract_cmd = _tess_cmd
		# Configure tesseract for better text extraction
		custom_config = r'--oem 3 --psm 6'
		text = pytesseract.image_to_string(img, config=custom_config)
		_ocr_available = True
		_tess_last_error = None
		return (text or "").strip()
	except Exception as e:
		_ocr_available = False
		_tess_last_error = str(e)
		# Fallback: simple text detection using OpenCV
		try:
			gray = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2GRAY)
			# No OCR, but basic detection succeeded
			return "OCR not available - using basic detection"
		except Exception:
			return ""


def extract_urls_from_text(text: str) -> list[str]:
    """Extract URLs from OCR text."""
    # Pattern for URLs with protocol
    url_pattern_with_protocol = r'https?://[^\s<>"{}|\\^`\[\]]+'
    # Pattern for URLs without protocol (domain.tld/path)
    url_pattern_without_protocol = r'(?:www\.)?[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*\.[a-zA-Z]{2,}(?:/[^\s<>"{}|\\^`\[\]]*)?'
    
    urls = []
    # Find URLs with protocol
    urls.extend(re.findall(url_pattern_with_protocol, text, re.IGNORECASE))
    # Find URLs without protocol
    urls_without_protocol = re.findall(url_pattern_without_protocol, text, re.IGNORECASE)
    # Add https:// prefix to URLs without protocol
    for url in urls_without_protocol:
        if not url.startswith(('http://', 'https://')):
            urls.append(f"https://{url}")
    
    return urls


async def analyze_urls_from_screenshot(urls: list[str]) -> Dict[str, any]:
    """Analyze extracted URLs using URL service."""
    if not urls:
        return {"urls_analyzed": 0, "phishing_urls": [], "results": []}
    
    results = []
    phishing_urls = []
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        for url in urls[:3]:  # Limit to first 3 URLs to avoid timeout
            try:
                response = await client.post(
                    "http://url:8002/analyze_url_v2",
                    json={"url": url}
                )
                if response.status_code == 200:
                    data = response.json()
                    results.append({
                        "url": url,
                        "is_phishing": data.get("is_phishing", False),
                        "confidence": data.get("confidence", 0.0),
                        "reasons": data.get("reasons", [])
                    })
                    if data.get("is_phishing", False):
                        phishing_urls.append(url)
            except Exception:
                continue
    
    return {
        "urls_analyzed": len(results),
        "phishing_urls": phishing_urls,
        "results": results
    }


def compute_metrics(img: Image.Image) -> Dict[str, float]:
	arr = np.array(img)
	gray = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)
	edges = cv2.Canny(gray, 100, 200)
	edge_density = float(edges.mean() / 255.0)
	# text-ish density via adaptive threshold as proxy
	th = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY_INV, 15, 10)
	text_density = float(th.mean() / 255.0)
	color_std = float(arr.std() / 255.0)
	return {
		"edge_density": round(edge_density, 4),
		"text_density": round(text_density, 4),
		"color_std": round(color_std, 4),
	}


def detect_phishing_visual_cues(img: Image.Image) -> Dict[str, float]:
    """Detect visual phishing indicators."""
    arr = np.array(img)
    gray = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)
    
    # Detect overlays and popups
    overlay_score = 0.0
    if arr.shape[0] > 100 and arr.shape[1] > 100:
        # Check for modal-like structures (dark borders, centered content)
        edges = cv2.Canny(gray, 50, 150)
        edge_density = np.mean(edges) / 255.0
        if edge_density > 0.1:
            overlay_score += 0.2
    
    # Detect suspicious color patterns (often used in phishing)
    color_variance = float(np.std(arr) / 255.0)
    suspicious_colors = 0.0
    if color_variance < 0.15:  # Low color variation might indicate template
        suspicious_colors += 0.3
    
    # Detect text density (phishing pages often have lots of text)
    text_mask = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY_INV, 11, 2)
    text_density = float(np.mean(text_mask) / 255.0)
    
    return {
        "overlay_score": round(overlay_score, 4),
        "suspicious_colors": round(suspicious_colors, 4),
        "text_density": round(text_density, 4),
        "visual_risk_score": round(overlay_score + suspicious_colors + (text_density * 0.3), 4)
    }


def score(metrics: Dict[str, float]) -> tuple[float, list[str]]:
	score = 0.0
	reasons: list[str] = []
	if metrics["text_density"] > 0.35:
		score += 0.25; reasons.append("High overlay text density")
	if metrics["edge_density"] > 0.2:
		score += 0.2; reasons.append("High edge density")
	if metrics["color_std"] < 0.12:
		score += 0.15; reasons.append("Low color variation (template-like)")
	
	# Add visual phishing cues
	if "visual_risk_score" in metrics and metrics["visual_risk_score"] > 0.4:
		score += 0.3; reasons.append("High visual phishing indicators")
	
	confidence = min(1.0, score)
	return confidence, reasons


def try_onnx_logits(arr: np.ndarray):
    if ort is None:
        return None
    model_path = os.getenv("IMAGE_ONNX_MODEL", "/models/image/tiny_cnn.onnx")
    if not os.path.exists(model_path):
        return None
    try:
        providers_env = os.getenv("ORT_PROVIDERS", "CPUExecutionProvider").split(",")
        providers = [p.strip() for p in providers_env if p.strip()]
        sess = ort.InferenceSession(model_path, providers=providers)
        # Expecting [N, C, H, W] float32 in [0,1]. Resize to 224.
        img = cv2.resize(arr, (224, 224))
        x = (img.astype("float32") / 255.0)
        x = np.transpose(x, (2, 0, 1))[None, ...]
        out = sess.run(None, {sess.get_inputs()[0].name: x})
        return out[0]
    except Exception:
        return None


@app.post("/analyze_screenshot", response_model=ImageAnalyzeResponse)
async def analyze_image(req: ImageAnalyzeRequest) -> ImageAnalyzeResponse:
	img = load_image(req)
	if img is None:
		return ImageAnalyzeResponse(is_phishing=False, confidence=0.0, reasons=["Invalid or missing image"], metrics={})
	
	# Extract text and URLs from screenshot
	extracted_text = extract_text_with_ocr(img)
	urls = extract_urls_from_text(extracted_text)
	url_analysis = await analyze_urls_from_screenshot(urls)
	
	metrics = compute_metrics(img)
	visual_cues = detect_phishing_visual_cues(img)
	metrics.update(visual_cues)
	
	# Try ONNX model first
	logits = try_onnx_logits(np.array(img))
	reasons = []
	base_confidence = 0.0
	
	if logits is not None:
		probs = np.exp(logits) / np.sum(np.exp(logits), axis=-1, keepdims=True)
		p = float(probs[0, 1]) if probs.ndim == 2 and probs.shape[1] >= 2 else float(probs.squeeze())
		reasons.append("Visual model signal")
		base_confidence = p
	else:
		base_confidence, heuristic_reasons = score(metrics)
		reasons.extend(heuristic_reasons)
	
	# Add visual cues reasons
	if visual_cues.get("visual_risk_score", 0) > 0.4:
		reasons.append("High visual phishing indicators")
	
	# Boost confidence if URLs in screenshot are phishing
	confidence = base_confidence
	if url_analysis["phishing_urls"]:
		confidence = min(1.0, confidence + 0.4)
		reasons.append(f"Phishing URLs detected in screenshot: {', '.join(url_analysis['phishing_urls'])}")
	
	# Add URL analysis to metrics
	metrics["extracted_text"] = extracted_text[:200]  # First 200 chars
	metrics["urls_found"] = len(urls)
	metrics["phishing_urls_count"] = len(url_analysis["phishing_urls"])
	metrics["visual_risk_score"] = visual_cues.get("visual_risk_score", 0)
	
	return ImageAnalyzeResponse(is_phishing=confidence >= 0.5, confidence=float(round(confidence, 3)), reasons=reasons[:5], metrics=metrics)


@app.get("/health")
async def health():
    return {"status": "ok", "service": "image", "version": app.version}


@app.get("/debug")
async def debug():
	# Report actual OCR availability and tesseract path if set
	try:
		import pytesseract  # type: ignore
		tess_cmd = getattr(pytesseract.pytesseract, "tesseract_cmd", None)
	except Exception:
		tess_cmd = None
	return {
		"ocr_available": bool(_ocr_available),
		"tesseract_cmd": tess_cmd or os.getenv("TESSERACT_CMD") or None,
		"tesseract_last_error": _tess_last_error,
		"url_service_url": "http://url:8002/analyze_url_v2",
		"features": [
			"OCR text extraction",
			"URL detection from text",
			"URL analysis integration",
			"Visual phishing cues",
			"Template detection"
		]
	}


@app.post("/analyze_screenshot/human", response_class=PlainTextResponse)
async def analyze_image_human(req: ImageAnalyzeRequest) -> PlainTextResponse:
	"""Human-friendly output without JSON."""
	result = await analyze_image(req)
	# Invalid image case
	if any("Invalid or missing image" in r for r in result.reasons):
		message = "Unable to analyze the image: invalid or missing image."
		return PlainTextResponse(message)

	confidence_pct = int(round(result.confidence * 100))
	lines: list[str] = []
	if result.is_phishing:
		lines.append(f"\u26a0\ufe0f  Phishing suspected — Confidence: {confidence_pct}%")
		if result.reasons:
			lines.append("")
			lines.append("Why we think it's risky:")
			for reason in result.reasons[:5]:
				lines.append(f" - {reason}")
	else:
		lines.append(f"\u2705  Looks safe — Confidence: {confidence_pct}%")
		if result.reasons:
			lines.append("")
			lines.append("Notes:")
			for reason in result.reasons[:5]:
				lines.append(f" - {reason}")

	# Helpful context (non-JSON)
	urls_found = result.metrics.get("urls_found", 0)
	phish_count = result.metrics.get("phishing_urls_count", 0)
	visual_risk = result.metrics.get("visual_risk_score", 0)
	lines.append("")
	lines.append("Details:")
	lines.append(f" - URLs detected in screenshot: {urls_found}")
	if phish_count:
		lines.append(f" - Known phishing links detected: {phish_count}")
	lines.append(f" - Visual risk indicators score: {visual_risk}")

	return PlainTextResponse("\n".join(lines))


@app.post("/analyze_image_v2", response_model=ImageAnalyzeV2Response)
async def analyze_image_v2(req: ImageAnalyzeRequest) -> ImageAnalyzeV2Response:
	"""
	Enhanced image analysis with brand detection, visual checks, and URL extraction.
	"""
	start_time = time.time()
	telemetry["images_processed"] += 1
	
	# Load image
	img = load_image(req)
	if img is None:
		return ImageAnalyzeV2Response(
			label="benign",
			confidence=0.0,
			detected_brands=[],
			visual_reasons=["Invalid or missing image"],
			extracted_urls=[],
			url_analysis_results=[],
			timings_ms={"total": 0},
			meta={"feature_flags": {}, "degraded": True},
			# Frontend-expected fields
			is_phishing=False,
			final_verdict=False
		)
	
	timings = {}
	detected_brands = []
	visual_reasons = []
	extracted_urls = []
	url_analysis_results = []
	visual_score = 0.0
	confidence = 0.0
	meta = {
		"feature_flags": {
			"brand_detection": FEATURE_BRAND_DETECTION,
			"visual_checks": FEATURE_VISUAL_CHECKS,
			"url_extraction": FEATURE_URL_EXTRACTION,
			"url_fusion": FEATURE_URL_FUSION_INTEGRATION
		},
		"degraded": False
	}
	
	try:
		# 1. Preprocessing
		preprocess_start = time.time()
		preprocessed = preprocessor.preprocess_for_ocr(img)
		timings["preprocessing"] = (time.time() - preprocess_start) * 1000
		
		# 2. Brand detection (if enabled)
		if FEATURE_BRAND_DETECTION:
			brand_start = time.time()
			brand_results = brand_detector.detect_brands(img)
			detected_brands = brand_results.get("detected_brands", [])
			if brand_results.get("degraded"):
				meta["degraded"] = True
				telemetry["degraded_runs"] += 1
			if detected_brands:
				telemetry["brand_hits"] += 1
			timings["brand_detection"] = (time.time() - brand_start) * 1000
		
		# 3. Visual checks (if enabled)
		if FEATURE_VISUAL_CHECKS:
			visual_start = time.time()
			visual_results = visual_checker.check_visual_indicators(
				img, detected_brands, ""
			)
			visual_score = visual_results.get("visual_score", 0.0)
			visual_reasons = visual_results.get("reasons", [])
			if visual_results.get("breakdown", {}).get("form_layout", 0) > 0:
				telemetry["visual_form_hits"] += 1
			timings["visual_checks"] = (time.time() - visual_start) * 1000
		
		# 4. URL extraction (if enabled)
		if FEATURE_URL_EXTRACTION:
			url_start = time.time()
			url_results = url_extractor.extract_urls(
				preprocessed["processed_image"],
				preprocessed.get("text_regions", [])
			)
			extracted_urls = url_results.get("urls", [])
			ocr_text = url_results.get("ocr_text", "")
			if extracted_urls:
				telemetry["url_extracted"] += 1
			timings["url_extraction"] = (time.time() - url_start) * 1000
			
			# 5. URL analysis with fusion (if enabled)
			if FEATURE_URL_FUSION_INTEGRATION and extracted_urls:
				fusion_start = time.time()
				url_analysis_results = await analyze_urls_with_fusion(extracted_urls)
				telemetry["url_fusion_calls"] += len(extracted_urls)
				timings["url_fusion"] = (time.time() - fusion_start) * 1000
		
		# 6. Calculate final confidence and decision
		confidence = visual_score
		
		# Boost confidence if URLs are phishing
		if url_analysis_results:
			phishing_urls = [r for r in url_analysis_results if r.get("is_phishing", False)]
			if phishing_urls:
				max_url_confidence = max(r.get("confidence", 0) for r in phishing_urls)
				confidence = max(confidence, max_url_confidence)
				visual_reasons.append(f"Phishing URLs detected: {len(phishing_urls)} (confidence: {max_url_confidence:.3f})")
		
		# Brand-domain mismatch check
		if detected_brands and extracted_urls:
			brand_risk = brand_detector.check_brand_domain_mismatch(
				detected_brands, ocr_text, extracted_urls
			)
			if brand_risk > 0:
				confidence = max(confidence, brand_risk)
				visual_reasons.append("Brand-domain mismatch detected")
		
		# Final decision - if any URL is phishing, mark as phishing
		has_phishing_urls = any(r.get("is_phishing", False) for r in url_analysis_results) if url_analysis_results else False
		label = "phishing" if (confidence >= 0.6 or has_phishing_urls) else "benign"
		
		timings["total"] = (time.time() - start_time) * 1000
		
		# Convert label to frontend-expected fields
		is_phishing = (label == "phishing")
		final_verdict = is_phishing
		
		return ImageAnalyzeV2Response(
			label=label,
			confidence=round(confidence, 3),
			detected_brands=detected_brands,
			visual_reasons=visual_reasons,
			extracted_urls=extracted_urls,
			url_analysis_results=url_analysis_results,
			timings_ms=timings,
			meta=meta,
			# Add frontend-expected fields
			is_phishing=is_phishing,
			final_verdict=final_verdict
		)
		
	except Exception as e:
		logger.error(f"Enhanced image analysis failed: {e}")
		telemetry["degraded_runs"] += 1
		return ImageAnalyzeV2Response(
			label="benign",
			confidence=0.0,
			detected_brands=[],
			visual_reasons=[f"Analysis failed: {str(e)}"],
			extracted_urls=[],
			url_analysis_results=[],
			timings_ms={"total": (time.time() - start_time) * 1000},
			meta={**meta, "degraded": True, "error": str(e)},
			# Frontend-expected fields
			is_phishing=False,
			final_verdict=False
		)


async def analyze_urls_with_fusion(urls: List[str]) -> List[Dict[str, Any]]:
	"""Analyze URLs using the fusion endpoint."""
	if not urls:
		return []
	
	results = []
	async with httpx.AsyncClient(timeout=10.0) as client:
		for url in urls:
			try:
				response = await client.post(
					"http://url:8002/analyze_url_v2",
					json={"url": url}
				)
				if response.status_code == 200:
					data = response.json()
					results.append({
						"url": url,
						"is_phishing": data.get("final_verdict", False),
						"confidence": data.get("confidence", 0.0),
						"reasons": data.get("reasons", []),
						"fusion_sources": data.get("sources", {}),
						"final_verdict": data.get("final_verdict", False),
						"sources": data.get("sources", {})
					})
			except Exception as e:
				logger.warning(f"URL fusion analysis failed for {url}: {e}")
				continue
	
	return results


@app.get("/health")
async def health_v2():
	"""Enhanced health endpoint with feature status."""
	return {
		"status": "ok",
		"service": "image_v2",
		"version": app.version,
		"features": {
			"brand_detection": FEATURE_BRAND_DETECTION,
			"visual_checks": FEATURE_VISUAL_CHECKS,
			"url_extraction": FEATURE_URL_EXTRACTION,
			"url_fusion": FEATURE_URL_FUSION_INTEGRATION
		},
		"telemetry": telemetry,
		"degraded": any([
			brand_detector.degraded,
			not visual_checker.enabled,
			not url_extractor.ocr_available
		])
	}


@app.get("/debug_image_v2")
async def debug_image_v2():
	"""Debug endpoint showing intermediate artifacts and configuration."""
	return {
		"feature_flags": {
			"FEATURE_BRAND_DETECTION": FEATURE_BRAND_DETECTION,
			"FEATURE_VISUAL_CHECKS": FEATURE_VISUAL_CHECKS,
			"FEATURE_URL_EXTRACTION": FEATURE_URL_EXTRACTION,
			"FEATURE_URL_FUSION_INTEGRATION": FEATURE_URL_FUSION_INTEGRATION
		},
		"model_status": {
			"brand_detector_loaded": brand_detector.model_loaded,
			"brand_detector_degraded": brand_detector.degraded,
			"visual_checker_enabled": visual_checker.enabled,
			"url_extractor_available": url_extractor.ocr_available,
			"ocr_engine": url_extractor.ocr_engine
		},
		"telemetry": telemetry,
		"timeout_ms": TIMEOUT_MS,
		"brand_domains_count": len(brand_detector.BRAND_DOMAINS),
		"warning_phrases_count": len(visual_checker.WARNING_PHRASES)
	}
