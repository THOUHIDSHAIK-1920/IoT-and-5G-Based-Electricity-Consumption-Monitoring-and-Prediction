"""
VoltSense 5G - Unit Tests for Machine Learning Forecasting Engine
"""
import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from database.database import DatabaseManager
from modules.energy_forecasting import EnergyForecastingEngine


@pytest.fixture
def forecast_test_env(tmp_path):
    """Sets up a database with 120 hours of realistic telemetry."""
    db_file = tmp_path / "test_forecast.db"
    db = DatabaseManager(db_file)

    base_time = datetime(2026, 3, 1, 0, 0, 0)
    readings = []
    energy_kwh = 1000.0

    for h in range(120):
        t = base_time + timedelta(hours=h)
        hour_of_day = t.hour
        # Diurnal usage pattern
        diurnal = 0.3 + 0.7 * np.sin((hour_of_day / 24.0) * np.pi)
        power_w = 4000.0 * diurnal + np.random.normal(0, 50)
        energy_kwh += (power_w / 1000.0)

        readings.append({
            "device_id": "DEV_BLD_B_01",
            "timestamp": t.strftime("%Y-%m-%d %H:%M:%S"),
            "voltage": 230.0,
            "current": round(power_w / (230.0 * 0.92), 2),
            "active_power": round(power_w, 1),
            "apparent_power": round(power_w / 0.92, 1),
            "energy_kwh": round(energy_kwh, 3),
            "frequency": 50.0,
            "power_factor": 0.92,
            "is_simulated": 1,
            "transmission_protocol": "5G_URLLC",
            "latency_ms": 2.5,
            "packet_loss": 0
        })

    db.insert_readings_bulk(readings)
    forecaster = EnergyForecastingEngine(db)
    return db, forecaster


def test_feature_dataset_preparation(forecast_test_env):
    db, forecaster = forecast_test_env
    feat_df = forecaster.prepare_feature_dataset(device_id="DEV_BLD_B_01")
    assert not feat_df.empty
    assert "hourly_kwh" in feat_df.columns
    assert "hour" in feat_df.columns
    assert "lag_1h" in feat_df.columns
    assert "rolling_mean_6h" in feat_df.columns


def test_chronological_model_benchmarking(forecast_test_env):
    db, forecaster = forecast_test_env
    eval_df, b_summary = forecaster.evaluate_and_compare_models(device_id="DEV_BLD_B_01")
    
    assert not eval_df.empty
    assert len(eval_df) == 3  # Linear Regression, Random Forest, ARIMA
    assert "mae" in eval_df.columns
    assert "rmse" in eval_df.columns
    assert "r2" in eval_df.columns

    # Verify best model is tagged
    assert b_summary["best_model_name"] in ["Random Forest Regressor", "Linear Regression", "ARIMA Time Series"]


def test_future_forecast_generation(forecast_test_env):
    db, forecaster = forecast_test_env
    forecast_res = forecaster.generate_future_forecast(
        horizon_hours=24,
        model_name="Random Forest Regressor",
        device_id="DEV_BLD_B_01"
    )
    assert "error" not in forecast_res
    assert len(forecast_res["forecast_df"]) == 24
    assert forecast_res["total_predicted_kwh"] > 0
    assert forecast_res["projected_cost_inr"] > 0
    assert "lower_bound_kwh" in forecast_res["forecast_df"].columns
    assert "upper_bound_kwh" in forecast_res["forecast_df"].columns


def test_insufficient_data_handling(tmp_path):
    empty_db = DatabaseManager(tmp_path / "empty.db")
    forecaster = EnergyForecastingEngine(empty_db)
    res = forecaster.generate_future_forecast(horizon_hours=24)
    assert "error" in res
