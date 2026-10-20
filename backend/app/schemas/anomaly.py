from pydantic import BaseModel, Field
from typing import List, Literal, Optional
from datetime import datetime


class AnomalyEvent(BaseModel):
    timestamp: str
    observed: float
    expected: float
    deviation: float
    deviation_pct: float
    severity: Literal["low", "medium", "high"]
    method: str
    explanation: str


class AnomalySummary(BaseModel):
    total_anomalies: int
    high_severity: int
    medium_severity: int
    low_severity: int


class AnomalyRequest(BaseModel):
    dataset_id: str
    method: Literal["statistical", "isolation_forest", "residual"] = "statistical"
    sensitivity: float = Field(default=2.5, ge=1.0, le=5.0)
    window_size: Optional[int] = Field(default=24, ge=1, le=168)


class AnomalyResponse(BaseModel):
    dataset_id: str
    method: str
    sensitivity: float
    anomalies: List[AnomalyEvent]
    summary: AnomalySummary
    detected_at: str