from setuptools import setup, find_packages

setup(
    name="poweros-ingestion",
    version="0.1.0",
    description="IoT Gateway and Telemetry Ingestion Service for POWER OS",
    packages=find_packages(),
    install_requires=[
        "fastapi>=0.111.0",
        "uvicorn>=0.30.0",
        "paho-mqtt>=2.0.0",
        "redis>=5.0.0",
        "httpx>=0.27.0",
        "psycopg2-binary>=2.9.9",
    ],
    python_requires=">=3.10",
)
