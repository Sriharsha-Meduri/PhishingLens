# Phishing Detection System API Documentation

## Overview

The Phishing Detection System provides a comprehensive API for detecting phishing attempts across multiple modalities: text, URLs, images, and graph analysis. The system is built with microservices architecture and provides real-time threat detection capabilities.

## Base URL

```
http://localhost:8000
```

## Authentication

Currently, the API does not require authentication. For production deployments, consider implementing API key authentication.

## Rate Limiting

- Default rate limit: 100 requests per minute per IP
- Burst limit: 200 requests per minute
- Rate limit headers are included in responses

## Endpoints

### 1. Text Analysis

Analyze text content for phishing indicators using advanced NLP models.

**Endpoint:** `POST /analyze_text`

**Request Body:**
```json
{
  "text": "Your account has been compromised. Click here to verify: http://fake-bank.com/login"
}
```

**Response:**
```json
{
  "is_phishing": true,
  "confidence": 0.95,
  "reasons": [
    "Urgent language detected",
    "Suspicious URL in text",
    "Account compromise claim"
  ],
  "model_info": {
    "model_type": "distilbert",
    "version": "v2.4.1",
    "threshold": 0.995
  },
  "processing_time_ms": 45
}
```

**Performance Target:** <50ms

### 2. URL Analysis

Analyze URLs for phishing indicators using multiple detection methods.

**Endpoint:** `POST /analyze_url`

**Request Body:**
```json
{
  "url": "http://fake-bank.com/login"
}
```

**Response:**
```json
{
  "is_phishing": true,
  "confidence": 0.87,
  "reasons": [
    "Suspicious domain structure",
    "High entropy in URL",
    "No SSL certificate"
  ],
  "features": {
    "length": 25,
    "entropy": 3.2,
    "has_ip": false,
    "suspicious_tld": false,
    "dns_a_records": 1,
    "ssl_days_to_expire": 30
  },
  "fusion_sources": {
    "scanner": 0.8,
    "hf_model": 0.9,
    "otx": 0.0,
    "graph": 0.7
  },
  "processing_time_ms": 78
}
```

**Performance Target:** <100ms

### 3. Image Analysis

Analyze screenshots and images for phishing indicators using computer vision.

**Endpoint:** `POST /analyze_screenshot`

**Request Body:**
```json
{
  "image_base64": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
}
```

**Response:**
```json
{
  "is_phishing": true,
  "confidence": 0.92,
  "reasons": [
    "Form layout detected",
    "Brand mismatch identified",
    "Warning overlay present"
  ],
  "detected_brands": ["paypal", "microsoft"],
  "visual_indicators": {
    "form_layout": 0.8,
    "color_mismatch": 0.6,
    "warning_overlay": 0.9
  },
  "extracted_urls": [
    "http://fake-paypal.com/login",
    "http://suspicious-site.com/verify"
  ],
  "url_analysis_results": [
    {
      "url": "http://fake-paypal.com/login",
      "is_phishing": true,
      "confidence": 0.95
    }
  ],
  "processing_time_ms": 156
}
```

**Performance Target:** <200ms

### 4. Enhanced Image Analysis (V2)

Advanced image analysis with brand detection and URL extraction.

**Endpoint:** `POST /analyze_image_v2`

**Request Body:** Same as `/analyze_screenshot`

**Response:**
```json
{
  "label": "phishing",
  "confidence": 0.94,
  "detected_brands": ["paypal"],
  "visual_reasons": [
    "Form layout detected",
    "Brand-domain mismatch",
    "Warning phrase detected"
  ],
  "extracted_urls": [
    "http://fake-paypal.com/login"
  ],
  "url_analysis_results": [
    {
      "url": "http://fake-paypal.com/login",
      "is_phishing": true,
      "confidence": 0.95,
      "sources": {
        "scanner": 0.8,
        "hf": 0.9,
        "otx": 0.0
      }
    }
  ],
  "timings_ms": {
    "preprocessing": 15,
    "brand_detection": 45,
    "visual_checks": 30,
    "url_extraction": 25,
    "url_fusion": 41
  },
  "features": {
    "brand_detection": true,
    "visual_checks": true,
    "url_extraction": true,
    "url_fusion": true
  }
}
```

### 5. Graph Analysis

Analyze relationships and patterns in data using graph neural networks.

**Endpoint:** `POST /graph_check`

**Request Body:**
```json
{
  "nodes": ["user1", "user2", "suspicious_domain"],
  "edges": [
    {"from": "user1", "to": "user2", "type": "communication"},
    {"from": "user2", "to": "suspicious_domain", "type": "access"}
  ]
}
```

**Response:**
```json
{
  "is_phishing": true,
  "confidence": 0.88,
  "anomaly_score": 0.75,
  "patterns_detected": [
    "Suspicious communication pattern",
    "Unusual access pattern to domain"
  ],
  "processing_time_ms": 67
}
```

## Health and Monitoring Endpoints

### Health Check

**Endpoint:** `GET /health`

**Response:**
```json
{
  "service": "gateway",
  "status": "healthy",
  "timestamp": 1640995200.0,
  "dependencies": {
    "text": {
      "healthy": true,
      "version": "0.1.0",
      "response_time": 0.045
    },
    "url": {
      "healthy": true,
      "version": "0.1.0",
      "response_time": 0.078
    },
    "image": {
      "healthy": true,
      "version": "0.1.0",
      "response_time": 0.156
    },
    "graph": {
      "healthy": true,
      "version": "0.1.0",
      "response_time": 0.067
    }
  },
  "issues": []
}
```

### Metrics

**Endpoint:** `GET /metrics`

Returns Prometheus-formatted metrics for monitoring.

## Error Responses

### 400 Bad Request
```json
{
  "detail": "Invalid request format"
}
```

### 422 Validation Error
```json
{
  "detail": [
    {
      "loc": ["body", "text"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

### 500 Internal Server Error
```json
{
  "detail": "Internal server error"
}
```

### 503 Service Unavailable
```json
{
  "detail": "Service temporarily unavailable"
}
```

## Performance Metrics

The system tracks the following performance metrics:

- **Response Time**: Average, median, 95th percentile, 99th percentile
- **Throughput**: Requests per second
- **Error Rate**: Percentage of failed requests
- **Model Performance**: Accuracy, precision, recall, F1-score
- **Resource Usage**: CPU, memory, disk usage

## Rate Limiting

Rate limiting is implemented to prevent abuse:

- **Text Analysis**: 100 requests/minute
- **URL Analysis**: 100 requests/minute  
- **Image Analysis**: 50 requests/minute
- **Graph Analysis**: 100 requests/minute

Rate limit headers:
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1640995260
```

## CORS Support

The API supports Cross-Origin Resource Sharing (CORS) for web applications:

- **Allowed Origins**: All origins (*)
- **Allowed Methods**: GET, POST, OPTIONS
- **Allowed Headers**: Content-Type, Authorization
- **Max Age**: 86400 seconds (24 hours)

## SDK Examples

### Python
```python
import requests

# Text analysis
response = requests.post(
    "http://localhost:8000/analyze_text",
    json={"text": "Your account has been compromised. Click here to verify."}
)
result = response.json()
print(f"Phishing: {result['is_phishing']}, Confidence: {result['confidence']}")
```

### JavaScript
```javascript
// URL analysis
const response = await fetch('http://localhost:8000/analyze_url', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    url: 'http://fake-bank.com/login'
  })
});

const result = await response.json();
console.log(`Phishing: ${result.is_phishing}, Confidence: ${result.confidence}`);
```

### cURL
```bash
# Image analysis
curl -X POST "http://localhost:8000/analyze_screenshot" \
  -H "Content-Type: application/json" \
  -d '{
    "image_base64": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
  }'
```

## Monitoring and Observability

The API provides comprehensive monitoring capabilities:

- **Health Checks**: Service and dependency health status
- **Metrics**: Prometheus-compatible metrics
- **Logging**: Structured logging with correlation IDs
- **Tracing**: Distributed tracing for request flows
- **Alerting**: Automated alerts for service issues

Access monitoring dashboards:
- **Prometheus**: http://localhost:9090
- **Grafana**: http://localhost:3000 (admin/admin123)

## Best Practices

1. **Request Timeouts**: Set appropriate timeouts (30s for text, 20s for URL, 60s for image)
2. **Error Handling**: Implement retry logic with exponential backoff
3. **Caching**: Cache results for identical requests when appropriate
4. **Batch Processing**: Use batch endpoints for multiple analyses
5. **Monitoring**: Monitor response times and error rates
6. **Security**: Validate and sanitize all inputs
7. **Rate Limiting**: Respect rate limits and implement client-side throttling

## Support

For technical support or questions:
- **Documentation**: See `/docs` directory
- **Issues**: Report issues in the project repository
- **Monitoring**: Check service health at `/health` endpoint
