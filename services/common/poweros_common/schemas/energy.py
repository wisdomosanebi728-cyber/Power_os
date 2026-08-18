from datetime import datetime, timezone
from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class GenerationMix(BaseModel):
    solar_kw: float = Field(0.0, ge=0.0)
    battery_discharge_kw: float = Field(0.0, ge=0.0)
    grid_import_kw: float = Field(0.0, ge=0.0)
    generator_kw: float = Field(0.0, ge=0.0)
    total_kw: float = Field(0.0, ge=0.0)


class StorageState(BaseModel):
    battery_capacity_kwh: float = Field(..., ge=0.0)
    battery_stored_kwh: float = Field(..., ge=0.0)
    state_of_charge_percent: float = Field(..., ge=0.0, le=100.0)
    battery_charging_kw: float = Field(0.0, ge=0.0)
    battery_health_percent: float = Field(100.0, ge=0.0, le=100.0)


class ConsumptionBreakdown(BaseModel):
    total_demand_kw: float = Field(0.0, ge=0.0)
    breakdown_by_category: Dict[str, float] = Field(default_factory=dict)
    critical_load_kw: float = Field(0.0, ge=0.0)
    non_critical_load_kw: float = Field(0.0, ge=0.0)


class GridState(BaseModel):
    available: bool = True
    current_power_kw: float = Field(0.0, ge=0.0)
    tariff_per_kwh: float = Field(0.18, ge=0.0)


class GeneratorState(BaseModel):
    running: bool = False
    current_output_kw: float = Field(0.0, ge=0.0)
    fuel_level_percent: float = Field(100.0, ge=0.0, le=100.0)
    cost_per_kwh: float = Field(0.42, ge=0.0)


class LiveEnergyState(BaseModel):
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    community_id: str
    generation: GenerationMix
    storage: StorageState
    consumption: ConsumptionBreakdown
    grid_status: GridState
    generator_status: GeneratorState
    current_lcoe_per_kwh: float = Field(0.0, ge=0.0)
    carbon_intensity_g_co2_kwh: Optional[float] = None


class EnergySummaryWindow(BaseModel):
    start_time: datetime
    end_time: datetime
    solar_generated_kwh: float
    battery_cycled_kwh: float
    grid_imported_kwh: float
    generator_produced_kwh: float
    total_consumed_kwh: float
    total_cost: float
    estimated_savings: float
