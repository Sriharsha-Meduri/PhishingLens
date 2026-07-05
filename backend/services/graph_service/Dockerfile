FROM python:3.11-slim
WORKDIR /app
COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir -r /app/backend/requirements.txt
COPY backend/services/graph_service /app/backend/services/graph_service
COPY backend/common /app/backend/common
ENV PYTHONPATH=/app
CMD ["uvicorn", "backend.services.graph_service.main:app", "--host", "0.0.0.0", "--port", "8004"]
