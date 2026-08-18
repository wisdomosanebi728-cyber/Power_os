from fastapi import APIRouter, Query
from poweros_common.schemas.optimization import (
    OptimizationRequest,
    OptimizationRecommendation,
)
from ..solver import EconomicDispatchSolver
from ..config import OptimizationConfig

router = APIRouter(prefix="/api/v1/optimization", tags=["Economic Dispatch Optimizer"])
config = OptimizationConfig()
solver = EconomicDispatchSolver(config)


@router.post("/solve", response_model=OptimizationRecommendation)
def solve_optimization(req: OptimizationRequest):
    """Calculates lowest-cost dispatch strategy and explainable directives for given inputs."""
    return solver.solve(req)


@router.get("/recommendation", response_model=OptimizationRecommendation)
def get_live_recommendation(
    community_id: str = Query("00000000-0000-0000-0000-000000000001"),
    current_demand_kw: float = Query(22.5),
    available_solar_kw: float = Query(18.5),
    battery_soc_percent: float = Query(78.5),
    battery_capacity_kwh: float = Query(60.0),
    grid_available: bool = Query(True),
    grid_tariff_per_kwh: float = Query(0.18),
    diesel_price_per_liter: float = Query(1.35),
    generator_efficiency_kwh_l: float = Query(3.2),
):
    """Convenience GET endpoint providing instant live optimization recommendation."""
    req = OptimizationRequest(
        community_id=community_id,
        current_demand_kw=current_demand_kw,
        available_solar_kw=available_solar_kw,
        battery_soc_percent=battery_soc_percent,
        battery_capacity_kwh=battery_capacity_kwh,
        grid_available=grid_available,
        grid_tariff_per_kwh=grid_tariff_per_kwh,
        diesel_price_per_liter=diesel_price_per_liter,
        generator_efficiency_kwh_l=generator_efficiency_kwh_l,
        generator_available=True,
        generator_rated_kw=36.0,
    )
    return solver.solve(req)
