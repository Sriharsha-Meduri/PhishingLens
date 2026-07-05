import sys
import os

# Ensure the project root is in PYTHONPATH
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../"))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from fastapi import FastAPI, HTTPException, Request
from fastapi import Response
from fastapi.responses import PlainTextResponse
from backend.common.schemas import (
	TextAnalyzeRequest, TextAnalyzeResponse,
	UrlAnalyzeRequest,
	ImageAnalyzeRequest, ImageAnalyzeResponse,
	GraphCheckRequest, GraphCheckResponse,
)
from backend.common.config import settings
from backend.common.monitoring import (
    MonitoringMiddleware, HealthChecker, MetricsCollector,
    create_metrics_endpoint, create_health_endpoint, setup_logging
)
import httpx
import time

app = FastAPI(title="Phishing Detection Gateway", version="0.1.0")

# Setup monitoring
logger = setup_logging("gateway")
health_checker = HealthChecker("gateway", ["text", "url", "image", "graph"])

# Add monitoring middleware
app.middleware("http")(MonitoringMiddleware(app, "gateway"))

# Function-based CORS middleware (compatible across FastAPI/Starlette versions)
@app.middleware("http")
async def cors_middleware(request, call_next):
    if request.method == "OPTIONS":
        response = Response(status_code=204)
    else:
        response = await call_next(request)
    origin = request.headers.get("origin") or "*"
    acrh = request.headers.get("access-control-request-headers") or "*"
    response.headers["Access-Control-Allow-Origin"] = origin
    response.headers["Vary"] = "Origin"
    response.headers["Access-Control-Allow-Methods"] = "GET,POST,OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = acrh
    response.headers["Access-Control-Allow-Credentials"] = "false"
    response.headers["Access-Control-Max-Age"] = "86400"
    return response



@app.post("/analyze_text")
async def analyze_text(req: TextAnalyzeRequest):
	"""Analyze text for phishing indicators with monitoring."""
	start_time = time.time()
	
	try:
		# Allow longer timeout to accommodate first-time ONNX model load
		async with httpx.AsyncClient(timeout=30.0) as client:
			resp = await client.post(f"{settings.TEXT_SERVICE_URL}/analyze_text", json=req.model_dump())
			if resp.status_code != 200:
				raise HTTPException(status_code=resp.status_code, detail=resp.text)
			
			result = resp.json()
			
			# Extract values from text service response format
			hf_text = result.get("hf_text", {})
			urls = result.get("urls", [])
			final_verdict = result.get("final_verdict", False)
			
			# Determine if phishing based on text OR URLs
			text_is_phishing = hf_text.get("verdict_text", False) if hf_text else False
			url_is_phishing = any(bool(url.get("final_verdict", False)) for url in urls)
			is_phishing = text_is_phishing or url_is_phishing or final_verdict
			
			# Get confidence from text analysis
			confidence = hf_text.get("phishing_prob_cal", 0.0) if hf_text else 0.0
			
			# Build reasons list
			reasons = []
			if text_is_phishing:
				reasons.append("HF text model prediction")
			if url_is_phishing:
				reasons.append("URL analysis detected phishing")
			
			# Record metrics
			if is_phishing:
				MetricsCollector.record_phishing_detection("gateway", "text")
			else:
				MetricsCollector.record_legitimate_classification("gateway")
			
			# Record confidence
			MetricsCollector.record_model_confidence("gateway", "text", confidence)
			
			# Enhanced response for frontend with URL analysis
			simplified_result = {
				"text": req.text[:100] + "..." if len(req.text) > 100 else req.text,
				"is_phishing": is_phishing,
				"confidence": confidence,
				"model": "distilbert",
				"reasons": reasons,
				"url_analysis": urls,  # Include URL analysis results
				"text_analysis": hf_text,  # Include text analysis details
				"final_verdict": final_verdict
			}
			
			logger.info(f"Text analysis completed in {time.time() - start_time:.3f}s")
			return simplified_result
			
	except Exception as e:
		logger.error(f"Text analysis failed: {e}")
		raise


@app.post("/analyze_url")
async def analyze_url(req: UrlAnalyzeRequest):
	"""Analyze URL for phishing indicators with monitoring."""
	start_time = time.time()
	
	try:
		async with httpx.AsyncClient(timeout=20.0) as client:
			resp = await client.post(f"{settings.URL_SERVICE_URL}/analyze_url_v2", json=req.model_dump())
			if resp.status_code != 200:
				raise HTTPException(status_code=resp.status_code, detail=resp.text)
			
			result = resp.json()
			
			# Record metrics
			if result.get("is_phishing", False):
				MetricsCollector.record_phishing_detection("gateway", "url")
			else:
				MetricsCollector.record_legitimate_classification("gateway")
			
			# Record confidence
			confidence = result.get("confidence", 0.0)
			MetricsCollector.record_model_confidence("gateway", "url", confidence)
			
			logger.info(f"URL analysis completed in {time.time() - start_time:.3f}s")
			return result
			
	except Exception as e:
		logger.error(f"URL analysis failed: {e}")
		raise

@app.post("/analyze_url_v2")
async def analyze_url_v2(req: UrlAnalyzeRequest):
	"""Enhanced URL analysis with 4-source fusion."""
	start_time = time.time()
	
	try:
		async with httpx.AsyncClient(timeout=30.0) as client:
			resp = await client.post(f"{settings.URL_SERVICE_URL}/analyze_url_v2", json=req.model_dump())
			if resp.status_code != 200:
				raise HTTPException(status_code=resp.status_code, detail=resp.text)
			
			result = resp.json()
			
			# Record metrics
			if result.get("final_verdict", False):
				MetricsCollector.record_phishing_detection("gateway", "url_v2")
			else:
				MetricsCollector.record_legitimate_classification("gateway")
			
			# Record confidence
			confidence = result.get("confidence", 0.0)
			MetricsCollector.record_model_confidence("gateway", "url_v2", confidence)
			
			# Simplify response for frontend
			simplified_result = {
				"url": result.get("url", req.url),
				"final_verdict": result.get("final_verdict", False),
				"confidence": result.get("confidence", 0.0),
				"models": {
					"scanner": {
						"fired": result.get("sources", {}).get("scanner", {}).get("fired", False),
						"reasons": result.get("sources", {}).get("scanner", {}).get("reason", [])
					},
					"hf": {
						"fired": result.get("sources", {}).get("hf", {}).get("fired", False),
						"reasons": result.get("sources", {}).get("hf", {}).get("reason", [])
					},
					"graph": {
						"fired": result.get("sources", {}).get("graph", {}).get("fired", False),
						"reasons": result.get("sources", {}).get("graph", {}).get("reason", [])
					},
					"otx": {
						"fired": result.get("sources", {}).get("otx", {}).get("fired", False),
						"reasons": result.get("sources", {}).get("otx", {}).get("reason", [])
					}
				}
			}
			
			logger.info(f"Enhanced URL analysis completed in {time.time() - start_time:.3f}s")
			return simplified_result
			
	except Exception as e:
		logger.error(f"Enhanced URL analysis failed: {e}")
		raise


@app.post("/analyze_screenshot", response_model=ImageAnalyzeResponse)
async def analyze_screenshot(req: ImageAnalyzeRequest) -> ImageAnalyzeResponse:
	async with httpx.AsyncClient(timeout=30.0) as client:
		resp = await client.post(f"{settings.IMAGE_SERVICE_URL}/analyze_screenshot", json=req.model_dump())
		if resp.status_code != 200:
			raise HTTPException(status_code=resp.status_code, detail=resp.text)
		return ImageAnalyzeResponse(**resp.json())


@app.post("/analyze_image_v2")
async def analyze_image_v2(req: ImageAnalyzeRequest):
	"""Enhanced image analysis with brand detection, visual checks, and URL extraction."""
	async with httpx.AsyncClient(timeout=60.0) as client:
		resp = await client.post(f"{settings.IMAGE_SERVICE_URL}/analyze_image_v2", json=req.model_dump())
		if resp.status_code != 200:
			raise HTTPException(status_code=resp.status_code, detail=resp.text)
		
		result = resp.json()
		
		# Simplify response for frontend
		simplified_result = {
			"label": result.get("label", "unknown"),
			"confidence": result.get("confidence", 0.0),
			"is_phishing": result.get("label", "").lower() in ["phishing", "suspicious", "malicious"],
			"model": "mobilenet",
			"reasons": result.get("visual_reasons", []),
			"detected_brands": result.get("detected_brands", [])
		}
		
		return simplified_result


@app.post("/graph_check", response_model=GraphCheckResponse)
async def graph_check(req: GraphCheckRequest) -> GraphCheckResponse:
	async with httpx.AsyncClient(timeout=10.0) as client:
		resp = await client.post(f"{settings.GRAPH_SERVICE_URL}/graph_check", json=req.model_dump())
		if resp.status_code != 200:
			raise HTTPException(status_code=resp.status_code, detail=resp.text)
		return GraphCheckResponse(**resp.json())


@app.get("/health")
async def health():
	"""Enhanced health endpoint with dependency checks."""
	health_status = await health_checker.check_service_health()
	return health_status

@app.get("/metrics")
async def metrics():
	"""Prometheus metrics endpoint."""
	from backend.common.monitoring import generate_latest, CONTENT_TYPE_LATEST
	return PlainTextResponse(
		generate_latest(),
		media_type=CONTENT_TYPE_LATEST
	)


# Handle all CORS preflight requests explicitly (defensive)
@app.options("/{full_path:path}")
async def preflight(full_path: str) -> Response:
    return Response(status_code=204)


# ---------------- Human-friendly passthrough endpoints ----------------

@app.post("/analyze_text/human", response_class=PlainTextResponse)
async def analyze_text_human(req: TextAnalyzeRequest) -> str:
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(f"{settings.TEXT_SERVICE_URL}/analyze_text/human", json=req.model_dump())
        if resp.status_code != 200:
            raise HTTPException(status_code=resp.status_code, detail=resp.text)
        return resp.text


@app.post("/analyze_url/human", response_class=PlainTextResponse)
async def analyze_url_human(req: UrlAnalyzeRequest) -> str:
    async with httpx.AsyncClient(timeout=20.0) as client:
        resp = await client.post(f"{settings.URL_SERVICE_URL}/analyze_url/human", json=req.model_dump())
        if resp.status_code != 200:
            raise HTTPException(status_code=resp.status_code, detail=resp.text)
        return resp.text


@app.post("/analyze_screenshot/human", response_class=PlainTextResponse)
async def analyze_screenshot_human(req: ImageAnalyzeRequest) -> str:
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(f"{settings.IMAGE_SERVICE_URL}/analyze_screenshot/human", json=req.model_dump())
        if resp.status_code != 200:
            raise HTTPException(status_code=resp.status_code, detail=resp.text)
        return resp.text


@app.post("/analyze_image_v2/human", response_class=PlainTextResponse)
async def analyze_image_v2_human(req: ImageAnalyzeRequest) -> str:
    """Enhanced image analysis with human-friendly output."""
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(f"{settings.IMAGE_SERVICE_URL}/analyze_image_v2", json=req.model_dump())
        if resp.status_code != 200:
            raise HTTPException(status_code=resp.status_code, detail=resp.text)
        
        data = resp.json()
        
        # Format human-friendly output
        lines = []
        lines.append(f"🔍 Enhanced Image Analysis Results")
        lines.append("=" * 40)
        lines.append(f"🏷️  Label: {data.get('label', 'unknown').upper()}")
        lines.append(f"🎯 Confidence: {data.get('confidence', 0):.1%}")
        
        detected_brands = data.get('detected_brands', [])
        if detected_brands:
            lines.append(f"🏢 Detected Brands: {', '.join(detected_brands)}")
        
        visual_reasons = data.get('visual_reasons', [])
        if visual_reasons:
            lines.append(f"👁️  Visual Indicators:")
            for reason in visual_reasons:
                lines.append(f"   - {reason}")
        
        extracted_urls = data.get('extracted_urls', [])
        if extracted_urls:
            lines.append(f"🔗 Extracted URLs:")
            for url in extracted_urls:
                lines.append(f"   - {url}")
        
        url_analysis = data.get('url_analysis_results', [])
        if url_analysis:
            lines.append(f"🔍 URL Analysis:")
            for url_result in url_analysis:
                status = "🚨 PHISHING" if url_result.get('is_phishing') else "✅ BENIGN"
                lines.append(f"   - {url_result.get('url', 'unknown')}: {status}")
        
        timings = data.get('timings_ms', {})
        if timings:
            lines.append(f"\n⏱️  Performance:")
            for stage, time_ms in timings.items():
                lines.append(f"   - {stage}: {time_ms:.0f}ms")
        
        return "\n".join(lines)


@app.post("/graph_check/human", response_class=PlainTextResponse)
async def graph_check_human(req: GraphCheckRequest) -> str:
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(f"{settings.GRAPH_SERVICE_URL}/graph_check/human", json=req.model_dump())
        if resp.status_code != 200:
            raise HTTPException(status_code=resp.status_code, detail=resp.text)
        return resp.text