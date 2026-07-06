# PhishingLens consolidated API - deployable on Hugging Face Spaces (Docker SDK)
# or any Docker host. CPU-only; the DistilBERT model is baked in for fast cold starts.
FROM python:3.11-slim

WORKDIR /app

# System deps: Tesseract OCR for the image (visual) lens.
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr && rm -rf /var/lib/apt/lists/*

# Newer pip handles the PyTorch index wheels correctly.
RUN pip install --no-cache-dir --upgrade pip

# CPU-only PyTorch (>=2.6 so transformers will load .safetensors weights).
RUN pip install --no-cache-dir "torch>=2.6" --index-url https://download.pytorch.org/whl/cpu

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Cache the model inside the image so the Space boots ready (no ~270MB runtime download).
ENV HF_HOME=/app/hf_cache
RUN mkdir -p /app/hf_cache && \
    python -c "from transformers import AutoModelForSequenceClassification, AutoTokenizer; \
m='cybersectony/phishing-email-detection-distilbert_v2.4.1'; \
AutoTokenizer.from_pretrained(m); AutoModelForSequenceClassification.from_pretrained(m)" && \
    chmod -R 777 /app/hf_cache

COPY app.py .

ENV PORT=7860
EXPOSE 7860

CMD ["sh", "-c", "uvicorn app:app --host 0.0.0.0 --port ${PORT}"]
