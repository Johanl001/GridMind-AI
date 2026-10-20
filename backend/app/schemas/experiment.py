from pydantic import BaseModel, Field
from typing import Dict, Any, Optional
from datetime import datetime


class ExperimentCreate(BaseModel):
    dataset_id: str
    model_type: str
    hyperparameters: Optional[Dict[str, Any]] = None
    train_split: float = Field(default=0.7, ge=0.5, le=0.9)
    val_split: float = Field(default=0.15, ge=0.05, le=0.3)


class ExperimentResponse(BaseModel):
    id: str
    name: str
    dataset_id: str
    model_type: str
    hyperparameters: Optional[Dict[str, Any]] = None
    train_range: dict
    val_range: dict
    test_range: dict
    val_metrics: dict
    test_metrics: Optional[dict] = None
    training_duration: float
    created_at: str

    class Config:
        from_attributes = True