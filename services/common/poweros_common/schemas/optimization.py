from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class DispatchAction(str, Enum):
    DISPATCH_SOLAR_ONLY = "DISPATCH_SOLAR_ONLY"
    DISPATCH_SOLAR_AND_BATTERY = "DISPATCH_SOLAR_AND_BATTERY"
    DISPATCH_SOLAR_AND_GRID = "DISPATCH_SOLAR_AND_GRID"
    DISPATCH_SOLAR_BATTERY_GRID = "DISPATCH_SOLAR_BATTERY_GRID"
    DISPATCH_GENERATOR_BACKUP = "DISPATCH_GENERATOR_BACKUP"
    LOAD_SHED_NON_CRITICAL = "LOAD_SHED_NON_CRITICAL"
    CHARGE_BATTERY_SURPLUS_SOLAR = "CHARGE_BATTERY_SURPLUS_SOLAR"


class DispatchStrategy(BaseModel):
    solar_target_kw: float = Field(0.0, ge=0.0)
    battery_discharge_target_kw: float = Field(0.0, ge=0.0)
    battery_charge_target_kw: float = Field(0.0, ge=0.0)
    grid_import_target_kw: float = Field(0.0, ge=0.0)
    generator_target_kw: float = Field(0.0, ge=0.0)
    curtailed_solar_kw: float = Field(0.0, ge=0.0)
    shed_load_kw: float = Field(0.0, ge=0.0)


class FinancialImpact(BaseModel):
    current_cost_rate_per_hour: float = Field(..., ge=0.0)
    unoptimized_baseline_cost_per_hour: float = Field(..., ge=0.0)
    hourly_savings: float = Field(..., ge=0.0)
    savings_percentage: float = Field(..., ge=0.0, le=100.0)
    levelized_cost_per_kwh: float = Field(..., ge=0.0)


class ShortageRisk(BaseModel):
    risk_level: str = Field("LOW", description="LOW, MODERATE, HIGH, CRITICAL")
    projected_deficit_kwh: float = Field(0.0, ge=0.0)
    hours_of_battery_autonomy: float = Field(..., ge=0.0)
    recommended_action: Optional[str] = None


class PhysicalConstraints(BaseModel):
    max_inverter_kw: float = Field(..., gt=0.0)
    battery_min_soc_percent: float = Field(20.0, ge=0.0, le=100.0)
    battery_max_charge_kw: float = Field(..., ge=0.0)
    battery_max_discharge_kw: float = Field(..., ge=0.0)
    generator_rated_kw: float = Field(..., ge=0.0)
    generator_min_load_percent: float = Field(30.0, ge=0.0, le=100.0)


class OptimizationRecommendation(BaseModel):
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    community_id: str
    action: DispatchAction
    confidence: float = Field(0.95, ge=0.0, le=1.0)
    strategy_details: DispatchStrategy
    explanation: str
    financial_impact: FinancialImpact
    shortage_risk: ShortageRisk
    physical_guards_verified: bool = True


class OptimizationRequest(BaseModel):
    community_id: str
    current_demand_kw: float = Field(..., ge=0.0)
    available_solar_kw: float = Field(..., ge=0.0)
    battery_soc_percent: float = Field(..., ge=0.0, le=100.0)
    battery_capacity_kwh: float = Field(..., gt=0.0)
    grid_available: bool = True
    grid_tariff_per_kwh: float = Field(0.18, ge=0.0)
    diesel_price_per_liter: float = Field(1.35, gt=0.0)
    generator_efficiency_kwh_l: float = Field(3.2, gt=0.0)
    generator_available: bool = True
    generator_rated_kw: float = Field(50.0, ge=0.0)
    forecast_next_hour_demand_kw: Optional[float] = None
    forecast_next_hour_solar_kw: Optional[float] = None
