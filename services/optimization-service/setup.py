from setuptools import setup, find_packages

setup(
    name="poweros-optimization",
    version="0.1.0",
    description="Economic Dispatch & Constraint Optimization Engine for POWER OS",
    packages=find_packages(),
    install_requires=[
        "fastapi>=0.111.0",
        "uvicorn>=0.30.0",
        "numpy>=1.26.0",
        "scipy>=1.12.0",
        "httpx>=0.27.0",
    ],
    python_requires=">=3.10",
)
