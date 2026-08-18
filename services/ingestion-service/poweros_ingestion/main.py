from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from poweros_common.schemas.telemetry import NormalizedTelemetry
from .config import IngestionConfig
from .buffer_writer import TelemetryBufferWriter
from .mqtt_consumer import MqttTelemetryConsumer
from .adapters.simulator_adapter import SimulatorJsonAdapter

config = IngestionConfig()
buffer_writer = TelemetryBufferWriter(config)
mqtt_consumer = MqttTelemetryConsumer(config, buffer_writer)
simulator_adapter = SimulatorJsonAdapter()


@asynccontextmanager
async def lifespan(app: FastAPI):
    buffer_writer.start()
    mqtt_consumer.start()
    yield
    mqtt_consumer.stop()
    buffer_writer.stop()


app = FastAPI(
    title="POWER OS - Ingestion Gateway",
    version="0.1.0",
    description="IoT Gateway and Telemetry Ingestion Service for POWER OS",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health_check():
    return {
        "service": config.SERVICE_NAME,
        "status": "healthy",
        "mqtt_connected": mqtt_consumer.is_connected,
        "database_connected": buffer_writer.db_available,
        "redis_connected": buffer_writer.redis_client is not None,
    }


@app.get("/metrics")
def get_metrics():
    return {
        "total_ingested": buffer_writer.total_ingested,
        "total_flushed": buffer_writer.total_flushed,
        "total_dropped": buffer_writer.total_dropped,
        "current_buffer_depth": len(buffer_writer.buffer),
    }


@app.post("/api/v1/telemetry/ingest", status_code=status.HTTP_202_ACCEPTED)
def ingest_http_telemetry(payload: dict):
    try:
        normalized = simulator_adapter.parse_payload(payload)
        buffer_writer.add(normalized)
        return {"status": "accepted", "device_id": normalized.device_id, "timestamp": normalized.time.isoformat()}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Malformed telemetry payload: {str(e)}",
        )
