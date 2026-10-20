import sqlite3
import os
from pathlib import Path
from contextlib import contextmanager
from app.core.config import settings


def get_db_path() -> str:
    db_url = settings.DATABASE_URL
    if db_url.startswith("sqlite:///"):
        return db_url.replace("sqlite:///", "")
    return "./gridmind.db"


@contextmanager
def get_db_connection():
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def init_db():
    db_path = get_db_path()
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    with get_db_connection() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS datasets (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                source TEXT NOT NULL,
                filepath TEXT,
                rows INTEGER,
                columns TEXT,
                date_range_start TEXT,
                date_range_end TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS models (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                type TEXT NOT NULL,
                dataset_id TEXT NOT NULL,
                STATUS TEXT NOT NULL,
                filepath TEXT,
                hyperparameters TEXT,
                train_split REAL,
                val_split REAL,
                train_range_start TEXT,
                train_range_end TEXT,
                val_range_start TEXT,
                val_range_end TEXT,
                test_range_start TEXT,
                test_range_end TEXT,
                training_duration REAL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (dataset_id) REFERENCES datasets (id)
            );

            CREATE TABLE IF NOT EXISTS model_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                model_id TEXT NOT NULL,
                mae REAL,
                mse REAL,
                rmse REAL,
                r2 REAL,
                mape REAL,
                split TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (model_id) REFERENCES models (id)
            );

            CREATE TABLE IF NOT EXISTS experiments (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                dataset_id TEXT NOT NULL,
                model_type TEXT NOT NULL,
                hyperparameters TEXT,
                train_range_start TEXT,
                train_range_end TEXT,
                val_range_start TEXT,
                val_range_end TEXT,
                test_range_start TEXT,
                test_range_end TEXT,
                training_duration REAL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (dataset_id) REFERENCES datasets (id)
            );

            CREATE TABLE IF NOT EXISTS experiment_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                experiment_id TEXT NOT NULL,
                mae REAL,
                mse REAL,
                rmse REAL,
                r2 REAL,
                mape REAL,
                split TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (experiment_id) REFERENCES experiments (id)
            );

            CREATE TABLE IF NOT EXISTS forecasts (
                id TEXT PRIMARY KEY,
                model_id TEXT NOT NULL,
                horizon_hours INTEGER NOT NULL,
                predictions TEXT NOT NULL,
                summary TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (model_id) REFERENCES models (id)
            );

            CREATE TABLE IF NOT EXISTS anomalies (
                id TEXT PRIMARY KEY,
                dataset_id TEXT NOT NULL,
                method TEXT NOT NULL,
                sensitivity REAL NOT NULL,
                anomalies_data TEXT NOT NULL,
                summary TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (dataset_id) REFERENCES datasets (id)
            );

            CREATE TABLE IF NOT EXISTS optimizations (
                id TEXT PRIMARY KEY,
                dataset_id TEXT NOT NULL,
                forecast_id TEXT,
                flexible_loads TEXT NOT NULL,
                tariff_schedule TEXT NOT NULL,
                horizon_hours INTEGER NOT NULL,
                weight_cost REAL NOT NULL,
                weight_peak REAL NOT NULL,
                baseline_schedule TEXT NOT NULL,
                optimized_schedule TEXT NOT NULL,
                baseline_demand TEXT NOT NULL,
                optimized_demand TEXT NOT NULL,
                baseline_cost REAL NOT NULL,
                optimized_cost REAL NOT NULL,
                cost_savings REAL NOT NULL,
                cost_savings_pct REAL NOT NULL,
                baseline_peak REAL NOT NULL,
                optimized_peak REAL NOT NULL,
                peak_reduction REAL NOT NULL,
                peak_reduction_pct REAL NOT NULL,
                constraint_violations TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (dataset_id) REFERENCES datasets (id)
            );
        """)

        # Schema migrations for existing databases
        cursor = conn.cursor()
        for table, col in [
            ("models", "feature_importance TEXT"),
            ("experiments", "feature_importance TEXT"),
            ("optimizations", "solver TEXT DEFAULT 'milp'"),
            ("anomalies", "window_size INTEGER DEFAULT 24"),
        ]:
            try:
                cursor.execute(f"ALTER TABLE {table} ADD COLUMN {col};")
            except sqlite3.OperationalError:
                pass  # column already exists

        conn.commit()