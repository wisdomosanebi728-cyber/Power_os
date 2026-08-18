from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .config import EnergyConfig
from .routes.energy_routes import router as energy_router

config = EnergyConfig()


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(
    title="POWER OS - Energy Service",
    version="0.1.0",
    description="Real-Time Energy State Aggregator and Anomaly Detector for POWER OS",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(energy_router)


@app.get("/health")
def health_check():
    return {
        "service": config.SERVICE_NAME,
        "status": "healthy",
    }
