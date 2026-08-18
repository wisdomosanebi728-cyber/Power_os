from datetime import datetime, timezone
from fastapi.testclient import TestClient
from poweros_common.schemas.telemetry import NormalizedTelemetry
from poweros_ingestion.config import IngestionConfig
from poweros_ingestion.buffer_writer import TelemetryBufferWriter
from poweros_ingestion.main import app


def test_buffer_writer_batching():
    config = IngestionConfig(BATCH_SIZE=3)
    writer = TelemetryBufferWriter(config)

    t1 = NormalizedTelemetry(
        time=datetime.now(timezone.utc),
        community_id="comm-1",
        device_id="sol-001",
        source_type="solar",
        power_kw=10.0,
        energy_kwh=20.0,
    )
    t2 = NormalizedTelemetry(
        time=datetime.now(timezone.utc),
        community_id="comm-1",
        device_id="bat-001",
        source_type="battery",
        power_kw=-5.0,
        energy_kwh=40.0,
    )

    writer.add(t1)
    writer.add(t2)
    assert len(writer.buffer) == 2
    assert writer.total_ingested == 2

    flushed = writer.flush()
    assert flushed == 2
    assert len(writer.buffer) == 0
    assert writer.total_flushed == 2


def test_api_health_endpoint():
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "ingestion-service"


def test_api_http_ingest_endpoint():
    client = TestClient(app)
    payload = {
        "timestamp": "2026-08-15T12:00:00Z",
        "community_id": "00000000-0000-0000-0000-000000000001",
        "device_id": "meter-workshop-01",
        "source_type": "load",
        "power_kw": 4.5,
        "cumulative_kwh": 890.2,
    }
    response = client.post("/api/v1/telemetry/ingest", json=payload)
    assert response.status_code == 202
    data = response.json()
    assert data["status"] == "accepted"
    assert data["device_id"] == "meter-workshop-01"
