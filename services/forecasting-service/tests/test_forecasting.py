from datetime import datetime, timezone
import pytest
from fastapi.testclient import TestClient
from poweros_forecasting.models.demand_predictor import DemandPredictor
from poweros_forecasting.models.solar_predictor import SolarPredictor
from poweros_forecasting.main import app


def test_demand_predictor_physics():
    base_time = datetime(2026, 8, 15, 0, 0, 0, tzinfo=timezone.utc)
    points = DemandPredictor.predict_24h(base_time, current_load_kw=15.0)

    assert len(points) == 24
    for pt in points:
        assert pt.predicted_demand_kw > 0.0
        assert pt.confidence_lower_kw <= pt.predicted_demand_kw <= pt.confidence_upper_kw
        assert 0.0 <= pt.confidence_score <= 1.0

    # Verify peak hours have higher load than 03:00 AM
    night_load = points[2].predicted_demand_kw  # ~03:00
    evening_load = points[19].predicted_demand_kw  # ~20:00
    assert evening_load > night_load


def test_solar_predictor_physics():
    base_time = datetime(2026, 8, 15, 0, 0, 0, tzinfo=timezone.utc)
    solar_yields = SolarPredictor.predict_24h_solar(base_time, solar_capacity_kw=30.0)

    assert len(solar_yields) == 24
    # Hour 2 (02:00) -> 0 kW
    assert solar_yields[1] == 0.0
    # Hour 12 (12:00) -> Peak solar > 20 kW
    assert solar_yields[11] > 20.0


def test_forecast_api_endpoints():
    client = TestClient(app)

    # 1. Health
    h_res = client.get("/health")
    assert h_res.status_code == 200
    assert h_res.json()["status"] == "healthy"

    # 2. 24h forecast
    f_res = client.get("/api/v1/forecast/24h")
    assert f_res.status_code == 200
    data = f_res.json()
    assert data["horizon_hours"] == 24
    assert len(data["points"]) == 24
    assert "predicted_demand_kw" in data["points"][0]
    assert "predicted_solar_kw" in data["points"][0]
