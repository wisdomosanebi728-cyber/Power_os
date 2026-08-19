FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir --upgrade pip setuptools wheel

COPY services/common /app/services/common
RUN pip install --no-cache-dir /app/services/common

COPY simulator /app/simulator
WORKDIR /app/simulator
RUN pip install --no-cache-dir -r requirements.txt

ENV PYTHONPATH=/app/services/common:/app/simulator

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "10000"]
