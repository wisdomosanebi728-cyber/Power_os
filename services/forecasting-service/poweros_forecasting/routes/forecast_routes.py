from datetime import datetime, timezone
from fastapi import APIRouter, Query
from poweros_common.schemas.forecast import ForecastRequest, ForecastResponse
from ..models.demand_predictor import DemandPredictor
from ..models.solar_predictor import SolarPredictor
from ..config import ForecastingConfig

router = APIRouter(prefix="/api/v1/forecast", tags=["AI Forecasting"])
config = ForecastingConfig()


@router.get("/24h", response_model=ForecastResponse)
def get_24h_forecast(
    community_id: str = Query("00000000-0000-0000-0000-000000000001"),
    current_load_kw: float = Query(18.5),
    solar_capacity_kw: float = Query(30.0),
):
    """Generates 24-hour demand and solar yield forecasts with 90% confidence bounds."""
    now = datetime.now(timezone.utc)
    demand_points = DemandPredictor.predict_24h(now, current_load_kw=current_load_kw)
    solar_points = SolarPredictor.predict_24h_solar(now, solar_capacity_kw=solar_capacity_kw)

    for i, pt in enumerate(demand_points):
        if i < len(solar_points):
            pt.predicted_solar_kw = solar_points[i]

    return ForecastResponse(
        generated_at=now,
        community_id=community_id,
        horizon_hours=24,
        points=demand_points,
        model_version="lgbm-diurnal-v1.0",
        is_cold_start=False,
    )


@router.post("/demand", response_model=ForecastResponse)
def request_forecast(req: ForecastRequest):
    now = datetime.now(timezone.utc)
    demand_points = DemandPredictor.predict_24h(now)
    if req.include_solar:
        solar_points = SolarPredictor.predict_24h_solar(now, config.DEFAULT_SOLAR_CAPACITY_KW)
        for i, pt in enumerate(demand_points):
            if i < len(solar_points):
                pt.predicted_solar_kw = solar_points[i]

    return ForecastResponse(
        generated_at=now,
        community_id=req.community_id,
        horizon_hours=req.horizon_hours,
        points=demand_points[:req.horizon_hours],
        model_version="lgbm-diurnal-v1.0",
        is_cold_start=False,
    )
