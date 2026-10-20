from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import JSONResponse
from typing import List
import pandas as pd
from io import BytesIO

from app.schemas.dataset import DatasetCreate, DatasetResponse, DataSummary
from app.services.data_service import DataService

router = APIRouter()
data_service = DataService()

@router.post("/upload", response_model=DatasetResponse)
async def upload_dataset(file: UploadFile = File(...)):
    """Upload a CSV dataset"""
    try:
        content = await file.read()
        dataset = data_service.upload_dataset(content, file.filename)
        return dataset
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/generate-synthetic", response_model=DatasetResponse)
@router.post("/generate", response_model=DatasetResponse)
async def generate_synthetic_dataset(days: int = 30, freq: str = 'h', anomalies: bool = True):
    """Generate a synthetic energy consumption dataset"""
    try:
        dataset = data_service.generate_synthetic_dataset(days=days, freq=freq, anomalies=anomalies)
        return dataset
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/", response_model=List[DatasetResponse])
async def list_datasets():
    """List all datasets"""
    try:
        datasets = data_service.list_datasets()
        return datasets
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{dataset_id}/summary", response_model=DataSummary)
async def get_dataset_summary(dataset_id: str):
    """Get summary statistics for a dataset"""
    try:
        summary = data_service.get_dataset_summary(dataset_id)
        return summary
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.get("/{dataset_id}/preview")
async def get_dataset_preview(dataset_id: str, limit: int = 50):
    """Get sample records from dataset"""
    try:
        preview = data_service.get_dataset_preview(dataset_id, limit=limit)
        return preview
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.get("/{dataset_id}/history")
async def get_dataset_history(dataset_id: str, limit: int = 168):
    """Get recent time-series consumption history for charting"""
    try:
        history = data_service.get_dataset_history(dataset_id, limit=limit)
        return history
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.delete("/{dataset_id}")
async def delete_dataset(dataset_id: str):
    """Delete a dataset"""
    try:
        success = data_service.delete_dataset(dataset_id)
        if not success:
          raise HTTPException(status_code=404, detail="Dataset not found")
        return {"message": "Dataset deleted successfully"}
    except Exception as e:
      raise HTTPException(status_code=500, detail=str(e))