# Phishing Detection System - Deployment Guide

## Overview

This guide provides comprehensive instructions for deploying the Phishing Detection System in production environments. The system supports both Docker Compose and Kubernetes deployments with full monitoring and logging capabilities.

## Prerequisites

### System Requirements

- **Operating System**: Linux (Ubuntu 20.04+), macOS, or Windows 10+
- **Docker**: Version 20.10+
- **Docker Compose**: Version 2.0+
- **Memory**: Minimum 8GB RAM (16GB recommended)
- **CPU**: Minimum 4 cores (8 cores recommended)
- **Storage**: Minimum 50GB free space
- **Network**: Internet access for model downloads and API calls

### Optional Requirements

- **Kubernetes**: Version 1.20+ (for K8s deployment)
- **Helm**: Version 3.0+ (for K8s deployment)
- **GPU**: NVIDIA GPU with CUDA support (for faster inference)

## Quick Start

### 1. Clone Repository

```bash
git clone <repository-url>
cd SIHPhishing
```

### 2. Set Environment Variables

Create a `.env` file in the project root:

```bash
# API Keys (replace with your actual keys)
PHISHTANK_API_KEY=your_phishtank_api_key_here
OTX_API_KEY=your_otx_api_key_here
MISP_URL=your_misp_url_here
MISP_API_KEY=your_misp_api_key_here

# Monitoring
GRAFANA_ADMIN_PASSWORD=admin123
PROMETHEUS_RETENTION=200h

# Performance
TEXT_SERVICE_TIMEOUT=30
URL_SERVICE_TIMEOUT=20
IMAGE_SERVICE_TIMEOUT=60
GRAPH_SERVICE_TIMEOUT=10
```

### 3. Deploy with Docker Compose

```bash
# Make deployment script executable
chmod +x scripts/deploy_production.sh

# Run deployment
./scripts/deploy_production.sh
```

### 4. Verify Deployment

```bash
# Check service health
curl http://localhost:8000/health

# Check monitoring
curl http://localhost:9090/-/healthy  # Prometheus
curl http://localhost:3000/api/health  # Grafana
```

## Detailed Deployment Options

### Option 1: Docker Compose (Recommended for Development)

#### Basic Deployment

```bash
# Start all services
docker-compose -f deployment/docker-compose.production.yml up -d

# View logs
docker-compose -f deployment/docker-compose.production.yml logs -f

# Stop services
docker-compose -f deployment/docker-compose.production.yml down
```

#### Services Included

- **Gateway**: API gateway and load balancer
- **Text Service**: NLP-based text analysis
- **URL Service**: URL analysis with fusion
- **Image Service**: Computer vision analysis
- **Graph Service**: Graph neural network analysis
- **Frontend**: Web interface
- **Prometheus**: Metrics collection
- **Grafana**: Monitoring dashboards
- **Loki**: Log aggregation
- **Continuous Learning**: Automated model retraining

#### Configuration

Edit `deployment/docker-compose.production.yml` to customize:

```yaml
services:
  gateway:
    environment:
      TEXT_SERVICE_URL: http://text:8001
      URL_SERVICE_URL: http://url:8002
      IMAGE_SERVICE_URL: http://image:8003
      GRAPH_SERVICE_URL: http://graph:8004
    ports:
      - "8000:8000"
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
```

### Option 2: Kubernetes Deployment

#### Prerequisites

```bash
# Install kubectl
curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
sudo install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl

# Install Helm
curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash
```

#### Deploy to Kubernetes

```bash
# Create namespace
kubectl create namespace phishing-detection

# Apply configurations
kubectl apply -f deployment/k8s/namespace.yaml
kubectl apply -f deployment/k8s/configmap.yaml
kubectl apply -f deployment/k8s/secrets.yaml
kubectl apply -f deployment/k8s/persistent-volumes.yaml

# Deploy services
kubectl apply -f deployment/k8s/gateway-deployment.yaml
kubectl apply -f deployment/k8s/text-service-deployment.yaml
kubectl apply -f deployment/k8s/url-service-deployment.yaml
kubectl apply -f deployment/k8s/image-service-deployment.yaml
kubectl apply -f deployment/k8s/graph-service-deployment.yaml
kubectl apply -f deployment/k8s/continuous-learning-deployment.yaml

# Deploy ingress
kubectl apply -f deployment/k8s/ingress.yaml

# Check deployment status
kubectl get pods -n phishing-detection
kubectl get services -n phishing-detection
```

#### Access Services

```bash
# Get service URLs
kubectl get ingress -n phishing-detection

# Port forward for local access
kubectl port-forward -n phishing-detection service/gateway-service 8000:8000
kubectl port-forward -n phishing-detection service/grafana-service 3000:3000
```

### Option 3: Manual Deployment

#### 1. Install Dependencies

```bash
# Python dependencies
pip install -r backend/requirements.txt

# Node.js dependencies (for frontend)
cd frontend && npm install
```

#### 2. Start Services Individually

```bash
# Start gateway
cd backend/services/gateway
python main.py

# Start text service
cd backend/services/text_service
python main.py

# Start URL service
cd backend/services/url_service
python main.py

# Start image service
cd backend/services/image_service
python main.py

# Start graph service
cd backend/services/graph_service
python main.py

# Start frontend
cd frontend
npm run dev
```

## Configuration

### Environment Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `TEXT_SERVICE_URL` | Text service URL | `http://text:8001` | Yes |
| `URL_SERVICE_URL` | URL service URL | `http://url:8002` | Yes |
| `IMAGE_SERVICE_URL` | Image service URL | `http://image:8003` | Yes |
| `GRAPH_SERVICE_URL` | Graph service URL | `http://graph:8004` | Yes |
| `PHISHTANK_API_KEY` | PhishTank API key | - | No |
| `OTX_API_KEY` | OTX API key | - | No |
| `MISP_URL` | MISP server URL | - | No |
| `MISP_API_KEY` | MISP API key | - | No |

### Service Configuration

#### Text Service
```yaml
environment:
  SERVICE_MODEL_ID: cybersectony/phishing-email-detection-distilbert_v2.4.1
  EXTERNAL_TEXT_THRESHOLD: "0.995"
  SHORT_TEXT_MIN_TOKENS: "3"
  SHORT_TEXT_HIGH_THRESHOLD: "0.999"
```

#### URL Service
```yaml
environment:
  FUSION_K: "2"
  FUSION_WEIGHTS: "graph:1.0,scanner:1.0,hf:0.8,otx:1.0"
  T_SCAN: "0.29"
  T_HF: "0.74"
  T_GRAPH: "0.80"
```

#### Image Service
```yaml
environment:
  FEATURE_BRAND_DETECTION: "true"
  FEATURE_VISUAL_CHECKS: "true"
  FEATURE_URL_EXTRACTION: "true"
  FEATURE_URL_FUSION_INTEGRATION: "true"
```

## Monitoring and Observability

### Prometheus Metrics

Access Prometheus at `http://localhost:9090` to view:

- **Request Metrics**: Request count, duration, error rate
- **Performance Metrics**: Response time percentiles
- **Business Metrics**: Phishing detection rate, model accuracy
- **System Metrics**: CPU, memory, disk usage

### Grafana Dashboards

Access Grafana at `http://localhost:3000` (admin/admin123) to view:

- **System Overview**: Service health and status
- **Performance Dashboard**: Response times and throughput
- **Threat Detection Dashboard**: Phishing detection metrics
- **Continuous Learning Dashboard**: Model training and performance

### Logging

Logs are collected and aggregated using Loki:

- **Service Logs**: Application logs from all services
- **Access Logs**: HTTP request/response logs
- **Error Logs**: Error tracking and debugging
- **Audit Logs**: Security and compliance logging

## Performance Optimization

### Resource Limits

```yaml
services:
  gateway:
    deploy:
      resources:
        limits:
          memory: 512Mi
          cpus: '0.5'
        reservations:
          memory: 256Mi
          cpus: '0.25'
```

### Scaling

#### Horizontal Scaling

```bash
# Scale services
docker-compose -f deployment/docker-compose.production.yml up -d --scale gateway=3
docker-compose -f deployment/docker-compose.production.yml up -d --scale text=2
```

#### Kubernetes Scaling

```bash
# Scale deployments
kubectl scale deployment gateway -n phishing-detection --replicas=3
kubectl scale deployment text-service -n phishing-detection --replicas=2
```

### Performance Targets

- **Text Analysis**: <50ms (95th percentile)
- **URL Analysis**: <100ms (95th percentile)
- **Image Analysis**: <200ms (95th percentile)
- **Graph Analysis**: <100ms (95th percentile)

### Benchmarking

```bash
# Run performance benchmark
python scripts/performance_benchmark.py \
  --text-requests 100 \
  --url-requests 100 \
  --image-requests 50 \
  --output benchmark_results.json
```

## Security Considerations

### Network Security

- Use HTTPS in production
- Implement API authentication
- Configure firewall rules
- Use network segmentation

### Data Security

- Encrypt data at rest
- Use secure communication (TLS)
- Implement input validation
- Regular security updates

### Access Control

```yaml
# Example: API key authentication
environment:
  API_KEY_REQUIRED: "true"
  API_KEYS: "key1,key2,key3"
```

## Troubleshooting

### Common Issues

#### Service Not Starting

```bash
# Check logs
docker-compose logs <service-name>

# Check health
curl http://localhost:8000/health
```

#### Performance Issues

```bash
# Check resource usage
docker stats

# Run benchmark
python scripts/performance_benchmark.py
```

#### Monitoring Issues

```bash
# Check Prometheus
curl http://localhost:9090/-/healthy

# Check Grafana
curl http://localhost:3000/api/health
```

### Debug Mode

```bash
# Enable debug logging
export LOG_LEVEL=DEBUG
docker-compose -f deployment/docker-compose.production.yml up -d
```

### Health Checks

```bash
# Check all services
curl http://localhost:8000/health
curl http://localhost:8001/health
curl http://localhost:8002/health
curl http://localhost:8003/health
curl http://localhost:8004/health
```

## Maintenance

### Updates

```bash
# Update services
docker-compose -f deployment/docker-compose.production.yml pull
docker-compose -f deployment/docker-compose.production.yml up -d
```

### Backups

```bash
# Backup models
tar -czf models_backup.tar.gz models/

# Backup data
tar -czf data_backup.tar.gz data/
```

### Cleanup

```bash
# Remove old containers
docker system prune -a

# Remove old images
docker image prune -a
```

## Support

### Getting Help

1. **Documentation**: Check this guide and API documentation
2. **Logs**: Review service logs for errors
3. **Monitoring**: Check Grafana dashboards for issues
4. **Health Checks**: Verify service health endpoints

### Contact

- **Issues**: Report issues in the project repository
- **Documentation**: See `/docs` directory
- **Monitoring**: Check service health at `/health` endpoint

## Next Steps

After successful deployment:

1. **Configure Monitoring**: Set up alerts and dashboards
2. **Performance Tuning**: Optimize based on your workload
3. **Security Hardening**: Implement authentication and encryption
4. **Backup Strategy**: Set up regular backups
5. **Scaling**: Plan for horizontal scaling as needed
