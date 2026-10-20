from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime


class ForecastPrediction(BaseModel):
    timestamp: str
    predicted_consumption: float
    lower_bound: Optional[float] = None
    upper_bound: Optional[float] = None


class ForecastSummary(BaseModel):
    total_predicted: float
    peak_predicted: float
    avg_predicted: float


class ForecastRequest(BaseModel):
    model_id: str
    horizon_hours: int = Field(default=24, ge=1, le=168)
    scenario: Optional[Dict[str, Any]] = None


class ForecastResponse(BaseModel):
    forecast_id: str
    model_id: str
    horizon_hours: int
    predictions: List[ForecastPrediction]
    summary: ForecastSummary
    generated_at: str