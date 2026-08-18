import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from poweros_common.database import get_engine, get_session_factory, Base
from poweros_auth_device.routes.auth_routes import router as auth_router
from poweros_auth_device.routes.device_routes import router as device_router
from poweros_energy.routes.energy_routes import router as energy_router
from poweros_forecasting.routes.forecast_routes import router as forecast_router
from poweros_optimization.routes.optimization_routes import router as optimization_router
from poweros_ingestion.adapters.simulator_adapter import SimulatorJsonAdapter

from .config import GatewayConfig
from .routes.ws_routes import router as ws_router
from .routes.simulator_routes import router as simulator_router

logger = logging.getLogger("poweros-gateway")
config = GatewayConfig()
simulator_adapter = SimulatorJsonAdapter()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize Database connection pool if available
    try:
        engine = get_engine(config.AUTH_SERVICE_URL.replace("http://auth-device-service:8000", "postgresql://postgres:postgrespassword@localhost:5432/power_os"))
        Base.metadata.create_all(bind=engine)
        app.state.engine = engine
        app.state.session_factory = get_session_factory(engine)
        logger.info("Connected to database and verified table schemas.")
    except Exception as e:
        logger.warning(f"Database not immediately reachable on gateway startup ({e}). Gateway will run with in-memory state.")
        app.state.engine = None
        app.state.session_factory = None

    yield

    if getattr(app.state, "engine", None):
        app.state.engine.dispose()


app = FastAPI(
    title="POWER OS - Unified Microgrid Management Platform",
    version="1.0.0",
    description="Distributed Energy Operating System for Mini-Grids & Commercial/Industrial DERs",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount all domain microservice routers
app.include_router(auth_router)
app.include_router(device_router)
app.include_router(energy_router)
app.include_router(forecast_router)
app.include_router(optimization_router)
app.include_router(simulator_router)
app.include_router(ws_router)


@app.post("/api/v1/telemetry/ingest", status_code=status.HTTP_202_ACCEPTED, tags=["Telemetry Ingestion"])
def ingest_telemetry_http(payload: dict):
    """Direct HTTP fallback endpoint for IoT gateways to submit telemetry."""
    try:
        normalized = simulator_adapter.parse_payload(payload)
        return {
            "status": "accepted",
            "device_id": normalized.device_id,
            "timestamp": normalized.time.isoformat(),
            "power_kw": normalized.power_kw,
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Malformed telemetry payload: {str(e)}",
        )


# Static Dashboard UI Directory
current_dir = os.path.dirname(os.path.abspath(__file__))
static_dir = os.path.join(current_dir, "static")

if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

    @app.get("/", include_in_schema=False)
    async def serve_dashboard():
        return FileResponse(os.path.join(static_dir, "index.html"))


@app.get("/health")
def health():
    return {
        "service": "poweros-gateway",
        "status": "healthy",
        "version": "1.0.0",
    }
