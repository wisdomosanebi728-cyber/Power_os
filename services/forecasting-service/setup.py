from setuptools import setup, find_packages

setup(
    name="poweros-forecasting",
    version="0.1.0",
    description="AI Demand and Solar Forecasting Service for POWER OS",
    packages=find_packages(),
    install_requires=[
        "fastapi>=0.111.0",
        "uvicorn>=0.30.0",
        "numpy>=1.26.0",
        "scikit-learn>=1.4.0",
        "httpx>=0.27.0",
    ],
    python_requires=">=3.10",
)
