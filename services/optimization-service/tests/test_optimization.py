import pytest
from fastapi.testclient import TestClient
from poweros_common.schemas.optimization import (
    OptimizationRequest,
    DispatchAction,
)
from poweros_optimization.config import OptimizationConfig
from poweros_optimization.solver import EconomicDispatchSolver
from poweros_optimization.main import app


def test_optimization_solar_and_battery():
    config = OptimizationConfig()
    solver = EconomicDispatchSolver(config)

    # 15 kW demand, 10 kW solar, 70% battery SoC (healthy)
    req = OptimizationRequest(
        community_id="comm-1",
        current_demand_kw=15.0,
        available_solar_kw=10.0,
        battery_soc_percent=70.0,
        battery_capacity_kwh=60.0,
        grid_available=True,
    )
    rec = solver.solve(req)

    assert rec.action == DispatchAction.DISPATCH_SOLAR_AND_BATTERY
    assert rec.strategy_details.solar_target_kw == 10.0
    assert rec.strategy_details.battery_discharge_target_kw == 5.0
    assert rec.strategy_details.generator_target_kw == 0.0
    assert rec.financial_impact.hourly_savings > 0.0
    assert rec.physical_guards_verified is True


def test_battery_empty_guard_no_discharge():
    config = OptimizationConfig()
    solver = EconomicDispatchSolver(config)

    # Battery at minimum reserve (20% SoC)
    req = OptimizationRequest(
        community_id="comm-1",
        current_demand_kw=20.0,
        available_solar_kw=5.0,
        battery_soc_percent=20.0,  # Empty!
        battery_capacity_kwh=60.0,
        grid_available=True,
    )
    rec = solver.solve(req)

    # Battery must NOT be discharged below 20%
    assert rec.strategy_details.battery_discharge_target_kw == 0.0
    assert rec.strategy_details.solar_target_kw == 5.0
    assert rec.strategy_details.grid_import_target_kw == 15.0


def test_surplus_solar_charges_battery():
    config = OptimizationConfig()
    solver = EconomicDispatchSolver(config)

    # Solar 25 kW > Demand 10 kW -> 15 kW excess
    req = OptimizationRequest(
        community_id="comm-1",
        current_demand_kw=10.0,
        available_solar_kw=25.0,
        battery_soc_percent=50.0,
        battery_capacity_kwh=60.0,
        grid_available=True,
    )
    rec = solver.solve(req)

    assert rec.action == DispatchAction.CHARGE_BATTERY_SURPLUS_SOLAR
    assert rec.strategy_details.solar_target_kw == 10.0
    assert rec.strategy_details.battery_charge_target_kw > 0.0


def test_grid_blackout_genset_fallback():
    config = OptimizationConfig()
    solver = EconomicDispatchSolver(config)

    # Night time (0 kW solar), Grid down, Battery depleted (20%) -> Generator must start
    req = OptimizationRequest(
        community_id="comm-1",
        current_demand_kw=20.0,
        available_solar_kw=0.0,
        battery_soc_percent=20.0,
        battery_capacity_kwh=60.0,
        grid_available=False,
        generator_available=True,
        generator_rated_kw=36.0,
    )
    rec = solver.solve(req)

    assert rec.action == DispatchAction.DISPATCH_GENERATOR_BACKUP
    assert rec.strategy_details.generator_target_kw == 20.0
    assert rec.strategy_details.battery_discharge_target_kw == 0.0


def test_optimization_api_endpoints():
    client = TestClient(app)

    # 1. Health
    h_res = client.get("/health")
    assert h_res.status_code == 200

    # 2. Live recommendation GET
    rec_res = client.get("/api/v1/optimization/recommendation")
    assert rec_res.status_code == 200
    data = rec_res.json()
    assert "action" in data
    assert "strategy_details" in data
    assert "financial_impact" in data
    assert "explanation" in data
