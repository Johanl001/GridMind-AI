from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, Literal
from datetime import datetime


class ModelMetrics(BaseModel):
    mae: float
    mse: float
    rmse: float
    r2: float
    mape: Optional[float] = None


class ModelStatus(str):
    pass


class ModelCreate(BaseModel):
    dataset_id: str
    model_type: str
    hyperparameters: Optional[Dict[str, Any]] = None
    train_split: float = Field(default=0.7, ge=0.5, le=0.9)
    val_split: float = Field(default=0.15, ge=0.05, le=0.3)


class ModelResponse(BaseModel):
    id: str
    name: str
    type: str
    dataset_id: str
    status: Literal["training", "ready", "failed"]
    metrics: Optional[ModelMetrics] = None
    created_at: str
    training_duration: Optional[float] = None

    class Config:
        from_attributes = True