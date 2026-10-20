from pydantic import BaseModel, Field
from typing import List, Literal, Optional
from datetime import datetime


class FlexibleLoad(BaseModel):
    id: str
    name: str
    power_kw: float = Field(..., gt=0)
    duration_hours: float = Field(..., gt=0)
    earliest_start: str = Field(..., pattern=r"^([01]\d|2[0-3]):([0-5]\d)$")
    latest_end: str = Field(..., pattern=r"^([01]\d|2[0-3]):([0-5]\d)$")
    priority: int = Field(default=1, ge=1)
    continuous: bool = True


class TariffPeriod(BaseModel):
    start_hour: int = Field(..., ge=0, le=23)
    end_hour: int = Field(..., ge=1, le=24)
    rate_per_kwh: float = Field(..., ge=0)


class ScheduleEntry(BaseModel):
    load_id: str
    load_name: str
    start_time: str
    end_time: str
    power_kw: float
    energy_kwh: float
    cost: float


class OptimizationRequest(BaseModel):
    dataset_id: str
    forecast_id: Optional[str] = None
    flexible_loads: List[FlexibleLoad] = Field(..., min_length=1)
    tariff_schedule: List[TariffPeriod] = Field(..., min_length=1)
    horizon_hours: int = Field(default=24, ge=1, le=168)
    weight_cost: float = Field(default=0.7, ge=0, le=1)
    weight_peak: float = Field(default=0.3, ge=0, le=1)
    solver: Optional[str] = "milp"


class OptimizationResponse(BaseModel):
    optimization_id: str
    baseline_schedule: List[ScheduleEntry]
    optimized_schedule: List[ScheduleEntry]
    baseline_demand: List[dict]
    optimized_demand: List[dict]
    baseline_cost: float
    optimized_cost: float
    cost_savings: float
    cost_savings_pct: float
    baseline_peak: float
    optimized_peak: float
    peak_reduction: float
    peak_reduction_pct: float
    constraint_violations: List[str]
    solver: Optional[str] = "milp"
    generated_at: str


class ScenarioCompareRequest(BaseModel):
    dataset_id: str
    forecast_id: Optional[str] = None
    flexible_loads: List[FlexibleLoad] = Field(..., min_length=1)
    tariff_schedule: List[TariffPeriod] = Field(..., min_length=1)
    horizon_hours: int = Field(default=24, ge=1, le=168)