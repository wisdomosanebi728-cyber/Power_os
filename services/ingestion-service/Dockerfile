FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir --upgrade pip setuptools wheel

COPY services/common /app/services/common
RUN pip install --no-cache-dir /app/services/common

COPY services/ingestion-service /app/services/ingestion-service
WORKDIR /app/services/ingestion-service
RUN pip install --no-cache-dir .

ENV PYTHONPATH=/app/services/common:/app/services/ingestion-service

EXPOSE 8001

CMD ["uvicorn", "poweros_ingestion.main:app", "--host", "0.0.0.0", "--port", "8001"]
