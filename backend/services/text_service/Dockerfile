FROM python:3.11-slim
WORKDIR /app
COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir -r /app/backend/requirements.txt
COPY backend/services/text_service /app/backend/services/text_service
COPY backend/common /app/backend/common
COPY data/benign_urls.txt /app/data/benign_urls.txt
ENV PYTHONPATH=/app
CMD ["uvicorn", "backend.services.text_service.main:app", "--host", "0.0.0.0", "--port", "8001"]
