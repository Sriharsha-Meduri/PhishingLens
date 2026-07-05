#!/bin/bash

# Production deployment script for phishing detection system
# This script sets up the complete production environment with monitoring

set -e

echo "🚀 Deploying Phishing Detection System to Production"
echo "=================================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    print_error "Docker is not running. Please start Docker and try again."
    exit 1
fi

# Check if Docker Compose is available
if ! command -v docker-compose &> /dev/null; then
    print_error "Docker Compose is not installed. Please install Docker Compose and try again."
    exit 1
fi

print_status "Setting up production environment..."

# Create necessary directories
mkdir -p deployment/monitoring/grafana/dashboards
mkdir -p deployment/monitoring/grafana/provisioning/dashboards
mkdir -p deployment/monitoring/grafana/provisioning/datasources
mkdir -p logs

# Set up environment variables
if [ ! -f .env ]; then
    print_status "Creating environment file..."
    cat > .env << EOF
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
EOF
    print_warning "Please update .env file with your actual API keys"
fi

# Build all services
print_status "Building Docker images..."
docker-compose -f deployment/docker-compose.production.yml build

# Start the services
print_status "Starting production services..."
docker-compose -f deployment/docker-compose.production.yml up -d

# Wait for services to be ready
print_status "Waiting for services to be ready..."
sleep 30

# Check service health
print_status "Checking service health..."

services=("gateway:8000" "text:8001" "url:8002" "image:8003" "graph:8004")
for service in "${services[@]}"; do
    name=$(echo $service | cut -d: -f1)
    port=$(echo $service | cut -d: -f2)
    
    if curl -f http://localhost:$port/health > /dev/null 2>&1; then
        print_status "✅ $name service is healthy"
    else
        print_warning "⚠️  $name service health check failed"
    fi
done

# Check monitoring services
print_status "Checking monitoring services..."

if curl -f http://localhost:9090/-/healthy > /dev/null 2>&1; then
    print_status "✅ Prometheus is running"
else
    print_warning "⚠️  Prometheus health check failed"
fi

if curl -f http://localhost:3000/api/health > /dev/null 2>&1; then
    print_status "✅ Grafana is running"
else
    print_warning "⚠️  Grafana health check failed"
fi

# Run performance benchmark
print_status "Running performance benchmark..."
if [ -f scripts/performance_benchmark.py ]; then
    python scripts/performance_benchmark.py --text-requests 50 --url-requests 50 --image-requests 25
else
    print_warning "Performance benchmark script not found"
fi

# Display access information
echo ""
echo "🎉 Production Deployment Complete!"
echo "================================"
echo ""
echo "📊 Service URLs:"
echo "  Gateway:      http://localhost:8000"
echo "  Frontend:     http://localhost:5173"
echo "  Prometheus:   http://localhost:9090"
echo "  Grafana:      http://localhost:3000 (admin/admin123)"
echo ""
echo "🔍 Health Checks:"
echo "  Gateway:      http://localhost:8000/health"
echo "  Text:         http://localhost:8001/health"
echo "  URL:          http://localhost:8002/health"
echo "  Image:        http://localhost:8003/health"
echo "  Graph:        http://localhost:8004/health"
echo ""
echo "📈 Metrics:"
echo "  Prometheus:   http://localhost:9090/metrics"
echo "  Gateway:      http://localhost:8000/metrics"
echo ""
echo "🛠️  Management Commands:"
echo "  View logs:    docker-compose -f deployment/docker-compose.production.yml logs -f"
echo "  Stop all:     docker-compose -f deployment/docker-compose.production.yml down"
echo "  Restart:      docker-compose -f deployment/docker-compose.production.yml restart"
echo ""

# Check if all services are running
running_containers=$(docker-compose -f deployment/docker-compose.production.yml ps -q | wc -l)
expected_containers=8  # gateway, text, url, image, graph, frontend, prometheus, grafana

if [ "$running_containers" -eq "$expected_containers" ]; then
    print_status "✅ All services are running successfully!"
else
    print_warning "⚠️  Some services may not be running. Check with: docker-compose ps"
fi

echo ""
print_status "Deployment completed! Check the URLs above to access your services."
