import os
from pathlib import Path
from typing import List
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "GridMind AI"
    VERSION: str = "1.0.0"
    DEBUG: bool = True

    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000

    # Use GRIDMIND_API_KEY to avoid collision with any system-level API_KEY env var
    GRIDMIND_API_KEY: str = "dev-secret-change-in-production"

    CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://localhost:4173",
        "http://127.0.0.1:4173",
    ]

    DATA_DIR: Path = Path(__file__).parent.parent.parent / "data"
    MODELS_DIR: Path = Path(__file__).parent.parent.parent / "models"
    EXPERIMENTS_DIR: Path = Path(__file__).parent.parent.parent / "experiments"

    DATABASE_URL: str = "sqlite:///./gridmind.db"

    MAX_UPLOAD_SIZE: int = 10 * 1024 * 1024

    RANDOM_SEED: int = 42

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()


def get_settings() -> Settings:
    return settings


for dir_path in [settings.DATA_DIR, settings.MODELS_DIR, settings.EXPERIMENTS_DIR]:
    dir_path.mkdir(parents=True, exist_ok=True)