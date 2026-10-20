from fastapi import APIRouter, Depends, HTTPException
from typing import List, Optional
from pydantic import BaseModel

from app.schemas.optimization import OptimizationRequest, OptimizationResponse, ScenarioCompareRequest
from app.services.optimization_service import OptimizationService

router = APIRouter()
optimization_service = OptimizationService()

@router.post("/run", response_model=dict)
async def run_optimization(request: OptimizationRequest):
    """Run optimization for energy scheduling"""
    try:
        result = optimization_service.run_optimization(
            dataset_id=request.dataset_id,
            forecast_id=request.forecast_id,
            flexible_loads=[load.dict() for load in request.flexible_loads],
            tariff_schedule=[period.dict() for period in request.tariff_schedule],
            horizon_hours=request.horizon_hours,
            weight_cost=request.weight_cost,
            weight_peak=request.weight_peak,
            solver=request.solver or "milp"
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/scenarios", response_model=dict)
async def compare_scenarios(request: ScenarioCompareRequest):
    """Run multi-scenario comparative optimization"""
    try:
        result = optimization_service.run_scenario_comparison(
            dataset_id=request.dataset_id,
            forecast_id=request.forecast_id,
            flexible_loads=[load.dict() for load in request.flexible_loads],
            tariff_schedule=[period.dict() for period in request.tariff_schedule],
            horizon_hours=request.horizon_hours
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/", response_model=List[dict])
async def list_optimizations():
    """List all optimizations"""
    try:
        optimizations = optimization_service.list_optimizations()
        return optimizations
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{optimization_id}", response_model=dict)
async def get_optimization(optimization_id: str):
    """Get details of a specific optimization"""
    try:
        optimization = optimization_service.get_optimization(optimization_id)
        if not optimization:
            raise HTTPException(status_code=404, detail="Optimization not found")
        return optimization
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))