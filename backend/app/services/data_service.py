import pandas as pd
import numpy as np
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import uuid
import io
import hashlib

from app.persistence.database import get_db_connection
from app.core.config import settings
from app.schemas.dataset import DatasetCreate, DatasetResponse, DataSummary


class DataService:
    def __init__(self):
        self.data_dir = settings.DATA_DIR

    def upload_dataset(self, file_content: bytes, filename: str) -> DatasetResponse:
        try:
            df = pd.read_csv(io.BytesIO(file_content))
        except Exception as e:
            raise ValueError(f"Invalid CSV file: {str(e)}")

        dataset_id = str(uuid.uuid4())
        dataset_name = Path(filename).stem or f"dataset_{dataset_id[:8]}"

        processed_df = self._preprocess_dataframe(df)

        filepath = self.data_dir / f"{dataset_id}.csv"
        processed_df.to_csv(filepath, index=False)

        columns = list(processed_df.columns)
        rows = len(processed_df)
        date_range_start, date_range_end = self._get_date_range(processed_df)

        with get_db_connection() as conn:
            conn.execute("""
                INSERT INTO datasets (id, name, source, filepath, rows, columns, date_range_start, date_range_end)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                dataset_id,
                dataset_name,
                "upload",
                str(filepath),
                rows,
                ",".join(columns),
                date_range_start.isoformat() if date_range_start else None,
                date_range_end.isoformat() if date_range_end else None
            ))
            conn.commit()

        return DatasetResponse(
            id=dataset_id,
            name=dataset_name,
            source="upload",
            rows=rows,
            columns=columns,
            date_range={
                "start": date_range_start.isoformat() if date_range_start else "",
                "end": date_range_end.isoformat() if date_range_end else ""
            },
            created_at=datetime.now().isoformat()
        )

    def generate_synthetic_dataset(self, days: int = 30, freq: str = 'h', anomalies: bool = True) -> DatasetResponse:
        if days < 1:
            raise ValueError("days must be greater than zero")

        normalized_freq = freq.lower()
        if normalized_freq not in {'h', '15min'}:
            raise ValueError("freq must be 'h' or '15min'")

        dataset_id = str(uuid.uuid4())
        dataset_name = f"synthetic_energy_{days}d"

        start_date = datetime.now() - timedelta(days=days)
        samples_per_hour = 1 if normalized_freq == 'h' else 4
        timestamps = pd.date_range(
            start=start_date,
            periods=days * 24 * samples_per_hour,
            freq=normalized_freq,
        )

        hour_of_day = timestamps.hour.to_numpy() + timestamps.minute.to_numpy() / 60
        day_of_week = timestamps.dayofweek.to_numpy()
        day_of_year = timestamps.dayofyear.to_numpy()
        morning_peak = 0.22 * np.exp(-0.5 * ((hour_of_day - 8) / 2.0) ** 2)
        evening_peak = 0.38 * np.exp(-0.5 * ((hour_of_day - 19) / 2.7) ** 2)
        midday_activity = 0.12 * np.exp(-0.5 * ((hour_of_day - 13) / 3.0) ** 2)
        daily_profile = 0.72 + morning_peak + evening_peak + midday_activity
        weekly_profile = np.where(day_of_week >= 5, 0.78, 1.0)
        seasonal_profile = 1 + 0.08 * np.sin(2 * np.pi * day_of_year / 365.25)
        long_term_trend = np.linspace(0.96, 1.04, len(timestamps))
        rng = np.random.default_rng(settings.RANDOM_SEED)
        noise = rng.normal(0, 2.5, len(timestamps))
        consumption = 50 * daily_profile * weekly_profile * seasonal_profile * long_term_trend + noise
        consumption = np.maximum(consumption, 1.0)

        if anomalies:
            anomaly_indices = rng.choice(len(consumption), size=max(1, len(consumption)//100), replace=False)
            consumption[anomaly_indices] *= rng.uniform(2.0, 3.0, len(anomaly_indices))

        df = pd.DataFrame({
            'timestamp': timestamps,
            'consumption_kwh': consumption
        })

        filepath = self.data_dir / f"{dataset_id}.csv"
        df.to_csv(filepath, index=False)

        with get_db_connection() as conn:
            conn.execute("""
                INSERT INTO datasets (id, name, source, filepath, rows, columns, date_range_start, date_range_end)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                dataset_id,
                dataset_name,
                "synthetic",
                str(filepath),
                len(df),
                ",".join(df.columns),
                df['timestamp'].min().isoformat(),
                df['timestamp'].max().isoformat()
            ))
            conn.commit()

        return DatasetResponse(
            id=dataset_id,
            name=dataset_name,
            source="synthetic",
            rows=len(df),
            columns=list(df.columns),
            date_range={
                "start": df['timestamp'].min().isoformat(),
                "end": df['timestamp'].max().isoformat()
            },
            created_at=datetime.now().isoformat()
        )

    def get_dataset_summary(self, dataset_id: str) -> DataSummary:
        with get_db_connection() as conn:
            cursor = conn.execute("SELECT * FROM datasets WHERE id = ?", (dataset_id,))
            row = cursor.fetchone()
            if not row:
                raise ValueError(f"Dataset {dataset_id} not found")

        filepath = Path(row['filepath'])
        if not filepath.exists():
            raise FileNotFoundError(f"Dataset file not found: {filepath}")

        df = pd.read_csv(filepath)

        total_consumption = df.iloc[:, -1].sum()
        avg_consumption = df.iloc[:, -1].mean()
        peak_consumption = df.iloc[:, -1].max()
        min_consumption = df.iloc[:, -1].min()
        missing_values = df.isnull().sum().sum()
        duplicate_timestamps = len(df) - len(df.drop_duplicates(subset=['timestamp'])) if 'timestamp' in df.columns else 0

        date_range_start = pd.to_datetime(df['timestamp'].min()) if 'timestamp' in df.columns else None
        date_range_end = pd.to_datetime(df['timestamp'].max()) if 'timestamp' in df.columns else None

        return DataSummary(
            dataset_id=dataset_id,
            total_consumption=float(total_consumption),
            avg_consumption=float(avg_consumption),
            peak_consumption=float(peak_consumption),
            min_consumption=float(min_consumption),
            missing_values=int(missing_values),
            duplicate_timestamps=int(duplicate_timestamps),
            date_range={
                "start": date_range_start.isoformat() if date_range_start else "",
                "end": date_range_end.isoformat() if date_range_end else ""
            }
        )

    def list_datasets(self) -> List[DatasetResponse]:
        with get_db_connection() as conn:
            cursor = conn.execute("SELECT id, name, source, rows, columns, date_range_start, date_range_end, created_at FROM datasets ORDER BY created_at DESC")
            rows = cursor.fetchall()

        datasets = []
        for row in rows:
            datasets.append(DatasetResponse(
                id=row['id'],
                name=row['name'],
                source=row['source'],
                rows=row['rows'],
                columns=row['columns'].split(',') if row['columns'] else [],
                date_range={
                    "start": row['date_range_start'] or "",
                    "end": row['date_range_end'] or ""
                },
                created_at=row['created_at']
            ))

        return datasets

    def delete_dataset(self, dataset_id: str) -> bool:
        with get_db_connection() as conn:
            cursor = conn.execute("SELECT filepath FROM datasets WHERE id = ?", (dataset_id,))
            row = cursor.fetchone()
            if row:
                filepath = Path(row['filepath'])
                if filepath.exists():
                    filepath.unlink()
                conn.execute("DELETE FROM datasets WHERE id = ?", (dataset_id,))
                conn.commit()
                return True
        return False

    def _preprocess_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()

        if len(df.columns) == 0:
            raise ValueError("Empty dataset")

        timestamp_col = None
        for col in df.columns:
            if any(keyword in col.lower() for keyword in ['time', 'date', 'timestamp']):
                timestamp_col = col
                break

        if timestamp_col is None:
            df['timestamp'] = pd.date_range(start='2023-01-01', period=len(df), freq='H')
            timestamp_col = 'timestamp'

        df[timestamp_col] = pd.to_datetime(df[timestamp_col], errors='coerce')
        df = df.dropna(subset=[timestamp_col])
        df = df.sort_values(timestamp_col)

        consumption_col = None
        for col in df.columns:
            if any(keyword in col.lower() for keyword in ['energy', 'power', 'consumption', 'demand', 'load', 'kwh', 'kw']):
                if pd.api.types.is_numeric_dtype(df[col]):
                    consumption_col = col
                    break

        if consumption_col is None:
            numeric_cols = df.select_dtypes(include=[np.number]).columns
            if len(numeric_cols) > 0:
                consumption_col = numeric_cols[-1]
            else:
                raise ValueError("No numeric consumption column found")

        result = pd.DataFrame({
            'timestamp': df[timestamp_col],
            'consumption_kwh': pd.to_numeric(df[consumption_col], errors='coerce')
        })
        result = result.dropna()

        if len(result) == 0:
            raise ValueError("No valid data after preprocessing")

        result = result.resample('H', on='timestamp').mean().reset_index()
        result['consumption_kwh'] = result['consumption_kwh'].ffill().bfill()

        return result

    def get_dataset_preview(self, dataset_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        with get_db_connection() as conn:
            cursor = conn.execute("SELECT filepath FROM datasets WHERE id = ?", (dataset_id,))
            row = cursor.fetchone()
            if not row:
                raise ValueError(f"Dataset {dataset_id} not found")

        filepath = Path(row['filepath'])
        if not filepath.exists():
            raise FileNotFoundError(f"Dataset file not found: {filepath}")

        df = pd.read_csv(filepath)
        sample_df = df.head(limit)
        return sample_df.to_dict(orient='records')

    def get_dataset_history(self, dataset_id: str, limit: int = 168) -> List[Dict[str, Any]]:
        with get_db_connection() as conn:
            cursor = conn.execute("SELECT filepath FROM datasets WHERE id = ?", (dataset_id,))
            row = cursor.fetchone()
            if not row:
                raise ValueError(f"Dataset {dataset_id} not found")

        filepath = Path(row['filepath'])
        if not filepath.exists():
            raise FileNotFoundError(f"Dataset file not found: {filepath}")

        df = pd.read_csv(filepath)
        if 'timestamp' in df.columns and 'consumption_kwh' in df.columns:
            recent_df = df.tail(limit)
            return [
                {
                    'timestamp': str(r['timestamp']),
                    'consumption': float(r['consumption_kwh'])
                }
                for _, r in recent_df.iterrows()
            ]
        return []

    def _get_date_range(self, df: pd.DataFrame) -> tuple[Optional[datetime], Optional[datetime]]:
        if 'timestamp' not in df.columns:
            return None, None
        try:
            start = pd.to_datetime(df['timestamp'].min())
            end = pd.to_datetime(df['timestamp'].max())
            return start.to_pydatetime(), end.to_pydatetime()
        except Exception:
            return None, None