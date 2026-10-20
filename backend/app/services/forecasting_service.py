import pandas as pd
import numpy as np
import uuid
import json
import time
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
import joblib

from sklearn.linear_model import LinearRegression, Ridge, Lasso
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.preprocessing import StandardScaler
from xgboost import XGBRegressor

from app.persistence.database import get_db_connection
from app.core.config import settings
from app.services.data_service import DataService


def sigmoid(x: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-np.clip(x, -15.0, 15.0)))


class BaseForecaster:
    def __init__(self, random_seed: int = 42):
        self.random_seed = random_seed
        self.model = None
        self.feature_names = None
        np.random.seed(random_seed)

    def fit(self, X: pd.DataFrame, y: pd.Series) -> None:
        pass

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        return np.zeros(len(X))

    def get_feature_importance(self) -> Dict[str, float]:
        if not self.feature_names:
            return {}
        n = len(self.feature_names)
        return {feat: round(100.0 / n, 2) for feat in self.feature_names}


class PersistenceForecaster(BaseForecaster):
    def fit(self, X: pd.DataFrame, y: pd.Series) -> None:
        self.feature_names = list(X.columns)
        self.last_value = float(y.iloc[-1]) if len(y) > 0 else 0.0

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        return np.full(len(X), self.last_value)

    def get_feature_importance(self) -> Dict[str, float]:
        if not self.feature_names:
            return {}
        imp = {f: 0.0 for f in self.feature_names}
        if 'lag_1' in imp:
            imp['lag_1'] = 100.0
        else:
            imp[self.feature_names[0]] = 100.0
        return imp


class SeasonalNaiveForecaster(BaseForecaster):
    def __init__(self, seasonal_period: int = 24, random_seed: int = 42):
        super().__init__(random_seed)
        self.seasonal_period = seasonal_period

    def fit(self, X: pd.DataFrame, y: pd.Series) -> None:
        self.feature_names = list(X.columns)
        self.history = y.values

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        if len(self.history) < self.seasonal_period:
            return np.full(len(X), self.history[-1] if len(self.history) > 0 else 0.0)
        return np.tile(self.history[-self.seasonal_period:], (len(X) // self.seasonal_period) + 1)[:len(X)]

    def get_feature_importance(self) -> Dict[str, float]:
        if not self.feature_names:
            return {}
        imp = {f: 0.0 for f in self.feature_names}
        if 'lag_24' in imp:
            imp['lag_24'] = 70.0
        if 'hour' in imp:
            imp['hour'] = 30.0
        return imp


class SklearnForecaster(BaseForecaster):
    def __init__(self, model, random_seed: int = 42):
        super().__init__(random_seed)
        self.model = model

    def fit(self, X: pd.DataFrame, y: pd.Series) -> None:
        self.feature_names = list(X.columns)
        self.model.fit(X, y)

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        if self.feature_names:
            X = X[self.feature_names]
        preds = self.model.predict(X)
        return np.maximum(0.0, preds)

    def get_feature_importance(self) -> Dict[str, float]:
        if not self.feature_names:
            return {}
        if hasattr(self.model, 'feature_importances_'):
            importances = np.array(self.model.feature_importances_)
            total = np.sum(importances)
            norm = (importances / total * 100) if total > 0 else np.ones(len(self.feature_names)) / len(self.feature_names) * 100
            return {name: round(float(norm[i]), 2) for i, name in enumerate(self.feature_names)}
        elif hasattr(self.model, 'coef_'):
            coefs = np.abs(np.array(self.model.coef_)).flatten()
            total = np.sum(coefs)
            norm = (coefs / total * 100) if total > 0 else np.ones(len(self.feature_names)) / len(self.feature_names) * 100
            return {name: round(float(norm[i]), 2) for i, name in enumerate(self.feature_names)}
        return super().get_feature_importance()


class RecurrentForecaster(BaseForecaster):
    """
    Self-contained Recurrent Neural Network (LSTM / GRU) Forecaster implemented in NumPy.
    Runs reliably across all environments without C++ DLL dependencies.
    """
    def __init__(self, model_type: str = 'lstm', hidden_size: int = 16, seq_len: int = 12, epochs: int = 20, lr: float = 0.01, random_seed: int = 42):
        super().__init__(random_seed)
        self.model_type = model_type.lower()
        self.hidden_size = hidden_size
        self.seq_len = seq_len
        self.epochs = epochs
        self.lr = lr
        self.scaler_X = StandardScaler()
        self.scaler_y = StandardScaler()
        self.feature_importance = {}

        # Weights
        self.W = None
        self.U = None
        self.b = None
        self.Wy = None
        self.by = 0.0

    def _init_weights(self, in_dim: int):
        np.random.seed(self.random_seed)
        scale = 0.1
        h = self.hidden_size
        num_gates = 4 if self.model_type == 'lstm' else 3

        self.W = np.random.randn(num_gates * h, in_dim) * scale
        self.U = np.random.randn(num_gates * h, h) * scale
        self.b = np.zeros((num_gates * h, 1))
        if self.model_type == 'lstm':
            self.b[h:2*h] = 1.0  # forget gate bias
        self.Wy = np.random.randn(1, h) * scale
        self.by = 0.0

    def fit(self, X: pd.DataFrame, y: pd.Series) -> None:
        self.feature_names = list(X.columns)
        in_dim = len(self.feature_names)
        self._init_weights(in_dim)

        X_scaled = self.scaler_X.fit_transform(X.values)
        y_scaled = self.scaler_y.fit_transform(y.values.reshape(-1, 1)).flatten()

        n = len(X_scaled)
        effective_seq = min(self.seq_len, max(2, n // 4))

        X_seqs = []
        y_seqs = []
        for i in range(effective_seq, n):
            X_seqs.append(X_scaled[i - effective_seq:i])
            y_seqs.append(y_scaled[i])

        if len(X_seqs) == 0:
            X_seqs = [X_scaled]
            y_seqs = [y_scaled[-1]]

        N = len(X_seqs)
        h_dim = self.hidden_size
        beta1, beta2, eps = 0.9, 0.999, 1e-8
        mW, vW = np.zeros_like(self.W), np.zeros_like(self.W)
        mU, vU = np.zeros_like(self.U), np.zeros_like(self.U)
        mb, vb = np.zeros_like(self.b), np.zeros_like(self.b)
        mWy, vWy = np.zeros_like(self.Wy), np.zeros_like(self.Wy)
        mby, vby = 0.0, 0.0

        for epoch in range(self.epochs):
            indices = np.random.permutation(N)
            batch_indices = indices[:min(N, 64)]
            for idx in batch_indices:
                X_seq = X_seqs[idx]
                target = y_seqs[idx]

                # Forward pass
                if self.model_type == 'lstm':
                    hs = [np.zeros((h_dim, 1))]
                    cs = [np.zeros((h_dim, 1))]
                    gates_cache = []
                    for t in range(len(X_seq)):
                        xt = X_seq[t].reshape(-1, 1)
                        g = np.dot(self.W, xt) + np.dot(self.U, hs[-1]) + self.b
                        i_gate = sigmoid(g[:h_dim])
                        f_gate = sigmoid(g[h_dim:2*h_dim])
                        c_bar = np.tanh(g[2*h_dim:3*h_dim])
                        o_gate = sigmoid(g[3*h_dim:4*h_dim])
                        c_curr = f_gate * cs[-1] + i_gate * c_bar
                        h_curr = o_gate * np.tanh(c_curr)
                        hs.append(h_curr)
                        cs.append(c_curr)
                        gates_cache.append((xt, i_gate, f_gate, c_bar, o_gate))

                    pred = (np.dot(self.Wy, hs[-1]) + self.by)[0, 0]
                    err = pred - target
                    loss_grad = 2.0 * np.clip(err, -5.0, 5.0)

                    dWy = loss_grad * hs[-1].T
                    dby = loss_grad
                    dh = np.dot(self.Wy.T, loss_grad)

                    dW = np.zeros_like(self.W)
                    dU = np.zeros_like(self.U)
                    db = np.zeros_like(self.b)
                    dc_next = np.zeros((h_dim, 1))

                    for t in reversed(range(len(X_seq))):
                        xt, i_g, f_g, c_b, o_g = gates_cache[t]
                        c_p = cs[t]
                        c_c = cs[t+1]
                        tanh_c = np.tanh(c_c)

                        do = dh * tanh_c * o_g * (1 - o_g)
                        dc = dh * o_g * (1 - tanh_c ** 2) + dc_next
                        dc_bar = dc * i_g * (1 - c_b ** 2)
                        di = dc * c_b * i_g * (1 - i_g)
                        df = dc * c_p * f_g * (1 - f_g)

                        dg = np.vstack([di, df, dc_bar, do])
                        dW += np.dot(dg, xt.T)
                        dU += np.dot(dg, hs[t].T)
                        db += dg
                        dh = np.dot(self.U.T, dg)
                        dc_next = dc * f_g
                else:
                    # GRU forward & backward
                    hs = [np.zeros((h_dim, 1))]
                    gru_cache = []
                    for t in range(len(X_seq)):
                        xt = X_seq[t].reshape(-1, 1)
                        g = np.dot(self.W, xt) + np.dot(self.U, hs[-1]) + self.b
                        z_g = sigmoid(g[:h_dim])
                        r_g = sigmoid(g[h_dim:2*h_dim])
                        cand_input = np.dot(self.W[2*h_dim:3*h_dim], xt) + np.dot(self.U[2*h_dim:3*h_dim], r_g * hs[-1]) + self.b[2*h_dim:3*h_dim]
                        h_tilde = np.tanh(cand_input)
                        h_curr = (1 - z_g) * hs[-1] + z_g * h_tilde
                        hs.append(h_curr)
                        gru_cache.append((xt, z_g, r_g, h_tilde))

                    pred = (np.dot(self.Wy, hs[-1]) + self.by)[0, 0]
                    err = pred - target
                    loss_grad = 2.0 * np.clip(err, -5.0, 5.0)

                    dWy = loss_grad * hs[-1].T
                    dby = loss_grad
                    dh = np.dot(self.Wy.T, loss_grad)

                    dW = np.zeros_like(self.W)
                    dU = np.zeros_like(self.U)
                    db = np.zeros_like(self.b)

                    for t in reversed(range(len(X_seq))):
                        xt, z_g, r_g, h_t = gru_cache[t]
                        h_prev = hs[t]
                        dh_tilde = dh * z_g * (1 - h_t ** 2)
                        dz = dh * (h_t - h_prev) * z_g * (1 - z_g)
                        dr = np.dot(self.U[2*h_dim:3*h_dim].T, dh_tilde) * h_prev * r_g * (1 - r_g)
                        dg = np.vstack([dz, dr, dh_tilde])

                        dW += np.dot(dg, xt.T)
                        dU[:2*h_dim] += np.dot(dg[:2*h_dim], h_prev.T)
                        dU[2*h_dim:3*h_dim] += np.dot(dh_tilde, (r_g * h_prev).T)
                        db += dg
                        dh = dh * (1 - z_g) + np.dot(self.U[:2*h_dim].T, dg[:2*h_dim])

                # Adam updates with gradient clipping
                dW = np.clip(dW, -1.0, 1.0)
                dU = np.clip(dU, -1.0, 1.0)
                db = np.clip(db, -1.0, 1.0)
                dWy = np.clip(dWy, -1.0, 1.0)
                dby = np.clip(dby, -1.0, 1.0)

                mW = beta1 * mW + (1 - beta1) * dW
                vW = beta2 * vW + (1 - beta2) * (dW ** 2)
                self.W -= self.lr * mW / (np.sqrt(vW) + eps)

                mU = beta1 * mU + (1 - beta1) * dU
                vU = beta2 * vU + (1 - beta2) * (dU ** 2)
                self.U -= self.lr * mU / (np.sqrt(vU) + eps)

                mb = beta1 * mb + (1 - beta1) * db
                vb = beta2 * vb + (1 - beta2) * (db ** 2)
                self.b -= self.lr * mb / (np.sqrt(vb) + eps)

                mWy = beta1 * mWy + (1 - beta1) * dWy
                vWy = beta2 * vWy + (1 - beta2) * (dWy ** 2)
                self.Wy -= self.lr * mWy / (np.sqrt(vWy) + eps)

                mby = beta1 * mby + (1 - beta1) * dby
                vby = beta2 * vby + (1 - beta2) * (dby ** 2)
                self.by -= self.lr * mby / (np.sqrt(vby) + eps)

        # Feature importance derived from recurrent gate input weight sensitivities
        try:
            gate_sensitivities = np.sum(np.abs(self.W), axis=0)
            total_sens = np.sum(gate_sensitivities)
            if total_sens > 0:
                norm_sens = (gate_sensitivities / total_sens) * 100
            else:
                norm_sens = np.ones(in_dim) / in_dim * 100
            self.feature_importance = {name: round(float(norm_sens[i]), 2) for i, name in enumerate(self.feature_names)}
        except Exception:
            self.feature_importance = {name: round(100.0 / in_dim, 2) for name in self.feature_names}

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        if self.feature_names:
            X = X[self.feature_names]
        X_scaled = self.scaler_X.transform(X.values)
        n = len(X_scaled)
        effective_seq = min(self.seq_len, max(2, n // 4))
        h_dim = self.hidden_size

        preds = []
        for i in range(n):
            if i < effective_seq:
                pad_len = effective_seq - (i + 1)
                seq = np.vstack([np.repeat(X_scaled[0:1], pad_len, axis=0), X_scaled[:i + 1]])
            else:
                seq = X_scaled[i - effective_seq + 1:i + 1]

            if self.model_type == 'lstm':
                h = np.zeros((h_dim, 1))
                c = np.zeros((h_dim, 1))
                for t in range(len(seq)):
                    xt = seq[t].reshape(-1, 1)
                    g = np.dot(self.W, xt) + np.dot(self.U, h) + self.b
                    i_g = sigmoid(g[:h_dim])
                    f_g = sigmoid(g[h_dim:2*h_dim])
                    c_bar = np.tanh(g[2*h_dim:3*h_dim])
                    o_g = sigmoid(g[3*h_dim:4*h_dim])
                    c = f_g * c + i_g * c_bar
                    h = o_g * np.tanh(c)
            else:
                h = np.zeros((h_dim, 1))
                for t in range(len(seq)):
                    xt = seq[t].reshape(-1, 1)
                    g = np.dot(self.W, xt) + np.dot(self.U, h) + self.b
                    z_g = sigmoid(g[:h_dim])
                    r_g = sigmoid(g[h_dim:2*h_dim])
                    cand_input = np.dot(self.W[2*h_dim:3*h_dim], xt) + np.dot(self.U[2*h_dim:3*h_dim], r_g * h) + self.b[2*h_dim:3*h_dim]
                    h_tilde = np.tanh(cand_input)
                    h = (1 - z_g) * h + z_g * h_tilde

            y_hat = (np.dot(self.Wy, h) + self.by)[0, 0]
            preds.append(y_hat)

        preds_arr = np.array(preds).reshape(-1, 1)
        preds_unscaled = self.scaler_y.inverse_transform(preds_arr).flatten()
        return np.maximum(0.0, preds_unscaled)

    def get_feature_importance(self) -> Dict[str, float]:
        if self.feature_importance:
            return self.feature_importance
        return super().get_feature_importance()


MODEL_REGISTRY = {
    'persistence': lambda: PersistenceForecaster(),
    'seasonal_naive': lambda: SeasonalNaiveForecaster(),
    'linear_regression': lambda: SklearnForecaster(LinearRegression()),
    'ridge': lambda: SklearnForecaster(Ridge(alpha=1.0)),
    'lasso': lambda: SklearnForecaster(Lasso(alpha=0.1)),
    'random_forest': lambda: SklearnForecaster(RandomForestRegressor(n_estimators=30, max_depth=6, random_state=42)),
    'gradient_boosting': lambda: SklearnForecaster(GradientBoostingRegressor(n_estimators=30, learning_rate=0.1, max_depth=3, random_state=42)),
    'xgboost': lambda: SklearnForecaster(XGBRegressor(n_estimators=30, learning_rate=0.1, max_depth=3, random_state=42)),
    'lstm': lambda: RecurrentForecaster(model_type='lstm', hidden_size=16, seq_len=12, epochs=20, lr=0.01, random_seed=42),
    'gru': lambda: RecurrentForecaster(model_type='gru', hidden_size=16, seq_len=12, epochs=20, lr=0.01, random_seed=42),
}


class ForecastingService:
    def __init__(self):
        self.models_dir = settings.MODELS_DIR
        self.models_dir.mkdir(parents=True, exist_ok=True)
        self.data_service = DataService()

    def _create_features(self, df: pd.DataFrame, target_col: str = 'consumption_kwh') -> Tuple[pd.DataFrame, pd.Series]:
        df = df.copy()
        required_columns = {'timestamp', target_col}
        missing_columns = required_columns.difference(df.columns)
        if missing_columns:
            raise ValueError(f"Dataset is missing required columns: {', '.join(sorted(missing_columns))}")

        df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
        df[target_col] = pd.to_numeric(df[target_col], errors='coerce')
        df = df.dropna(subset=['timestamp', target_col])
        if df.empty:
            raise ValueError("Dataset has no valid timestamp and consumption rows")

        df = df.sort_values('timestamp')
        df = df.set_index('timestamp')

        target = df[target_col]

        features = pd.DataFrame(index=df.index)
        features['hour'] = df.index.hour
        features['day_of_week'] = df.index.dayofweek
        features['is_weekend'] = (df.index.dayofweek >= 5).astype(int)
        features['month'] = df.index.month

        for lag in [1, 24]:
            if len(df) > lag:
                features[f'lag_{lag}'] = target.shift(lag)

        features['rolling_mean_3'] = target.rolling(3, min_periods=1).mean()
        features['rolling_std_24'] = target.rolling(24, min_periods=1).std().fillna(0)
        features['trend_24'] = target.diff(24).fillna(0)

        features = features.ffill().bfill().fillna(0)
        target = target.loc[features.index]

        return features, target

    def _chronological_split(self, X: pd.DataFrame, y: pd.Series, train_split: float = 0.7, val_split: float = 0.15) -> Tuple:
        n = len(X)
        train_end = int(n * train_split)
        val_end = int(n * (train_split + val_split))

        X_train, y_train = X.iloc[:train_end], y.iloc[:train_end]
        X_val, y_val = X.iloc[train_end:val_end], y.iloc[train_end:val_end]
        X_test, y_test = X.iloc[val_end:], y.iloc[val_end:]

        return (X_train, y_train), (X_val, y_val), (X_test, y_test)

    def _calculate_metrics(self, y_true: np.ndarray, y_pred: np.ndarray) -> Dict[str, float]:
        mae = mean_absolute_error(y_true, y_pred)
        mse = mean_squared_error(y_true, y_pred)
        rmse = np.sqrt(mse)
        r2 = r2_score(y_true, y_pred)

        mape = None
        if np.any(y_true != 0):
            mask = y_true != 0
            mape = np.mean(np.abs((y_true[mask] - y_pred[mask]) / y_true[mask])) * 100

        return {
            'mae': float(mae),
            'mse': float(mse),
            'rmse': float(rmse),
            'r2': float(r2),
            'mape': float(mape) if mape is not None else None,
        }

    def train_model(
        self,
        dataset_id: str,
        model_type: str,
        hyperparameters: Optional[Dict[str, Any]] = None,
        train_split: float = 0.7,
        val_split: float = 0.15
    ) -> Dict[str, Any]:
        if model_type not in MODEL_REGISTRY:
            raise ValueError(f"Unknown model type: {model_type}")

        filepath = self.data_service.data_dir / f"{dataset_id}.csv"
        if not filepath.exists():
            raise FileNotFoundError(f"Dataset {dataset_id} file not found")
        df = pd.read_csv(filepath)

        start_time = time.time()
        X, y = self._create_features(df)
        (X_train, y_train), (X_val, y_val), (X_test, y_test) = self._chronological_split(X, y, train_split, val_split)

        model_factory = MODEL_REGISTRY[model_type]
        forecaster = model_factory()

        forecaster.fit(X_train, y_train)

        val_pred = forecaster.predict(X_val)
        val_metrics = self._calculate_metrics(y_val.values, val_pred)

        test_pred = forecaster.predict(X_test)
        test_metrics = self._calculate_metrics(y_test.values, test_pred)

        duration = round(time.time() - start_time, 2)
        model_id = str(uuid.uuid4())

        # Calculate residual error std for calibrated confidence intervals
        residuals = y_val.values - val_pred
        residual_std = float(np.std(residuals))
        if residual_std <= 1e-4 or np.isnan(residual_std):
            residual_std = max(1.0, float(np.mean(y_val) * 0.08))

        feature_importance = forecaster.get_feature_importance()

        # Save model artifact to disk
        model_filepath = self.models_dir / f"{model_id}.joblib"
        joblib.dump({
            'forecaster': forecaster,
            'feature_names': forecaster.feature_names,
            'residual_std': residual_std,
            'feature_importance': feature_importance,
            'val_metrics': val_metrics,
            'test_metrics': test_metrics,
            'model_type': model_type,
            'dataset_id': dataset_id,
        }, model_filepath)

        feature_importance_json = json.dumps(feature_importance)

        with get_db_connection() as conn:
            conn.execute("""
                INSERT INTO models (id, name, type, dataset_id, status, filepath, hyperparameters,
                                    train_split, val_split, train_range_start, train_range_end,
                                    val_range_start, val_range_end, test_range_start, test_range_end,
                                    training_duration, feature_importance)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                model_id,
                f"{model_type}_{model_id[:8]}",
                model_type,
                dataset_id,
                "ready",
                str(model_filepath),
                json.dumps(hyperparameters or {}),
                train_split,
                val_split,
                X_train.index[0].isoformat() if len(X_train) > 0 else None,
                X_train.index[-1].isoformat() if len(X_train) > 0 else None,
                X_val.index[0].isoformat() if len(X_val) > 0 else None,
                X_val.index[-1].isoformat() if len(X_val) > 0 else None,
                X_test.index[0].isoformat() if len(X_test) > 0 else None,
                X_test.index[-1].isoformat() if len(X_test) > 0 else None,
                duration,
                feature_importance_json
            ))

            conn.execute("""
                INSERT INTO model_metrics (model_id, mae, mse, rmse, r2, mape, split)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (model_id, val_metrics.get('mae'), val_metrics.get('mse'),
                  val_metrics.get('rmse'), val_metrics.get('r2'), val_metrics.get('mape'), 'validation'))

            conn.execute("""
                INSERT INTO model_metrics (model_id, mae, mse, rmse, r2, mape, split)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (model_id, test_metrics.get('mae'), test_metrics.get('mse'),
                  test_metrics.get('rmse'), test_metrics.get('r2'), test_metrics.get('mape'), 'test'))

            conn.execute("""
                INSERT INTO experiments (id, name, dataset_id, model_type, hyperparameters,
                                         train_range_start, train_range_end, val_range_start, val_range_end,
                                         test_range_start, test_range_end, training_duration, feature_importance)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                model_id,
                f"Experiment_{model_type}_{model_id[:8]}",
                dataset_id,
                model_type,
                json.dumps(hyperparameters or {}),
                X_train.index[0].isoformat() if len(X_train) > 0 else None,
                X_train.index[-1].isoformat() if len(X_train) > 0 else None,
                X_val.index[0].isoformat() if len(X_val) > 0 else None,
                X_val.index[-1].isoformat() if len(X_val) > 0 else None,
                X_test.index[0].isoformat() if len(X_test) > 0 else None,
                X_test.index[-1].isoformat() if len(X_test) > 0 else None,
                duration,
                feature_importance_json
            ))

            conn.execute("""
                INSERT INTO experiment_metrics (experiment_id, mae, mse, rmse, r2, mape, split)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (model_id, val_metrics.get('mae'), val_metrics.get('mse'),
                  val_metrics.get('rmse'), val_metrics.get('r2'), val_metrics.get('mape'), 'validation'))

            conn.execute("""
                INSERT INTO experiment_metrics (experiment_id, mae, mse, rmse, r2, mape, split)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (model_id, test_metrics.get('mae'), test_metrics.get('mse'),
                  test_metrics.get('rmse'), test_metrics.get('r2'), test_metrics.get('mape'), 'test'))

            conn.commit()

        return {
            'id': model_id,
            'model_id': model_id,
            'name': f"{model_type}_{model_id[:8]}",
            'type': model_type,
            'dataset_id': dataset_id,
            'status': 'ready',
            'metrics': val_metrics,
            'test_metrics': test_metrics,
            'feature_importance': feature_importance,
            'training_duration': duration,
            'filepath': str(model_filepath),
            'created_at': datetime.now().isoformat(),
        }

    def get_model(self, model_id: str) -> Optional[Dict[str, Any]]:
        with get_db_connection() as conn:
            cursor = conn.execute("SELECT * FROM models WHERE id = ?", (model_id,))
            row = cursor.fetchone()
            if not row:
                return None

            cursor = conn.execute("SELECT * FROM model_metrics WHERE model_id = ? AND split = 'validation'", (model_id,))
            metrics_row = cursor.fetchone()

            cursor = conn.execute("SELECT * FROM model_metrics WHERE model_id = ? AND split = 'test'", (model_id,))
            test_metrics_row = cursor.fetchone()

        feature_importance = {}
        if 'feature_importance' in row.keys() and row['feature_importance']:
            try:
                feature_importance = json.loads(row['feature_importance'])
            except Exception:
                pass

        return {
            'id': row['id'],
            'name': row['name'],
            'type': row['type'],
            'dataset_id': row['dataset_id'],
            'status': row['status'],
            'filepath': row['filepath'],
            'metrics': {
                'mae': metrics_row['mae'],
                'mse': metrics_row['mse'],
                'rmse': metrics_row['rmse'],
                'r2': metrics_row['r2'],
                'mape': metrics_row['mape'],
            } if metrics_row else None,
            'test_metrics': {
                'mae': test_metrics_row['mae'],
                'mse': test_metrics_row['mse'],
                'rmse': test_metrics_row['rmse'],
                'r2': test_metrics_row['r2'],
                'mape': test_metrics_row['mape'],
            } if test_metrics_row else None,
            'feature_importance': feature_importance,
            'training_duration': row['training_duration'],
            'created_at': row['created_at'],
        }

    def get_model_metrics(self, model_id: str) -> Optional[Dict[str, Any]]:
        model = self.get_model(model_id)
        if not model:
            return None
        return {
            'metrics': model['metrics'],
            'test_metrics': model['test_metrics'],
            'feature_importance': model['feature_importance'],
            'mae': model['metrics']['mae'] if model['metrics'] else 0.0,
            'mse': model['metrics']['mse'] if model['metrics'] else 0.0,
            'rmse': model['metrics']['rmse'] if model['metrics'] else 0.0,
            'r2': model['metrics']['r2'] if model['metrics'] else 0.0,
            'mape': model['metrics']['mape'] if model['metrics'] else 0.0,
        }

    def list_models(self) -> List[Dict[str, Any]]:
        with get_db_connection() as conn:
            cursor = conn.execute("SELECT * FROM models ORDER BY created_at DESC")
            rows = cursor.fetchall()

        models = []
        for row in rows:
            with get_db_connection() as conn:
                m_cur = conn.execute("SELECT * FROM model_metrics WHERE model_id = ? AND split = 'validation'", (row['id'],))
                m_row = m_cur.fetchone()

            feature_importance = {}
            if 'feature_importance' in row.keys() and row['feature_importance']:
                try:
                    feature_importance = json.loads(row['feature_importance'])
                except Exception:
                    pass

            models.append({
                'id': row['id'],
                'name': row['name'],
                'type': row['type'],
                'dataset_id': row['dataset_id'],
                'status': row['status'],
                'filepath': row['filepath'],
                'training_duration': row['training_duration'],
                'created_at': row['created_at'],
                'feature_importance': feature_importance,
                'metrics': {
                    'mae': m_row['mae'],
                    'mse': m_row['mse'],
                    'rmse': m_row['rmse'],
                    'r2': m_row['r2'],
                    'mape': m_row['mape'],
                } if m_row else None
            })
        return models

    def delete_model(self, model_id: str) -> bool:
        with get_db_connection() as conn:
            cursor = conn.execute("SELECT filepath FROM models WHERE id = ?", (model_id,))
            row = cursor.fetchone()
            if not row:
                return False

            if row['filepath']:
                p = Path(row['filepath'])
                if p.exists():
                    p.unlink(missing_ok=True)

            conn.execute("DELETE FROM model_metrics WHERE model_id = ?", (model_id,))
            conn.execute("DELETE FROM experiment_metrics WHERE experiment_id = ?", (model_id,))
            conn.execute("DELETE FROM experiments WHERE id = ?", (model_id,))
            conn.execute("DELETE FROM models WHERE id = ?", (model_id,))
            conn.commit()
            return True

    def generate_forecast(self, model_id: str, horizon_hours: int = 24) -> Dict[str, Any]:
        model = self.get_model(model_id)
        if not model:
            raise ValueError(f"Model {model_id} not found")

        dataset_id = model['dataset_id']
        filepath = self.data_service.data_dir / f"{dataset_id}.csv"
        if not filepath.exists():
            raise FileNotFoundError(f"Dataset file {filepath} not found")
        df = pd.read_csv(filepath)

        # Load persisted model from disk
        model_file = Path(model['filepath']) if model.get('filepath') else (self.models_dir / f"{model_id}.joblib")
        forecaster = None
        residual_std = 5.0

        if model_file.exists():
            saved_bundle = joblib.load(model_file)
            forecaster = saved_bundle.get('forecaster')
            residual_std = saved_bundle.get('residual_std', 5.0)

        if forecaster is None:
            forecaster = MODEL_REGISTRY[model['type']]()
            X, y = self._create_features(df)
            forecaster.fit(X, y)

        X, y = self._create_features(df)
        last_timestamp = pd.to_datetime(df['timestamp'].max())
        future_timestamps = pd.date_range(start=last_timestamp + timedelta(hours=1), periods=horizon_hours, freq='H')

        future_features = pd.DataFrame(index=future_timestamps)
        future_features['hour'] = future_timestamps.hour
        future_features['day_of_week'] = future_timestamps.dayofweek
        future_features['is_weekend'] = (future_timestamps.dayofweek >= 5).astype(int)
        future_features['month'] = future_timestamps.month

        for lag in [1, 24]:
            if len(y) > lag:
                future_features[f'lag_{lag}'] = y.iloc[-lag]
            else:
                future_features[f'lag_{lag}'] = y.iloc[-1] if len(y) > 0 else 0

        future_features['rolling_mean_3'] = y.tail(3).mean() if len(y) >= 3 else (y.iloc[-1] if len(y) > 0 else 0)
        future_features['rolling_std_24'] = y.tail(24).std() if len(y) >= 24 else 0
        future_features['trend_24'] = (y.iloc[-1] - y.iloc[-25]) if len(y) >= 25 else 0

        if hasattr(forecaster, 'feature_names') and forecaster.feature_names:
            for feat in forecaster.feature_names:
                if feat not in future_features.columns:
                    future_features[feat] = 0
            future_features = future_features[forecaster.feature_names]

        predictions = forecaster.predict(future_features)

        forecast_id = str(uuid.uuid4())
        prediction_list = []
        for h, (ts, pred) in enumerate(zip(future_timestamps, predictions)):
            pred_val = float(max(0.0, pred))
            uncertainty_scale = np.sqrt(1.0 + 0.05 * h)
            margin = 1.96 * residual_std * uncertainty_scale
            lower_b = float(max(0.0, pred_val - margin))
            upper_b = float(pred_val + margin)
            prediction_list.append({
                'timestamp': ts.isoformat(),
                'predicted_consumption': round(pred_val, 2),
                'lower_bound': round(lower_b, 2),
                'upper_bound': round(upper_b, 2),
            })

        predicted_vals = [p['predicted_consumption'] for p in prediction_list]
        summary = {
            'total_predicted': round(float(np.sum(predicted_vals)), 2),
            'peak_predicted': round(float(np.max(predicted_vals)), 2) if predicted_vals else 0.0,
            'avg_predicted': round(float(np.mean(predicted_vals)), 2) if predicted_vals else 0.0,
        }

        forecast_data = {
            'forecast_id': forecast_id,
            'model_id': model_id,
            'horizon_hours': horizon_hours,
            'predictions': prediction_list,
            'summary': summary,
            'generated_at': datetime.now().isoformat(),
        }

        with get_db_connection() as conn:
            conn.execute("""
                INSERT INTO forecasts (id, model_id, horizon_hours, predictions, summary)
                VALUES (?, ?, ?, ?, ?)
            """, (forecast_id, model_id, horizon_hours,
                  json.dumps(forecast_data['predictions']), json.dumps(forecast_data['summary'])))
            conn.commit()

        return forecast_data

    def list_forecasts(self) -> List[Dict[str, Any]]:
        with get_db_connection() as conn:
            cursor = conn.execute("SELECT * FROM forecasts ORDER BY created_at DESC")
            rows = cursor.fetchall()

        forecasts = []
        for row in rows:
            predictions = []
            summary = {}
            try:
                predictions = json.loads(row['predictions'])
                summary = json.loads(row['summary'])
            except Exception:
                pass
            forecasts.append({
                'forecast_id': row['id'],
                'model_id': row['model_id'],
                'horizon_hours': row['horizon_hours'],
                'predictions': predictions,
                'summary': summary,
                'created_at': row['created_at'],
            })
        return forecasts

    def get_forecast(self, forecast_id: str) -> Optional[Dict[str, Any]]:
        with get_db_connection() as conn:
            cursor = conn.execute("SELECT * FROM forecasts WHERE id = ?", (forecast_id,))
            row = cursor.fetchone()
            if not row:
                return None

        predictions = []
        summary = {}
        try:
            predictions = json.loads(row['predictions'])
            summary = json.loads(row['summary'])
        except Exception:
            pass

        return {
            'forecast_id': row['id'],
            'model_id': row['model_id'],
            'horizon_hours': row['horizon_hours'],
            'predictions': predictions,
            'summary': summary,
            'created_at': row['created_at'],
        }