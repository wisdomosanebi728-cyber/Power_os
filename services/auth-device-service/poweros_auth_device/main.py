import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from poweros_common.database import get_engine, get_session_factory, Base
import poweros_common.models.entities  # Ensure models are registered in Base.metadata
from .config import AuthDeviceConfig
from .routes.auth_routes import router as auth_router
from .routes.device_routes import router as device_router

logger = logging.getLogger("poweros-auth-device")
config = AuthDeviceConfig()


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        engine = get_engine(config.DATABASE_URL)
        Base.metadata.create_all(bind=engine)
        app.state.engine = engine
        app.state.session_factory = get_session_factory(engine)
        logger.info("Connected to database and verified table schemas.")
    except Exception as e:
        logger.warning(f"Database not immediately reachable on auth-device-service startup ({e}). Sessions will be initialized lazily.")
        app.state.engine = None
        app.state.session_factory = None

    yield

    if getattr(app.state, "engine", None):
        try:
            app.state.engine.dispose()
        except Exception:
            pass


app = FastAPI(
    title="POWER OS - Auth & Device Service",
    version="0.1.0",
    description="Identity, RBAC, and Device Management Service for POWER OS",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(device_router)


@app.get("/health")
def health_check():
    return {
        "service": config.SERVICE_NAME,
        "status": "healthy",
    }
