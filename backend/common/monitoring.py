"""
Monitoring utilities for the phishing detection system.
Provides Prometheus metrics, health checks, and logging.
"""

import time
import logging
from typing import Dict, Any, Optional
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
from fastapi import Request, Response
from fastapi.responses import PlainTextResponse
import asyncio
import httpx

# Prometheus metrics
REQUEST_COUNT = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status_code', 'service']
)

REQUEST_DURATION = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration in seconds',
    ['method', 'endpoint', 'service'],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
)

PHISHING_DETECTIONS = Counter(
    'phishing_detections_total',
    'Total phishing detections',
    ['service', 'detection_type']
)

LEGITIMATE_CLASSIFICATIONS = Counter(
    'legitimate_classifications_total',
    'Total legitimate classifications',
    ['service']
)

MODEL_CONFIDENCE = Histogram(
    'model_confidence_score',
    'Model confidence scores',
    ['service', 'model_type'],
    buckets=[0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
)

MODEL_ACCURACY = Gauge(
    'model_accuracy',
    'Current model accuracy',
    ['service', 'model_type']
)

SERVICE_HEALTH = Gauge(
    'service_health_status',
    'Service health status (1=healthy, 0=unhealthy)',
    ['service']
)

CONTINUOUS_LEARNING_RETRAIN = Counter(
    'continuous_learning_retrain_events_total',
    'Total continuous learning retrain events',
    ['status']
)

CONTINUOUS_LEARNING_DATA_FETCH = Counter(
    'continuous_learning_data_fetch_events_total',
    'Total continuous learning data fetch events',
    ['source']
)

CONTINUOUS_LEARNING_PERFORMANCE = Gauge(
    'continuous_learning_model_performance',
    'Continuous learning model performance',
    ['metric']
)

# Service dependencies for health checks
SERVICE_DEPENDENCIES = {
    'gateway': ['text', 'url', 'image', 'graph'],
    'text': [],
    'url': [],
    'image': [],
    'graph': []
}

class MonitoringMiddleware:
    """FastAPI middleware for request monitoring."""
    
    def __init__(self, app, service_name: str):
        self.app = app
        self.service_name = service_name
    
    async def __call__(self, request: Request, call_next):
        start_time = time.time()
        
        # Extract endpoint info
        method = request.method
        endpoint = request.url.path
        if endpoint.startswith('/'):
            endpoint = endpoint[1:]
        
        try:
            response = await call_next(request)
            status_code = str(response.status_code)
            
            # Record metrics
            REQUEST_COUNT.labels(
                method=method,
                endpoint=endpoint,
                status_code=status_code,
                service=self.service_name
            ).inc()
            
            REQUEST_DURATION.labels(
                method=method,
                endpoint=endpoint,
                service=self.service_name
            ).observe(time.time() - start_time)
            
            return response
            
        except Exception as e:
            # Record error metrics
            REQUEST_COUNT.labels(
                method=method,
                endpoint=endpoint,
                status_code="500",
                service=self.service_name
            ).inc()
            
            REQUEST_DURATION.labels(
                method=method,
                endpoint=endpoint,
                service=self.service_name
            ).observe(time.time() - start_time)
            
            raise

class HealthChecker:
    """Health check utilities for services."""
    
    def __init__(self, service_name: str, dependencies: list = None):
        self.service_name = service_name
        self.dependencies = dependencies or []
        self.logger = logging.getLogger(f"health.{service_name}")
    
    async def check_service_health(self) -> Dict[str, Any]:
        """Check the health of this service and its dependencies."""
        health_status = {
            "service": self.service_name,
            "status": "healthy",
            "timestamp": time.time(),
            "dependencies": {},
            "issues": []
        }
        
        # Check dependencies
        for dep in self.dependencies:
            try:
                dep_health = await self._check_dependency(dep)
                health_status["dependencies"][dep] = dep_health
                
                if not dep_health.get("healthy", False):
                    health_status["issues"].append(f"Dependency {dep} is unhealthy")
                    health_status["status"] = "degraded"
                    
            except Exception as e:
                health_status["dependencies"][dep] = {"healthy": False, "error": str(e)}
                health_status["issues"].append(f"Dependency {dep} check failed: {e}")
                health_status["status"] = "unhealthy"
        
        # Update Prometheus metric
        SERVICE_HEALTH.labels(service=self.service_name).set(
            1 if health_status["status"] == "healthy" else 0
        )
        
        return health_status
    
    async def _check_dependency(self, dependency: str) -> Dict[str, Any]:
        """Check a specific dependency."""
        try:
            # Map dependency names to URLs
            dep_urls = {
                'text': 'http://text:8001',
                'url': 'http://url:8002', 
                'image': 'http://image:8003',
                'graph': 'http://graph:8004'
            }
            
            if dependency not in dep_urls:
                return {"healthy": False, "error": "Unknown dependency"}
            
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{dep_urls[dependency]}/health")
                
                if response.status_code == 200:
                    data = response.json()
                    return {
                        "healthy": data.get("status") == "ok",
                        "version": data.get("version"),
                        "response_time": response.elapsed.total_seconds()
                    }
                else:
                    return {"healthy": False, "error": f"HTTP {response.status_code}"}
                    
        except Exception as e:
            return {"healthy": False, "error": str(e)}

class MetricsCollector:
    """Collect and expose Prometheus metrics."""
    
    @staticmethod
    def record_phishing_detection(service: str, detection_type: str = "unknown"):
        """Record a phishing detection."""
        PHISHING_DETECTIONS.labels(
            service=service,
            detection_type=detection_type
        ).inc()
    
    @staticmethod
    def record_legitimate_classification(service: str):
        """Record a legitimate classification."""
        LEGITIMATE_CLASSIFICATIONS.labels(service=service).inc()
    
    @staticmethod
    def record_model_confidence(service: str, model_type: str, confidence: float):
        """Record model confidence score."""
        MODEL_CONFIDENCE.labels(
            service=service,
            model_type=model_type
        ).observe(confidence)
    
    @staticmethod
    def update_model_accuracy(service: str, model_type: str, accuracy: float):
        """Update model accuracy metric."""
        MODEL_ACCURACY.labels(
            service=service,
            model_type=model_type
        ).set(accuracy)
    
    @staticmethod
    def record_continuous_learning_event(event_type: str, status: str):
        """Record continuous learning events."""
        if event_type == "retrain":
            CONTINUOUS_LEARNING_RETRAIN.labels(status=status).inc()
        elif event_type == "data_fetch":
            CONTINUOUS_LEARNING_DATA_FETCH.labels(source=status).inc()
    
    @staticmethod
    def update_continuous_learning_performance(metric: str, value: float):
        """Update continuous learning performance metrics."""
        CONTINUOUS_LEARNING_PERFORMANCE.labels(metric=metric).set(value)

def create_metrics_endpoint():
    """Create a FastAPI endpoint for Prometheus metrics."""
    async def metrics():
        return PlainTextResponse(
            generate_latest(),
            media_type=CONTENT_TYPE_LATEST
        )
    return metrics

def create_health_endpoint(health_checker: HealthChecker):
    """Create a FastAPI health endpoint."""
    async def health():
        return await health_checker.check_service_health()
    return health

# Logging configuration
def setup_logging(service_name: str, log_level: str = "INFO") -> logging.Logger:
    """Set up structured logging for a service."""
    logger = logging.getLogger(service_name)
    logger.setLevel(getattr(logging, log_level.upper()))
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File handler
    file_handler = logging.FileHandler(f'{service_name}.log')
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    return logger
