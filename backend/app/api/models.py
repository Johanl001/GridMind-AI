from fastapi import APIRouter, Depends, HTTPException
from typing import List, Optional
from pydantic import BaseModel

from app.schemas.model import ModelCreate, ModelResponse, ModelMetrics
from app.services.forecasting_service import ForecastingService

router = APIRouter()
forecasting_service = ForecastingService()

class TrainModelRequest(BaseModel):
    dataset_id: str
    model_type: str
    hyperparameters: Optional[dict] = None
    train_split: float = 0.7
    val_split: float = 0.15

@router.post("/train", response_model=dict)
async def train_model(request: TrainModelRequest):
    """Train a new forecasting model"""
    try:
        result = forecasting_service.train_model(
            dataset_id=request.dataset_id,
            model_type=request.model_type,
            hyperparameters=request.hyperparameters,
            train_split=request.train_split,
            val_split=request.val_split
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/", response_model=List[dict])
async def list_models():
    """List all trained models"""
    try:
        models = forecasting_service.list_models()
        return models
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{model_id}", response_model=dict)
async def get_model(model_id: str):
    """Get details of a specific model"""
    try:
        model = forecasting_service.get_model(model_id)
        if not model:
            raise HTTPException(status_code=404, detail="Model not found")
        return model
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.get("/{model_id}/metrics", response_model=dict)
async def get_model_metrics(model_id: str):
    """Get metrics and feature importance for a specific model"""
    try:
        metrics = forecasting_service.get_model_metrics(model_id)
        if not metrics:
            raise HTTPException(status_code=404, detail="Model metrics not found")
        return metrics
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.delete("/{model_id}")
async def delete_model(model_id: str):
    """Delete a trained model and its disk artifacts"""
    try:
        success = forecasting_service.delete_model(model_id)
        if not success:
            raise HTTPException(status_code=404, detail="Model not found")
        return {"message": "Model deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{model_id}/forecast", response_model=dict)
async def generate_forecast(model_id: str, horizon_hours: int = 24):
    """Generate forecast using a trained model"""
    try:
        forecast = forecasting_service.generate_forecast(model_id, horizon_hours)
        return forecast
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))