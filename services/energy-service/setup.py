from setuptools import setup, find_packages

setup(
    name="poweros-energy",
    version="0.1.0",
    description="Real-Time Energy State Aggregator & Anomaly Detection Service for POWER OS",
    packages=find_packages(),
    install_requires=[
        "fastapi>=0.111.0",
        "uvicorn>=0.30.0",
        "sqlalchemy>=2.0.29",
        "psycopg2-binary>=2.9.9",
        "httpx>=0.27.0",
    ],
    python_requires=">=3.10",
)
