from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


class DatasetCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    source: str = Field(..., pattern="^(upload|synthetic|public)$")


class DatasetResponse(BaseModel):
    id: str
    name: str
    source: str
    rows: int
    columns: List[str]
    date_range: dict
    created_at: str

    class Config:
        from_attributes = True


class DataSummary(BaseModel):
    dataset_id: str
    total_consumption: float
    avg_consumption: float
    peak_consumption: float
    min_consumption: float
    missing_values: int
    duplicate_timestamps: int
    date_range: dict