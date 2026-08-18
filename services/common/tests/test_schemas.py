from datetime import datetime, timezone
import pytest
from pydantic import ValidationError
from poweros_common.schemas.telemetry import (
    SolarTelemetry,
    BatteryTelemetry,
    GeneratorTelemetry,
    LoadTelemetry,
    TelemetryType,
    DeviceStatus,
)
from poweros_common.schemas.optimization import (
    OptimizationRequest,
    OptimizationRecommendation,
    DispatchAction,
    DispatchStrategy,
    FinancialImpact,
    ShortageRisk,
)


def test_solar_telemetry_valid():
    telemetry = SolarTelemetry(
        community_id="comm-1",
        device_id="sol-001",
        power_kw=15.4,
        daily_yield_kwh=42.1,
        irradiance_w_m2=750.0,
        status=DeviceStatus.ACTIVE,
    )
    assert telemetry.source_type == TelemetryType.SOLAR
    assert telemetry.power_kw == 15.4
    assert telemetry.daily_yield_kwh == 42.1


def test_battery_telemetry_soc_bounds():
    # Valid
    battery = BatteryTelemetry(
        community_id="comm-1",
        device_id="bat-001",
        power_kw=5.0,
        soc_percent=85.5,
        health_percent=98.0,
    )
    assert battery.soc_percent == 85.5

    # Invalid SoC > 100
    with pytest.raises(ValidationError):
        BatteryTelemetry(
            community_id="comm-1",
            device_id="bat-001",
            power_kw=5.0,
            soc_percent=105.0,
        )

    # Invalid SoC < 0
    with pytest.raises(ValidationError):
        BatteryTelemetry(
            community_id="comm-1",
            device_id="bat-001",
            power_kw=5.0,
            soc_percent=-5.0,
        )


def test_optimization_recommendation_schema():
    recommendation = OptimizationRecommendation(
        community_id="comm-1",
        action=DispatchAction.DISPATCH_SOLAR_AND_BATTERY,
        confidence=0.96,
        strategy_details=DispatchStrategy(
            solar_target_kw=18.0,
            battery_discharge_target_kw=4.0,
            grid_import_target_kw=0.0,
            generator_target_kw=0.0,
        ),
        explanation="Solar and battery cover 100% of demand.",
        financial_impact=FinancialImpact(
            current_cost_rate_per_hour=0.85,
            unoptimized_baseline_cost_per_hour=5.50,
            hourly_savings=4.65,
            savings_percentage=84.5,
            levelized_cost_per_kwh=0.038,
        ),
        shortage_risk=ShortageRisk(
            risk_level="LOW",
            projected_deficit_kwh=0.0,
            hours_of_battery_autonomy=8.2,
        ),
    )
    assert recommendation.action == DispatchAction.DISPATCH_SOLAR_AND_BATTERY
    assert recommendation.financial_impact.hourly_savings == 4.65
