from datetime import datetime, timezone
from typing import List, Optional
from pydantic import BaseModel, Field


class DemandForecastPoint(BaseModel):
    timestamp: datetime
    predicted_demand_kw: float = Field(..., ge=0.0)
    predicted_solar_kw: float = Field(0.0, ge=0.0)
    confidence_lower_kw: float = Field(..., ge=0.0)
    confidence_upper_kw: float = Field(..., ge=0.0)
    confidence_score: float = Field(0.85, ge=0.0, le=1.0)


class ForecastRequest(BaseModel):
    community_id: str
    horizon_hours: int = Field(24, ge=1, le=72)
    include_solar: bool = True


class ForecastResponse(BaseModel):
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    community_id: str
    horizon_hours: int
    points: List[DemandForecastPoint]
    model_version: str = "lgbm-v1.0"
    is_cold_start: bool = False
