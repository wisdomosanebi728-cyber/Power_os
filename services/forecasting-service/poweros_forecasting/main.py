from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .config import ForecastingConfig
from .routes.forecast_routes import router as forecast_router

config = ForecastingConfig()


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(
    title="POWER OS - Forecasting Service",
    version="0.1.0",
    description="AI Load Demand & Solar Yield Predictor for POWER OS",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(forecast_router)


@app.get("/health")
def health_check():
    return {
        "service": config.SERVICE_NAME,
        "status": "healthy",
    }
