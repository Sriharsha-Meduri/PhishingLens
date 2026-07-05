#!/bin/bash

# PhishingLens Publishing Script
# This script helps you publish your project to various registries

set -e

# Configuration
REGISTRY="docker.io"  # Change to ghcr.io for GitHub Container Registry
USERNAME="yourusername"  # Change to your username
PROJECT_NAME="phishinglens"
VERSION="latest"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if Docker is running
check_docker() {
    if ! docker info > /dev/null 2>&1; then
        log_error "Docker is not running. Please start Docker and try again."
        exit 1
    fi
    log_success "Docker is running"
}

# Build optimized images
build_images() {
    log_info "Building optimized Docker images..."
    
    # Build all services
    docker-compose -f deployment/optimized-docker-compose.yml build
    
    log_success "All images built successfully"
}

# Tag images for registry
tag_images() {
    log_info "Tagging images for registry..."
    
    # Tag all services
    docker tag ${PROJECT_NAME}-gateway:latest ${REGISTRY}/${USERNAME}/${PROJECT_NAME}-gateway:${VERSION}
    docker tag ${PROJECT_NAME}-text:latest ${REGISTRY}/${USERNAME}/${PROJECT_NAME}-text:${VERSION}
    docker tag ${PROJECT_NAME}-url:latest ${REGISTRY}/${USERNAME}/${PROJECT_NAME}-url:${VERSION}
    docker tag ${PROJECT_NAME}-image:latest ${REGISTRY}/${USERNAME}/${PROJECT_NAME}-image:${VERSION}
    docker tag ${PROJECT_NAME}-graph:latest ${REGISTRY}/${USERNAME}/${PROJECT_NAME}-graph:${VERSION}
    docker tag ${PROJECT_NAME}-frontend:latest ${REGISTRY}/${USERNAME}/${PROJECT_NAME}-frontend:${VERSION}
    
    log_success "All images tagged successfully"
}

# Push images to registry
push_images() {
    log_info "Pushing images to registry..."
    
    # Login to registry
    if [ "$REGISTRY" = "docker.io" ]; then
        log_info "Please login to Docker Hub:"
        docker login
    elif [ "$REGISTRY" = "ghcr.io" ]; then
        log_info "Please login to GitHub Container Registry:"
        echo $GITHUB_TOKEN | docker login ghcr.io -u $USERNAME --password-stdin
    fi
    
    # Push all services
    docker push ${REGISTRY}/${USERNAME}/${PROJECT_NAME}-gateway:${VERSION}
    docker push ${REGISTRY}/${USERNAME}/${PROJECT_NAME}-text:${VERSION}
    docker push ${REGISTRY}/${USERNAME}/${PROJECT_NAME}-url:${VERSION}
    docker push ${REGISTRY}/${USERNAME}/${PROJECT_NAME}-image:${VERSION}
    docker push ${REGISTRY}/${USERNAME}/${PROJECT_NAME}-graph:${VERSION}
    docker push ${REGISTRY}/${USERNAME}/${PROJECT_NAME}-frontend:${VERSION}
    
    log_success "All images pushed successfully"
}

# Create deployment manifests
create_manifests() {
    log_info "Creating deployment manifests..."
    
    # Create production docker-compose with registry images
    cat > deployment/docker-compose.production.yml << EOF
version: "3.9"

services:
  gateway:
    image: ${REGISTRY}/${USERNAME}/${PROJECT_NAME}-gateway:${VERSION}
    environment:
      TEXT_SERVICE_URL: http://text:8001
      URL_SERVICE_URL: http://url:8002
      IMAGE_SERVICE_URL: http://image:8003
      GRAPH_SERVICE_URL: http://graph:8004
    ports:
      - "8000:8000"
    depends_on:
      - text
      - url
      - image
      - graph
    restart: unless-stopped
    networks:
      - phishing-net

  text:
    image: ${REGISTRY}/${USERNAME}/${PROJECT_NAME}-text:${VERSION}
    environment:
      SERVICE_MODEL_ID: cybersectony/phishing-email-detection-distilbert_v2.4.1
      SERVICE_FALLBACK_MODEL_ID: /models/text/model
      SERVICE_USE_EXTERNAL_THRESHOLD: "true"
      EXTERNAL_TEXT_PROFILE: demo
      EXTERNAL_TEXT_THRESHOLD: "0.995"
      SHORT_TEXT_MIN_TOKENS: "3"
      SHORT_TEXT_HIGH_THRESHOLD: "0.999"
      EXTERNAL_CALIB_T: "1.90"
      ORT_PROVIDERS: CPUExecutionProvider
      URL_SERVICE_URL: http://url:8002
    ports:
      - "8001:8001"
    volumes:
      - ./models:/models:ro
    restart: unless-stopped
    networks:
      - phishing-net

  url:
    image: ${REGISTRY}/${USERNAME}/${PROJECT_NAME}-url:${VERSION}
    environment:
      EXTERNAL_URL_T_HF: "0.6"
      FUSION_K: "2"
      FUSION_WEIGHTS: "graph:1.0,scanner:1.0,hf:0.8,otx:1.0"
      T_SCAN: "0.29"
      T_HF: "0.74"
      T_GRAPH: "0.80"
      OTX_BASEURL: "https://otx.alienvault.com/api/v1"
      OTX_KEY: "89daa160ca2732951fcda18435dc939685a8ebd8aafda24951251abe88b6f7b7"
      OTX_TIMEOUT_MS: "5000"
      OTX_CACHE_TTL_H: "48"
      ALLOWLIST_DOMAINS: "youtube.com,*.gov.in"
      VERSION_TAG: "fusion-4src-k2-v1"
      FEATURE_GRAPH_ENABLED: "true"
      FEATURE_GRAPH_SYNTH_POSITIVE: "false"
    ports:
      - "8002:8002"
    volumes:
      - ./data:/app/data:ro
    restart: unless-stopped
    networks:
      - phishing-net

  image:
    image: ${REGISTRY}/${USERNAME}/${PROJECT_NAME}-image:${VERSION}
    ports:
      - "8003:8003"
    volumes:
      - ./models:/models:ro
    restart: unless-stopped
    networks:
      - phishing-net

  graph:
    image: ${REGISTRY}/${USERNAME}/${PROJECT_NAME}-graph:${VERSION}
    ports:
      - "8004:8004"
    volumes:
      - ./models:/models:ro
    restart: unless-stopped
    networks:
      - phishing-net

  frontend:
    image: ${REGISTRY}/${USERNAME}/${PROJECT_NAME}-frontend:${VERSION}
    environment:
      VITE_GATEWAY_URL: http://localhost:8000
    ports:
      - "5173:5173"
    depends_on:
      - gateway
    restart: unless-stopped
    networks:
      - phishing-net

networks:
  phishing-net:
    driver: bridge
EOF
    
    log_success "Deployment manifests created"
}

# Show image sizes
show_sizes() {
    log_info "Current image sizes:"
    docker images --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}" | grep ${PROJECT_NAME}
}

# Main execution
main() {
    log_info "Starting PhishingLens publishing process..."
    
    # Check prerequisites
    check_docker
    
    # Build optimized images
    build_images
    
    # Show sizes
    show_sizes
    
    # Tag images
    tag_images
    
    # Push images
    push_images
    
    # Create deployment manifests
    create_manifests
    
    log_success "Publishing completed successfully!"
    log_info "Your images are now available at:"
    echo "  - ${REGISTRY}/${USERNAME}/${PROJECT_NAME}-gateway:${VERSION}"
    echo "  - ${REGISTRY}/${USERNAME}/${PROJECT_NAME}-text:${VERSION}"
    echo "  - ${REGISTRY}/${USERNAME}/${PROJECT_NAME}-url:${VERSION}"
    echo "  - ${REGISTRY}/${USERNAME}/${PROJECT_NAME}-image:${VERSION}"
    echo "  - ${REGISTRY}/${USERNAME}/${PROJECT_NAME}-graph:${VERSION}"
    echo "  - ${REGISTRY}/${USERNAME}/${PROJECT_NAME}-frontend:${VERSION}"
    
    log_info "To deploy, run:"
    echo "  docker-compose -f deployment/docker-compose.production.yml up -d"
}

# Run main function
main "$@"
