import pandas as pd
import numpy as np
import uuid
import json
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler

from app.persistence.database import get_db_connection
from app.core.config import settings
from app.services.data_service import DataService


class AnomalyService:
    def __init__(self):
        self.data_service = DataService()

    def _prepare_data(self, df: pd.DataFrame, target_col: str = 'consumption_kwh') -> pd.DataFrame:
        df = df.copy()
        df = df.sort_values('timestamp')
        df = df.set_index('timestamp')

        features = pd.DataFrame(index=df.index)
        features['consumption'] = df[target_col]
        features['hour'] = df.index.hour
        features['day_of_week'] = df.index.dayofweek
        features['is_weekend'] = (df.index.dayofweek >= 5).astype(int)

        features['rolling_mean'] = df[target_col].rolling(24, min_periods=1).mean()
        features['rolling_std'] = df[target_col].rolling(24, min_periods=1).std().fillna(0)
        features['rolling_min'] = df[target_col].rolling(24, min_periods=1).min()
        features['rolling_max'] = df[target_col].rolling(24, min_periods=1).max()

        features['lag_1'] = df[target_col].shift(1)
        features['lag_24'] = df[target_col].shift(24)

        features = features.ffill().bfill().fillna(0)
        return features

    def detect_statistical_anomalies(
        self,
        df: pd.DataFrame,
        sensitivity: float = 2.5,
        window_size: int = 24,
        target_col: str = 'consumption_kwh'
    ) -> Tuple[List[Dict[str, Any]], Dict[str, int]]:
        df = df.copy()
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.sort_values('timestamp')
        df = df.set_index('timestamp')

        consumption = df[target_col]
        rolling_mean = consumption.rolling(window=window_size, center=True, min_periods=1).mean()
        rolling_std = consumption.rolling(window=window_size, center=True, min_periods=1).std().fillna(0)

        upper_bound = rolling_mean + (sensitivity * rolling_std)
        lower_bound = rolling_mean - (sensitivity * rolling_std)

        is_anomaly = (consumption > upper_bound) | (consumption < lower_bound)
        anomaly_indices = consumption[is_anomaly].index

        anomalies = []
        for idx in anomaly_indices:
            observed = float(consumption.loc[idx])
            expected = float(rolling_mean.loc[idx])
            std_val = float(rolling_std.loc[idx]) if float(rolling_std.loc[idx]) > 0 else 1.0
            deviation = observed - expected
            deviation_pct = (deviation / expected * 100) if expected != 0 else 0.0
            z_score = deviation / std_val

            abs_dev = abs(deviation_pct)
            if abs_dev > 50 or abs(z_score) > 3.5:
                severity = "high"
            elif abs_dev > 25 or abs(z_score) > 2.5:
                severity = "medium"
            else:
                severity = "low"

            hour = idx.hour
            is_weekend = idx.dayofweek >= 5

            if deviation > 0:
                if 0 <= hour <= 5:
                    category = "Abnormal Overnight Spike"
                    rec = "Investigate unexpected overnight equipment operation or HVAC control override."
                elif is_weekend:
                    category = "Unexpected Weekend Surge"
                    rec = "Verify facility weekend schedules or unauthorized baseload draw."
                else:
                    category = "Peak Demand Surge"
                    rec = "Evaluate load shifting options or stage heavy equipment to reduce peak charges."
                detail_desc = f"Load exceeded {window_size}h moving envelope by {abs(deviation):.2f} kW ({deviation_pct:+.1f}%, Z: {z_score:+.2f})."
            else:
                if observed < 0.1 * expected:
                    category = "Severe Drop / Potential Outage"
                    rec = "Check sensor telemetry and supply line continuity; potential equipment trip."
                else:
                    category = "Uncharacteristic Demand Drop"
                    rec = "Verify expected operational downtime or metering drop."
                detail_desc = f"Load dropped below {window_size}h moving envelope by {abs(deviation):.2f} kW ({deviation_pct:+.1f}%, Z: {z_score:+.2f})."

            anomalies.append({
                'timestamp': idx.isoformat(),
                'observed': round(observed, 2),
                'expected': round(expected, 2),
                'deviation': round(deviation, 2),
                'deviation_pct': round(deviation_pct, 1),
                'z_score': round(z_score, 2),
                'severity': severity,
                'method': 'statistical',
                'category': category,
                'recommendation': rec,
                'explanation': detail_desc
            })

        summary = {
            'total_anomalies': len(anomalies),
            'high_severity': sum(1 for a in anomalies if a['severity'] == 'high'),
            'medium_severity': sum(1 for a in anomalies if a['severity'] == 'medium'),
            'low_severity': sum(1 for a in anomalies if a['severity'] == 'low')
        }

        return anomalies, summary

    def detect_isolation_forest_anomalies(
        self,
        df: pd.DataFrame,
        sensitivity: float = 2.5,
        target_col: str = 'consumption_kwh'
    ) -> Tuple[List[Dict[str, Any]], Dict[str, int]]:
        df = df.copy()
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        features = self._prepare_data(df, target_col)

        scaler = StandardScaler()
        features_scaled = scaler.fit_transform(features)

        contamination = min(0.12, max(0.01, 1.0 / (sensitivity * 10)))
        iso_forest = IsolationForest(contamination=contamination, random_state=42, n_estimators=100)
        anomaly_labels = iso_forest.fit_predict(features_scaled)

        anomaly_indices = features[anomaly_labels == -1].index
        anomaly_scores = iso_forest.decision_function(features_scaled)[anomaly_labels == -1]

        anomalies = []
        normal_mask = anomaly_labels != -1
        normal_mean = float(features.loc[normal_mask, 'consumption'].mean()) if np.any(normal_mask) else 0.0

        for idx, score in zip(anomaly_indices, anomaly_scores):
            observed = float(features.loc[idx, 'consumption'])
            expected = normal_mean if normal_mean > 0 else observed
            deviation = observed - expected
            deviation_pct = (deviation / expected * 100) if expected != 0 else 0.0

            if abs(score) > 0.15 or abs(deviation_pct) > 40:
                severity = "high"
            elif abs(score) > 0.08 or abs(deviation_pct) > 20:
                severity = "medium"
            else:
                severity = "low"

            category = "Multivariate Pattern Outlier" if abs(deviation_pct) < 25 else ("Multi-feature Surge" if deviation > 0 else "Multi-feature Drop")
            rec = "Examine joint feature correlations (temperature, time-of-week, lag history) that deviated from typical clusters."
            detail_desc = f"Isolation Forest detected abnormal multivariate cluster (Score: {score:.3f}, Deviation: {deviation_pct:+.1f}% vs typical)."

            anomalies.append({
                'timestamp': idx.isoformat(),
                'observed': round(observed, 2),
                'expected': round(expected, 2),
                'deviation': round(deviation, 2),
                'deviation_pct': round(deviation_pct, 1),
                'z_score': round(float(-score * 10), 2),
                'severity': severity,
                'method': 'isolation_forest',
                'category': category,
                'recommendation': rec,
                'explanation': detail_desc
            })

        summary = {
            'total_anomalies': len(anomalies),
            'high_severity': sum(1 for a in anomalies if a['severity'] == 'high'),
            'medium_severity': sum(1 for a in anomalies if a['severity'] == 'medium'),
            'low_severity': sum(1 for a in anomalies if a['severity'] == 'low')
        }

        return anomalies, summary

    def detect_residual_anomalies(
        self,
        df: pd.DataFrame,
        model_id: str,
        sensitivity: float = 2.5,
        target_col: str = 'consumption_kwh'
    ) -> Tuple[List[Dict[str, Any]], Dict[str, int]]:
        from app.services.forecasting_service import ForecastingService, MODEL_REGISTRY
        forecasting_service = ForecastingService()

        model_info = forecasting_service.get_model(model_id)
        if not model_info:
            raise ValueError(f"Model {model_id} not found")

        df = df.copy()
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        X, y = forecasting_service._create_features(df, target_col)

        forecaster = MODEL_REGISTRY[model_info['type']]()
        forecaster.fit(X, y)
        predictions = forecaster.predict(X)

        residuals = y.values - predictions
        residual_mean = float(np.mean(residuals))
        residual_std = float(np.std(residuals))
        if residual_std <= 1e-4:
            residual_std = 1.0

        threshold = sensitivity * residual_std
        is_anomaly = np.abs(residuals - residual_mean) > threshold
        anomaly_indices = y.index[is_anomaly]

        anomalies = []
        for idx in anomaly_indices:
            pos = y.index.get_loc(idx)
            observed = float(y.iloc[pos])
            expected = float(predictions[pos])
            res = float(residuals[pos])
            dev_pct = (res / expected * 100) if expected != 0 else 0.0
            z_score = (res - residual_mean) / residual_std

            if abs(res) > 2.0 * threshold or abs(dev_pct) > 40:
                severity = "high"
            elif abs(res) > 1.3 * threshold or abs(dev_pct) > 20:
                severity = "medium"
            else:
                severity = "low"

            category = f"Model Residual Outlier ({model_info['type']})"
            rec = "Assess whether unmodeled external shocks (e.g. weather extremes, scheduled maintenance) occurred."
            detail_desc = f"Forecast prediction missed observed by {res:+.2f} kW ({dev_pct:+.1f}%), exceeding 99% residual tolerance bound ({threshold:.2f} kW)."

            anomalies.append({
                'timestamp': idx.isoformat(),
                'observed': round(observed, 2),
                'expected': round(expected, 2),
                'deviation': round(res, 2),
                'deviation_pct': round(dev_pct, 1),
                'z_score': round(z_score, 2),
                'severity': severity,
                'method': 'residual',
                'category': category,
                'recommendation': rec,
                'explanation': detail_desc
            })

        summary = {
            'total_anomalies': len(anomalies),
            'high_severity': sum(1 for a in anomalies if a['severity'] == 'high'),
            'medium_severity': sum(1 for a in anomalies if a['severity'] == 'medium'),
            'low_severity': sum(1 for a in anomalies if a['severity'] == 'low')
        }

        return anomalies, summary

    def detect_anomalies(
        self,
        dataset_id: str,
        method: str = "statistical",
        sensitivity: float = 2.5,
        window_size: Optional[int] = 24
    ) -> Dict[str, Any]:
        filepath = self.data_service.data_dir / f"{dataset_id}.csv"
        if not filepath.exists():
            raise FileNotFoundError(f"Dataset {dataset_id} file not found")
        df = pd.read_csv(filepath)

        if method == "statistical":
            anomalies, summary_dict = self.detect_statistical_anomalies(df, sensitivity, window_size or 24)
        elif method == "isolation_forest":
            anomalies, summary_dict = self.detect_isolation_forest_anomalies(df, sensitivity)
        elif method == "residual":
            from app.services.forecasting_service import ForecastingService
            forecasting_service = ForecastingService()
            models = forecasting_service.list_models()
            model_id = None
            for m in models:
                if m['dataset_id'] == dataset_id and m['status'] == 'ready':
                    model_id = m['id']
                    break
            if not model_id:
                # Train a quick Ridge model for residual detection if no model exists
                ridge_res = forecasting_service.train_model(dataset_id=dataset_id, model_type='ridge')
                model_id = ridge_res['id']
            anomalies, summary_dict = self.detect_residual_anomalies(df, model_id, sensitivity)
        else:
            raise ValueError(f"Unknown anomaly detection method: {method}")

        anomaly_id = str(uuid.uuid4())
        gen_time = datetime.now().isoformat()

        with get_db_connection() as conn:
            conn.execute("""
                INSERT INTO anomalies (id, dataset_id, method, sensitivity, anomalies_data, summary, window_size, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                anomaly_id,
                dataset_id,
                method,
                sensitivity,
                json.dumps(anomalies),
                json.dumps(summary_dict),
                window_size or 24,
                gen_time
            ))
            conn.commit()

        return {
            'anomaly_id': anomaly_id,
            'dataset_id': dataset_id,
            'method': method,
            'sensitivity': sensitivity,
            'window_size': window_size or 24,
            'anomalies': anomalies,
            'summary': summary_dict,
            'detected_at': gen_time,
        }

    def get_anomaly(self, anomaly_id: str) -> Optional[Dict[str, Any]]:
        with get_db_connection() as conn:
            cursor = conn.execute("SELECT * FROM anomalies WHERE id = ?", (anomaly_id,))
            row = cursor.fetchone()
            if not row:
                return None

        anomalies = json.loads(row['anomalies_data']) if row['anomalies_data'] else []
        summary = json.loads(row['summary']) if row['summary'] else {}

        return {
            'id': row['id'],
            'dataset_id': row['dataset_id'],
            'method': row['method'],
            'sensitivity': row['sensitivity'],
            'window_size': row['window_size'] if 'window_size' in row.keys() else 24,
            'anomalies': anomalies,
            'summary': summary,
            'detected_at': row['created_at'],
        }

    def list_anomalies(self) -> List[Dict[str, Any]]:
        with get_db_connection() as conn:
            cursor = conn.execute("SELECT * FROM anomalies ORDER BY created_at DESC")
            rows = cursor.fetchall()

        anomalies_list = []
        for row in rows:
            anomalies = json.loads(row['anomalies_data']) if row['anomalies_data'] else []
            summary = json.loads(row['summary']) if row['summary'] else {}
            anomalies_list.append({
                'id': row['id'],
                'dataset_id': row['dataset_id'],
                'method': row['method'],
                'sensitivity': row['sensitivity'],
                'window_size': row['window_size'] if 'window_size' in row.keys() else 24,
                'anomalies': anomalies,
                'summary': summary,
                'detected_at': row['created_at'],
            })
        return anomalies_list