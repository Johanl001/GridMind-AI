import io
import csv
import json
from fastapi import APIRouter, HTTPException, Query, Response
from typing import List, Optional

from app.persistence.database import get_db_connection
from app.services.forecasting_service import ForecastingService

router = APIRouter()
forecasting_service = ForecastingService()


def _format_experiment_row(row, conn) -> dict:
    exp_id = row['id']

    # Fetch validation metrics
    val_cur = conn.execute("SELECT * FROM experiment_metrics WHERE experiment_id = ? AND split = 'validation'", (exp_id,))
    val_row = val_cur.fetchone()
    if not val_row:
        val_cur = conn.execute("SELECT * FROM model_metrics WHERE model_id = ? AND split = 'validation'", (exp_id,))
        val_row = val_cur.fetchone()

    # Fetch test metrics
    test_cur = conn.execute("SELECT * FROM experiment_metrics WHERE experiment_id = ? AND split = 'test'", (exp_id,))
    test_row = test_cur.fetchone()
    if not test_row:
        test_cur = conn.execute("SELECT * FROM model_metrics WHERE model_id = ? AND split = 'test'", (exp_id,))
        test_row = test_cur.fetchone()

    hyperparams = {}
    if 'hyperparameters' in row.keys() and row['hyperparameters']:
        try:
            hyperparams = json.loads(row['hyperparameters'])
        except Exception:
            hyperparams = {}

    val_metrics = {
        'mae': float(val_row['mae']) if val_row and val_row['mae'] is not None else 0.0,
        'mse': float(val_row['mse']) if val_row and val_row['mse'] is not None else 0.0,
        'rmse': float(val_row['rmse']) if val_row and val_row['rmse'] is not None else 0.0,
        'r2': float(val_row['r2']) if val_row and val_row['r2'] is not None else 0.0,
        'mape': float(val_row['mape']) if val_row and val_row['mape'] is not None else 0.0,
    }

    test_metrics = {
        'mae': float(test_row['mae']) if test_row and test_row['mae'] is not None else 0.0,
        'mse': float(test_row['mse']) if test_row and test_row['mse'] is not None else 0.0,
        'rmse': float(test_row['rmse']) if test_row and test_row['rmse'] is not None else 0.0,
        'r2': float(test_row['r2']) if test_row and test_row['r2'] is not None else 0.0,
        'mape': float(test_row['mape']) if test_row and test_row['mape'] is not None else 0.0,
    } if test_row else None

    feature_importance = {}
    if 'feature_importance' in row.keys() and row['feature_importance']:
        try:
            feature_importance = json.loads(row['feature_importance'])
        except Exception:
            pass

    return {
        'id': row['id'],
        'name': row['name'],
        'dataset_id': row['dataset_id'],
        'model_type': row['model_type'] if 'model_type' in row.keys() else row['type'],
        'hyperparameters': hyperparams,
        'train_range': {
            'start': row['train_range_start'] or '',
            'end': row['train_range_end'] or '',
        },
        'val_range': {
            'start': row['val_range_start'] or '',
            'end': row['val_range_end'] or '',
        },
        'test_range': {
            'start': row['test_range_start'] or '',
            'end': row['test_range_end'] or '',
        },
        'val_metrics': val_metrics,
        'test_metrics': test_metrics,
        'feature_importance': feature_importance,
        'training_duration': float(row['training_duration'] or 0.0),
        'created_at': row['created_at'],
    }


@router.get("/", response_model=List[dict])
async def list_experiments():
    """List all experiments with comprehensive metrics"""
    try:
        with get_db_connection() as conn:
            cursor = conn.execute("SELECT * FROM experiments ORDER BY created_at DESC")
            rows = cursor.fetchall()
            if not rows:
                cursor = conn.execute("SELECT * FROM models ORDER BY created_at DESC")
                rows = cursor.fetchall()

            experiments = [_format_experiment_row(r, conn) for r in rows]
        return experiments
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/export")
async def export_experiments(format: str = Query("json", regex="^(json|csv)$")):
    """Export all experiments in JSON or CSV format"""
    try:
        with get_db_connection() as conn:
            cursor = conn.execute("SELECT * FROM experiments ORDER BY created_at DESC")
            rows = cursor.fetchall()
            if not rows:
                cursor = conn.execute("SELECT * FROM models ORDER BY created_at DESC")
                rows = cursor.fetchall()
            experiments = [_format_experiment_row(r, conn) for r in rows]

        if format == "csv":
            output = io.StringIO()
            fieldnames = [
                "id", "name", "dataset_id", "model_type", "val_mae", "val_rmse",
                "val_r2", "val_mape", "test_mae", "test_rmse", "test_r2",
                "training_duration_sec", "created_at"
            ]
            writer = csv.DictWriter(output, fieldnames=fieldnames)
            writer.writeheader()
            for exp in experiments:
                val_m = exp.get("val_metrics", {})
                test_m = exp.get("test_metrics", {}) or {}
                writer.writerow({
                    "id": exp["id"],
                    "name": exp["name"],
                    "dataset_id": exp["dataset_id"],
                    "model_type": exp["model_type"],
                    "val_mae": val_m.get("mae", ""),
                    "val_rmse": val_m.get("rmse", ""),
                    "val_r2": val_m.get("r2", ""),
                    "val_mape": val_m.get("mape", ""),
                    "test_mae": test_m.get("mae", ""),
                    "test_rmse": test_m.get("rmse", ""),
                    "test_r2": test_m.get("r2", ""),
                    "training_duration_sec": exp["training_duration"],
                    "created_at": exp["created_at"],
                })
            return Response(
                content=output.getvalue(),
                media_type="text/csv",
                headers={"Content-Disposition": "attachment; filename=gridmind_experiments.csv"}
            )
        else:
            return Response(
                content=json.dumps(experiments, indent=2),
                media_type="application/json",
                headers={"Content-Disposition": "attachment; filename=gridmind_experiments.json"}
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{experiment_id}", response_model=dict)
async def get_experiment(experiment_id: str):
    """Get details of a specific experiment"""
    try:
        with get_db_connection() as conn:
            cursor = conn.execute("SELECT * FROM experiments WHERE id = ?", (experiment_id,))
            row = cursor.fetchone()
            if not row:
                cursor = conn.execute("SELECT * FROM models WHERE id = ?", (experiment_id,))
                row = cursor.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Experiment not found")
            return _format_experiment_row(row, conn)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))