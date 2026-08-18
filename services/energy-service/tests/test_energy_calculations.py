import pytest
from fastapi.testclient import TestClient
from poweros_energy.state_aggregator import EnergyStateAggregator
from poweros_energy.anomaly_detector import AnomalyDetector
from poweros_energy.main import app


def test_energy_aggregation_live_state():
    readings = [
        {"device_id": "sol-001", "source_type": "solar", "power_kw": 20.0},
        {"device_id": "bat-001", "source_type": "battery", "power_kw": 5.0, "soc_percent": 65.0, "stored_energy_kwh": 39.0},
        {"device_id": "grid-001", "source_type": "grid", "power_kw": 0.0, "available": True},
        {"device_id": "gen-001", "source_type": "generator", "power_kw": 0.0, "fuel_level_percent": 90.0},
        {"device_id": "meter-1", "source_type": "load", "consumer_type": "residential", "power_kw": 10.0, "criticality": "medium"},
        {"device_id": "meter-2", "source_type": "load", "consumer_type": "commercial_cold_store", "power_kw": 15.0, "criticality": "high"},
    ]

    state = EnergyStateAggregator.calculate_live_state(readings, community_id="comm-test-1")
    assert state.generation.solar_kw == 20.0
    assert state.generation.battery_discharge_kw == 5.0
    assert state.generation.total_kw == 25.0
    assert state.consumption.total_demand_kw == 25.0
    assert state.consumption.critical_load_kw == 15.0
    assert state.consumption.non_critical_load_kw == 10.0
    assert state.storage.state_of_charge_percent == 65.0
    assert state.current_lcoe_per_kwh > 0.0


def test_anomaly_detection():
    readings = [
        {"device_id": "sol-001", "source_type": "solar", "power_kw": 5.0},
        {"device_id": "bat-001", "source_type": "battery", "power_kw": 10.0, "soc_percent": 22.0, "stored_energy_kwh": 13.2},
        {"device_id": "grid-001", "source_type": "grid", "power_kw": 0.0, "available": False, "status": "offline"},
        {"device_id": "gen-001", "source_type": "generator", "power_kw": 15.0, "fuel_level_percent": 15.0},
        {"device_id": "meter-1", "source_type": "load", "consumer_type": "residential", "power_kw": 30.0},
    ]
    state = EnergyStateAggregator.calculate_live_state(readings, community_id="comm-test-1")
    alerts = AnomalyDetector.detect_anomalies(state)
    alert_codes = {a["code"] for a in alerts}

    assert "GRID_OUTAGE" in alert_codes
    assert "LOW_BATTERY_RESERVE" in alert_codes
    assert "GENERATOR_LOW_FUEL" in alert_codes


def test_energy_endpoints():
    client = TestClient(app)

    # 1. Health
    h_res = client.get("/health")
    assert h_res.status_code == 200

    # 2. Live energy state
    live_res = client.get("/api/v1/communities/00000000-0000-0000-0000-000000000001/energy/live")
    assert live_res.status_code == 200
    live_data = live_res.json()
    assert "generation" in live_data
    assert "storage" in live_data
    assert "consumption" in live_data

    # 3. History
    hist_res = client.get("/api/v1/communities/00000000-0000-0000-0000-000000000001/energy/history?range_hours=12")
    assert hist_res.status_code == 200
    hist_data = hist_res.json()
    assert len(hist_data["series"]) == 13

    # 4. Alerts
    alerts_res = client.get("/api/v1/communities/00000000-0000-0000-0000-000000000001/energy/alerts")
    assert alerts_res.status_code == 200
