FROM python:3.11-slim
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    tesseract-ocr \
    tesseract-ocr-eng \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir -r /app/backend/requirements.txt

# Install additional dependencies for enhanced image service
RUN pip install --no-cache-dir \
    ultralytics \
    easyocr \
    paddlepaddle \
    paddleocr \
    tldextract

# Create models directory
RUN mkdir -p /app/models/image

# Copy service code
COPY backend/services/image_service /app/backend/services/image_service
COPY backend/common /app/backend/common

# Set environment variables
ENV PYTHONPATH=/app
ENV FEATURE_BRAND_DETECTION=true
ENV FEATURE_VISUAL_CHECKS=true
ENV FEATURE_URL_EXTRACTION=true
ENV FEATURE_URL_FUSION_INTEGRATION=true
ENV BRAND_MODEL_VARIANT=yolov5s
ENV OCR_ENGINE=tesseract
ENV TIMEOUT_MS=1200

# Expose port
EXPOSE 8003

CMD ["uvicorn", "backend.services.image_service.main:app", "--host", "0.0.0.0", "--port", "8003"]
