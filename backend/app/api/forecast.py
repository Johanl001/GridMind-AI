from fastapi import APIRouter, HTTPException
from typing import List, Optional
from pydantic import BaseModel, Field

from app.services.forecasting_service import ForecastingService
from app.schemas.forecast import ForecastRequest, ForecastResponse

router = APIRouter()
forecasting_service = ForecastingService()


@router.post("/", response_model=dict)
async def generate_forecast(request: ForecastRequest):
    """Generate forecast using a trained model"""
    try:
        result = forecasting_service.generate_forecast(
            model_id=request.model_id,
            horizon_hours=request.horizon_hours
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/", response_model=List[dict])
async def list_forecasts():
    """List all forecasts"""
    try:
        forecasts = forecasting_service.list_forecasts()
        return forecasts
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{forecast_id}", response_model=dict)
async def get_forecast(forecast_id: str):
    """Get details of a specific forecast"""
    try:
        forecast = forecasting_service.get_forecast(forecast_id)
        if not forecast:
            raise HTTPException(status_code=404, detail="Forecast not found")
        return forecast
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))