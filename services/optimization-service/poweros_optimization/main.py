from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .config import OptimizationConfig
from .routes.optimization_routes import router as optimization_router

config = OptimizationConfig()


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(
    title="POWER OS - Optimization Service",
    version="0.1.0",
    description="Economic Dispatch & Invariant Optimizer Engine for POWER OS",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(optimization_router)


@app.get("/health")
def health_check():
    return {
        "service": config.SERVICE_NAME,
        "status": "healthy",
    }
