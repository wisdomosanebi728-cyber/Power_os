FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir --upgrade pip setuptools wheel

COPY services/common /app/services/common
RUN pip install --no-cache-dir /app/services/common

COPY services/forecasting-service /app/services/forecasting-service
WORKDIR /app/services/forecasting-service
RUN pip install --no-cache-dir .

ENV PYTHONPATH=/app/services/common:/app/services/forecasting-service

EXPOSE 8003

CMD ["uvicorn", "poweros_forecasting.main:app", "--host", "0.0.0.0", "--port", "8003"]
