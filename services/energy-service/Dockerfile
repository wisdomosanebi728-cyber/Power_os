FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir --upgrade pip setuptools wheel

COPY services/common /app/services/common
RUN pip install --no-cache-dir /app/services/common

COPY services/energy-service /app/services/energy-service
WORKDIR /app/services/energy-service
RUN pip install --no-cache-dir .

ENV PYTHONPATH=/app/services/common:/app/services/energy-service

EXPOSE 8002

CMD ["uvicorn", "poweros_energy.main:app", "--host", "0.0.0.0", "--port", "8002"]
