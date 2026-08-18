from datetime import datetime, timezone
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field, field_validator


class TelemetryType(str, Enum):
    SOLAR = "solar"
    BATTERY = "battery"
    GRID = "grid"
    GENERATOR = "generator"
    LOAD = "load"


class DeviceStatus(str, Enum):
    ACTIVE = "active"
    STANDBY = "standby"
    CHARGING = "charging"
    DISCHARGING = "discharging"
    FAULT = "fault"
    OFFLINE = "offline"


class BaseTelemetry(BaseModel):
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    community_id: str
    device_id: str
    source_type: TelemetryType
    power_kw: float = Field(..., description="Active power in kW. Positive for generation/consumption, signed for battery.")
    voltage_v: Optional[float] = Field(230.0, description="AC or DC bus voltage")
    current_a: Optional[float] = None
    frequency_hz: Optional[float] = 50.0
    status: DeviceStatus = DeviceStatus.ACTIVE


class SolarTelemetry(BaseTelemetry):
    source_type: TelemetryType = TelemetryType.SOLAR
    daily_yield_kwh: float = Field(0.0, ge=0.0)
    irradiance_w_m2: Optional[float] = Field(None, ge=0.0, le=1500.0)
    temperature_c: Optional[float] = None


class BatteryTelemetry(BaseTelemetry):
    source_type: TelemetryType = TelemetryType.BATTERY
    soc_percent: float = Field(..., ge=0.0, le=100.0, description="State of Charge in %")
    stored_energy_kwh: Optional[float] = Field(None, ge=0.0)
    temperature_c: Optional[float] = None
    health_percent: float = Field(100.0, ge=0.0, le=100.0)
    cycles: Optional[int] = Field(None, ge=0)


class GeneratorTelemetry(BaseTelemetry):
    source_type: TelemetryType = TelemetryType.GENERATOR
    fuel_level_percent: float = Field(..., ge=0.0, le=100.0, description="Fuel tank level in %")
    engine_run_hours: float = Field(0.0, ge=0.0)
    coolant_temp_c: Optional[float] = None
    rpm: Optional[int] = None


class LoadTelemetry(BaseTelemetry):
    source_type: TelemetryType = TelemetryType.LOAD
    consumer_type: str = Field("residential", description="residential, commercial_cold_store, workshop_barber, community_facility")
    cumulative_kwh: float = Field(0.0, ge=0.0)
    power_factor: Optional[float] = Field(0.95, ge=-1.0, le=1.0)
    criticality: str = Field("medium", description="high, medium, low")


class NormalizedTelemetry(BaseModel):
    """Unified internal representation stored in TimescaleDB."""
    time: datetime
    community_id: str
    device_id: str
    source_type: str
    power_kw: float
    energy_kwh: float
    voltage_v: Optional[float] = 230.0
    current_a: Optional[float] = None
    frequency_hz: Optional[float] = 50.0
    soc_percent: Optional[float] = None
    fuel_level_percent: Optional[float] = None
    status: str = "active"
