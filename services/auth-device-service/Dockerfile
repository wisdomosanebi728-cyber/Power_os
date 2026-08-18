FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir --upgrade pip setuptools wheel

COPY services/common /app/services/common
RUN pip install --no-cache-dir /app/services/common

COPY services/auth-device-service /app/services/auth-device-service
WORKDIR /app/services/auth-device-service
RUN pip install --no-cache-dir .

ENV PYTHONPATH=/app/services/common:/app/services/auth-device-service

EXPOSE 8000

CMD ["uvicorn", "poweros_auth_device.main:app", "--host", "0.0.0.0", "--port", "8000"]
