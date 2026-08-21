FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir --upgrade pip setuptools wheel

# Install common package
COPY services/common /app/services/common
RUN pip install --no-cache-dir /app/services/common

# Copy domain services
COPY services/auth-device-service /app/services/auth-device-service
RUN pip install --no-cache-dir /app/services/auth-device-service

COPY services/energy-service /app/services/energy-service
RUN pip install --no-cache-dir /app/services/energy-service

COPY services/forecasting-service /app/services/forecasting-service
RUN pip install --no-cache-dir /app/services/forecasting-service

COPY services/optimization-service /app/services/optimization-service
RUN pip install --no-cache-dir /app/services/optimization-service

COPY services/ingestion-service /app/services/ingestion-service
RUN pip install --no-cache-dir /app/services/ingestion-service

# Install Gateway Service
COPY services/gateway-service /app/services/gateway-service
WORKDIR /app/services/gateway-service
RUN pip install --no-cache-dir .

ENV PYTHONPATH=/app/services/common:/app/services/auth-device-service:/app/services/energy-service:/app/services/forecasting-service:/app/services/optimization-service:/app/services/ingestion-service:/app/services/gateway-service

EXPOSE 10000

CMD ["uvicorn", "poweros_gateway.main:app", "--host", "0.0.0.0", "--port", "10000"]