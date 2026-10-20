"""
GridMind AI Backend Entry Point
"""
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

from app.api import datasets, models, forecast, anomalies, optimization, experiments
from app.core.config import settings
from app.core.security import get_api_key
from app.persistence.database import init_db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting GridMind AI backend...")
    init_db()
    logger.info("Database initialized")
    yield
    logger.info("Shutting down GridMind AI backend...")


app = FastAPI(
    title="GridMind AI",
    description="Intelligent Energy Demand Forecasting, Anomaly Detection, and Optimization Platform",
    version="1.0.0",
    lifespan=lifespan,
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

api_auth = [Depends(get_api_key)]

app.include_router(datasets.router, prefix="/api/datasets", tags=["datasets"], dependencies=api_auth)
app.include_router(models.router, prefix="/api/models", tags=["models"], dependencies=api_auth)
app.include_router(forecast.router, prefix="/api/forecast", tags=["forecast"], dependencies=api_auth)
app.include_router(anomalies.router, prefix="/api/anomalies", tags=["anomalies"], dependencies=api_auth)
app.include_router(optimization.router, prefix="/api/optimization", tags=["optimization"], dependencies=api_auth)
app.include_router(experiments.router, prefix="/api/experiments", tags=["experiments"], dependencies=api_auth)


@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "version": "1.0.0"}


@app.get("/")
async def root():
    return {"message": "GridMind AI API", "docs": "/docs", "health": "/api/health"}