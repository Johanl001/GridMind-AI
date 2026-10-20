import pandas as pd
import pytest

from app.services.forecasting_service import ForecastingService


def test_create_features_parses_csv_timestamp_strings():
    timestamps = pd.date_range("2025-01-01", periods=72, freq="h")
    frame = pd.DataFrame({
        "timestamp": timestamps.strftime("%Y-%m-%d %H:%M:%S"),
        "consumption_kwh": range(10, 82),
    })

    features, target = ForecastingService()._create_features(frame)

    assert features.index.equals(pd.DatetimeIndex(timestamps))
    assert features["hour"].tolist() == timestamps.hour.tolist()
    assert len(target) == len(frame)


def test_create_features_reports_invalid_rows_and_missing_columns():
    service = ForecastingService()

    with pytest.raises(ValueError, match="no valid timestamp and consumption rows"):
        service._create_features(pd.DataFrame({
            "timestamp": ["not-a-date"],
            "consumption_kwh": ["not-a-number"],
        }))

    with pytest.raises(ValueError, match="missing required columns"):
        service._create_features(pd.DataFrame({"timestamp": ["2025-01-01"]}))
