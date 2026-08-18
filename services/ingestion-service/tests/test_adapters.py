import pytest
from poweros_ingestion.adapters.simulator_adapter import SimulatorJsonAdapter
from poweros_ingestion.adapters.sunspec_adapter import SunSpecModbusAdapter
from poweros_ingestion.adapters.meter_adapter import EastronModbusAdapter


def test_simulator_adapter():
    adapter = SimulatorJsonAdapter()
    raw = {
        "timestamp": "2026-08-15T12:00:00Z",
        "community_id": "00000000-0000-0000-0000-000000000001",
        "device_id": "sol-001",
        "source_type": "solar",
        "power_kw": 24.5,
        "daily_yield_kwh": 85.2,
        "voltage_v": 232.0,
        "status": "active",
    }
    normalized = adapter.parse_payload(raw)
    assert normalized.device_id == "sol-001"
    assert normalized.power_kw == 24.5
    assert normalized.energy_kwh == 85.2
    assert normalized.source_type == "solar"


def test_sunspec_modbus_adapter():
    adapter = SunSpecModbusAdapter()
    raw_sunspec = {
        "device_id": "sol-huawei-01",
        "model_id": 103,
        "registers": {
            "W": 245,
            "W_SF": 2,      # 245 * 10^2 = 24500 Watts = 24.5 kW
            "WH": 1124,
            "WH_SF": 2,     # 112400 Wh = 112.4 kWh
            "PhVphA": 2300,
            "PhV_SF": -1,   # 230.0 V
            "Hz": 5000,
            "Hz_SF": -2,    # 50.00 Hz
        },
    }
    normalized = adapter.parse_payload(raw_sunspec)
    assert normalized.device_id == "sol-huawei-01"
    assert normalized.power_kw == 24.5
    assert normalized.energy_kwh == 112.4
    assert normalized.voltage_v == 230.0
    assert normalized.frequency_hz == 50.0


def test_eastron_meter_adapter():
    adapter = EastronModbusAdapter()
    raw_meter = {
        "device_id": "meter-coldstore-01",
        "consumer_type": "commercial_cold_store",
        "measurements": {
            "active_power_kw": 6.85,
            "total_active_kwh": 3450.2,
            "line_voltage_v": 231.5,
            "current_a": 29.8,
            "frequency_hz": 50.05,
        },
    }
    normalized = adapter.parse_payload(raw_meter)
    assert normalized.device_id == "meter-coldstore-01"
    assert normalized.source_type == "load"
    assert normalized.power_kw == 6.85
    assert normalized.energy_kwh == 3450.2
    assert normalized.voltage_v == 231.5
