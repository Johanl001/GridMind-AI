from fastapi import APIRouter, Depends, HTTPException
from typing import List, Optional
from pydantic import BaseModel

from app.schemas.anomaly import AnomalyRequest, AnomalyResponse
from app.services.anomaly_service import AnomalyService

router = APIRouter()
anomaly_service = AnomalyService()

@router.post("/detect", response_model=dict)
async def detect_anomalies(request: AnomalyRequest):
    """Detect anomalies in a dataset"""
    try:
        result = anomaly_service.detect_anomalies(
            dataset_id=request.dataset_id,
            method=request.method,
            sensitivity=request.sensitivity,
            window_size=request.window_size
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/", response_model=List[dict])
async def list_anomalies():
    """List all anomaly detections"""
    try:
        anomalies = anomaly_service.list_anomalies()
        return anomalies
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{anomaly_id}", response_model=dict)
async def get_anomaly(anomaly_id: str):
    """Get details of a specific anomaly detection"""
    try:
        anomaly = anomaly_service.get_anomaly(anomaly_id)
        if not anomaly:
            raise HTTPException(status_code=404, detail="Anomaly not found")
        return anomaly
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))