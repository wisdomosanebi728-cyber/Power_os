from setuptools import setup, find_packages

setup(
    name="poweros-gateway",
    version="0.1.0",
    description="Unified API Gateway and Real-Time WebSocket Streaming Service for POWER OS",
    packages=find_packages(),
    install_requires=[
        "fastapi>=0.111.0",
        "uvicorn>=0.30.0",
        "websockets>=12.0",
        "redis>=5.0.0",
        "httpx>=0.27.0",
        "pydantic-settings>=2.2.0",
    ],
    python_requires=">=3.10",
)
