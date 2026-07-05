# Phishing Detection System - Architecture Overview

## System Architecture

The Phishing Detection System is built using a microservices architecture that provides comprehensive phishing detection across multiple modalities: text, URLs, images, and graph analysis. The system is designed for high performance, scalability, and reliability.

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Frontend Layer                           │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │   Web UI    │  │ Browser Ext │  │   Mobile    │             │
│  │             │  │             │  │     App     │             │
│  └─────────────┘  └─────────────┘  └─────────────┘             │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                      API Gateway Layer                         │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │                    Gateway Service                          │ │
│  │  • Load Balancing  • Rate Limiting  • Authentication      │ │
│  │  • Request Routing • CORS Handling  • Health Checks       │ │
│  └─────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Microservices Layer                         │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────┐ │
│  │    Text     │  │     URL     │  │   Image     │  │  Graph  │ │
│  │  Service    │  │  Service    │  │  Service    │  │ Service │ │
│  │             │  │             │  │             │  │         │ │
│  │ • DistilBERT│  │ • Fusion    │  │ • YOLOv5    │  │ • GNN   │ │
│  │ • NLP       │  │ • Scanner   │  │ • OCR       │  │ • Graph │ │
│  │ • Analysis  │  │ • OTX       │  │ • Brand     │  │ • ML    │ │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────┘ │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Data & Model Layer                          │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │   Models     │  │    Data     │  │  External   │             │
│  │             │  │             │  │   APIs      │             │
│  │ • ONNX      │  │ • Training  │  │ • PhishTank │             │
│  │ • PyTorch   │  │ • Testing   │  │ • OTX       │             │
│  │ • HuggingFace│  │ • Validation│  │ • MISP      │             │
│  └─────────────┘  └─────────────┘  └─────────────┘             │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                   Monitoring & Observability                   │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │ Prometheus  │  │   Grafana   │  │    Loki     │             │
│  │             │  │             │  │             │             │
│  │ • Metrics   │  │ • Dashboards│  │ • Logs      │             │
│  │ • Alerts    │  │ • Visualize │  │ • Aggregation│             │
│  │ • Storage   │  │ • Analysis  │  │ • Search    │             │
│  └─────────────┘  └─────────────┘  └─────────────┘             │
└─────────────────────────────────────────────────────────────────┘
```

## Service Architecture

### 1. Gateway Service

**Purpose**: Central API gateway that routes requests to appropriate microservices.

**Responsibilities**:
- Request routing and load balancing
- Rate limiting and throttling
- CORS handling
- Health check aggregation
- Metrics collection
- Authentication (future)

**Technology Stack**:
- FastAPI (Python)
- HTTP client (httpx)
- Prometheus metrics
- Structured logging

**Performance Targets**:
- Response time: <10ms overhead
- Throughput: 1000+ requests/second
- Availability: 99.9%

### 2. Text Service

**Purpose**: Analyzes text content for phishing indicators using NLP models.

**Responsibilities**:
- Text preprocessing and tokenization
- Model inference using DistilBERT
- Confidence scoring
- Result interpretation
- Model management

**Technology Stack**:
- FastAPI (Python)
- Transformers (HuggingFace)
- ONNX Runtime
- PyTorch
- DistilBERT model

**Performance Targets**:
- Response time: <50ms
- Accuracy: >95%
- Throughput: 500+ requests/second

### 3. URL Service

**Purpose**: Analyzes URLs for phishing indicators using multiple detection methods.

**Responsibilities**:
- URL feature extraction
- Multiple source fusion (Scanner, HF, OTX, Graph)
- Threat intelligence integration
- Result aggregation
- Caching

**Technology Stack**:
- FastAPI (Python)
- Requests (HTTP client)
- Feature extraction libraries
- External APIs (OTX, MISP)
- Redis (caching)

**Performance Targets**:
- Response time: <100ms
- Accuracy: >90%
- Throughput: 1000+ requests/second

### 4. Image Service

**Purpose**: Analyzes images and screenshots for phishing indicators using computer vision.

**Responsibilities**:
- Image preprocessing
- OCR text extraction
- Brand detection
- Visual indicator analysis
- URL extraction and analysis
- Model inference

**Technology Stack**:
- FastAPI (Python)
- OpenCV
- Tesseract OCR
- YOLOv5
- ONNX Runtime
- PIL/Pillow

**Performance Targets**:
- Response time: <200ms
- Accuracy: >85%
- Throughput: 100+ requests/second

### 5. Graph Service

**Purpose**: Analyzes relationships and patterns using graph neural networks.

**Responsibilities**:
- Graph construction
- Node and edge analysis
- Anomaly detection
- Pattern recognition
- GNN inference

**Technology Stack**:
- FastAPI (Python)
- PyTorch Geometric
- NetworkX
- GNN models
- ONNX Runtime

**Performance Targets**:
- Response time: <100ms
- Accuracy: >80%
- Throughput: 200+ requests/second

## Data Flow Architecture

### Request Flow

```
1. Client Request
   ↓
2. Gateway Service
   ├── Rate Limiting
   ├── Authentication
   ├── Request Routing
   └── Load Balancing
   ↓
3. Microservice Processing
   ├── Text Service (NLP Analysis)
   ├── URL Service (Fusion Analysis)
   ├── Image Service (CV Analysis)
   └── Graph Service (GNN Analysis)
   ↓
4. Response Aggregation
   ├── Result Fusion
   ├── Confidence Scoring
   └── Response Formatting
   ↓
5. Client Response
```

### Data Processing Pipeline

```
Input Data
    ↓
Preprocessing
    ├── Text: Tokenization, Cleaning
    ├── URL: Feature Extraction
    ├── Image: Resizing, OCR
    └── Graph: Node/Edge Construction
    ↓
Model Inference
    ├── Text: DistilBERT
    ├── URL: Fusion Models
    ├── Image: YOLOv5 + OCR
    └── Graph: GNN
    ↓
Post-processing
    ├── Confidence Scoring
    ├── Result Interpretation
    └── Response Formatting
    ↓
Output
```

## Technology Stack

### Backend Services
- **Language**: Python 3.9+
- **Framework**: FastAPI
- **ML Libraries**: PyTorch, Transformers, ONNX Runtime
- **HTTP Client**: httpx
- **Monitoring**: Prometheus, Grafana
- **Logging**: Structured logging with Loki

### Frontend
- **Framework**: React with Vite
- **Styling**: CSS3
- **HTTP Client**: Fetch API
- **Build Tool**: Vite

### Infrastructure
- **Containerization**: Docker
- **Orchestration**: Docker Compose / Kubernetes
- **Monitoring**: Prometheus + Grafana
- **Logging**: Loki + Promtail
- **Storage**: Local volumes / Persistent volumes

### ML Models
- **Text**: DistilBERT (HuggingFace)
- **Image**: YOLOv5 (ONNX)
- **Graph**: Custom GNN (PyTorch)
- **URL**: Ensemble of multiple models

## Deployment Architecture

### Development Environment

```
┌─────────────────────────────────────────────────────────────────┐
│                    Development Setup                            │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │   Local     │  │   Docker    │  │   Testing   │             │
│  │  Services   │  │  Compose    │  │  Framework  │             │
│  └─────────────┘  └─────────────┘  └─────────────┘             │
└─────────────────────────────────────────────────────────────────┘
```

### Production Environment

```
┌─────────────────────────────────────────────────────────────────┐
│                    Production Setup                            │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │   Load      │  │   Service    │  │  Monitoring │             │
│  │  Balancer   │  │   Cluster    │  │   Stack     │             │
│  └─────────────┘  └─────────────┘  └─────────────┘             │
└─────────────────────────────────────────────────────────────────┘
```

## Security Architecture

### Network Security
- **API Gateway**: Centralized security controls
- **Rate Limiting**: DDoS protection
- **CORS**: Cross-origin request handling
- **TLS**: Encrypted communication

### Data Security
- **Input Validation**: Sanitization and validation
- **Model Security**: Secure model storage
- **API Keys**: Secure credential management
- **Audit Logging**: Security event tracking

### Access Control
- **Authentication**: API key authentication (future)
- **Authorization**: Role-based access control (future)
- **Monitoring**: Security event monitoring
- **Alerting**: Automated security alerts

## Scalability Architecture

### Horizontal Scaling
- **Load Balancing**: Multiple service instances
- **Auto-scaling**: Dynamic resource allocation
- **Service Discovery**: Automatic service registration
- **Health Checks**: Automatic failover

### Vertical Scaling
- **Resource Optimization**: CPU and memory tuning
- **Model Optimization**: ONNX conversion for performance
- **Caching**: Redis for frequently accessed data
- **Connection Pooling**: Efficient resource utilization

## Monitoring Architecture

### Metrics Collection
- **Prometheus**: Metrics scraping and storage
- **Custom Metrics**: Business and technical metrics
- **Service Discovery**: Automatic target discovery
- **Alerting**: Automated alert generation

### Logging
- **Structured Logging**: JSON-formatted logs
- **Log Aggregation**: Centralized log collection
- **Log Analysis**: Search and analysis capabilities
- **Retention**: Configurable log retention

### Observability
- **Health Checks**: Service health monitoring
- **Dependency Tracking**: Service dependency monitoring
- **Performance Monitoring**: Response time tracking
- **Error Tracking**: Error rate and type monitoring

## Continuous Learning Architecture

### Data Pipeline
```
External Data Sources
    ├── PhishTank API
    ├── OTX API
    ├── MISP API
    └── User Feedback
    ↓
Data Collection
    ├── Automated Fetching
    ├── Data Validation
    └── Storage
    ↓
Model Training
    ├── Data Preprocessing
    ├── Model Training
    ├── Validation
    └── Model Evaluation
    ↓
Model Deployment
    ├── Model Versioning
    ├── A/B Testing
    ├── Gradual Rollout
    └── Performance Monitoring
```

### Model Management
- **Versioning**: Model version control
- **A/B Testing**: Model comparison
- **Rollback**: Automatic rollback on performance degradation
- **Monitoring**: Model performance tracking

## Performance Architecture

### Caching Strategy
- **Model Caching**: Pre-loaded models in memory
- **Result Caching**: Cached analysis results
- **Feature Caching**: Cached extracted features
- **API Response Caching**: HTTP response caching

### Optimization
- **Model Optimization**: ONNX conversion
- **Batch Processing**: Efficient batch inference
- **Async Processing**: Non-blocking operations
- **Resource Pooling**: Efficient resource utilization

## Future Enhancements

### Planned Features
- **Authentication**: OAuth2/JWT authentication
- **Multi-tenancy**: Tenant isolation
- **Advanced Analytics**: ML-based insights
- **Real-time Streaming**: Kafka integration
- **Edge Deployment**: Edge computing support

### Scalability Improvements
- **Microservice Mesh**: Service mesh integration
- **Event-driven Architecture**: Event streaming
- **Advanced Caching**: Distributed caching
- **Database Integration**: Persistent storage

## Conclusion

The Phishing Detection System architecture provides a robust, scalable, and maintainable solution for comprehensive phishing detection. The microservices architecture ensures high availability and performance, while the monitoring and observability stack provides comprehensive insights into system behavior and performance.

The system is designed to handle high-volume requests while maintaining low latency and high accuracy across all detection modalities. The continuous learning pipeline ensures the system stays up-to-date with evolving threats, while the comprehensive monitoring stack provides operational visibility and alerting capabilities.
