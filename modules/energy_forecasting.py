"""
VoltSense 5G - Module 3: Energy Consumption Prediction & Analytics Engine
Implements Linear Regression, Random Forest Regressor, and ARIMA time-series models with chronological evaluation.
"""
import warnings
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple

from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from statsmodels.tsa.arima.model import ARIMA

from database.database import DatabaseManager
from config import DEFAULT_TARIFF_INR_PER_KWH

# Suppress convergence warnings from ARIMA during automated grid sweeps
warnings.filterwarnings("ignore")


class EnergyForecastingEngine:
    """
    Predicts future energy consumption using multiple supervised and time-series ML algorithms.
    Strictly uses chronological train/test splits to avoid future-data leakage.
    """
    def __init__(self, db: DatabaseManager):
        self.db = db

    def prepare_feature_dataset(
        self, 
        device_id: Optional[str] = None, 
        building: Optional[str] = None
    ) -> pd.DataFrame:
        """
        Extracts hourly aggregated consumption series with calendar and lag features.
        """
        df = self.db.get_readings(device_id=device_id, building=building, order="ASC")
        if df.empty or len(df) < 48:
            return pd.DataFrame()

        if not pd.api.types.is_datetime64_any_dtype(df["timestamp"]):
            df["timestamp"] = pd.to_datetime(df["timestamp"])

        # Aggregate to hourly intervals
        df = df.set_index("timestamp")
        hourly_series = df.resample("1h").agg({
            "energy_kwh": "max",
            "active_power": "mean"
        }).ffill()

        # Incremental hourly kWh
        hourly_series["hourly_kwh"] = hourly_series["energy_kwh"].diff().fillna(
            hourly_series["active_power"] / 1000.0
        ).clip(lower=0.0)

        data = hourly_series.reset_index()

        # Calendar features
        data["hour"] = data["timestamp"].dt.hour
        data["dayofweek"] = data["timestamp"].dt.dayofweek
        data["is_weekend"] = (data["dayofweek"] >= 5).astype(int)
        data["month"] = data["timestamp"].dt.month

        # Cyclic hour features (sin/cos encoding of 24h cycle)
        data["hour_sin"] = np.sin(2 * np.pi * data["hour"] / 24.0)
        data["hour_cos"] = np.cos(2 * np.pi * data["hour"] / 24.0)

        # Lag features
        data["lag_1h"] = data["hourly_kwh"].shift(1)
        data["lag_24h"] = data["hourly_kwh"].shift(24)
        data["lag_168h"] = data["hourly_kwh"].shift(168).fillna(data["lag_24h"])

        # Rolling statistics
        data["rolling_mean_6h"] = data["hourly_kwh"].shift(1).rolling(window=6, min_periods=1).mean()
        data["rolling_mean_24h"] = data["hourly_kwh"].shift(1).rolling(window=24, min_periods=1).mean()

        # Drop initial rows with NaNs from lag shifting
        data = data.dropna().reset_index(drop=True)
        return data

    def evaluate_and_compare_models(
        self, 
        device_id: Optional[str] = None, 
        building: Optional[str] = None,
        test_ratio: float = 0.20
    ) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """
        Trains and chronologically tests Linear Regression, Random Forest, and ARIMA.
        Returns model comparison table and best model artifact.
        """
        data = self.prepare_feature_dataset(device_id=device_id, building=building)
        if data.empty or len(data) < 72:
            return pd.DataFrame(), {
                "error": "Insufficient historical data for model evaluation. Minimum 72 hourly records required."
            }

        split_idx = int(len(data) * (1.0 - test_ratio))
        train_df = data.iloc[:split_idx]
        test_df = data.iloc[split_idx:]

        feature_cols = [
            "hour", "dayofweek", "is_weekend", "month",
            "hour_sin", "hour_cos", "lag_1h", "lag_24h",
            "rolling_mean_6h", "rolling_mean_24h"
        ]
        target_col = "hourly_kwh"

        X_train, y_train = train_df[feature_cols], train_df[target_col]
        X_test, y_test = test_df[feature_cols], test_df[target_col]

        results = []

        # 1. Linear Regression
        lr = LinearRegression()
        lr.fit(X_train, y_train)
        y_pred_lr = np.clip(lr.predict(X_test), 0.0, None)
        mae_lr = mean_absolute_error(y_test, y_pred_lr)
        rmse_lr = np.sqrt(mean_squared_error(y_test, y_pred_lr))
        r2_lr = r2_score(y_test, y_pred_lr)
        results.append({
            "model": "Linear Regression",
            "mae": round(float(mae_lr), 3),
            "rmse": round(float(rmse_lr), 3),
            "r2": round(float(r2_lr), 3),
            "trained_model": lr,
            "predictions": y_pred_lr
        })

        # 2. Random Forest Regressor
        rf = RandomForestRegressor(n_estimators=100, max_depth=12, random_state=42, n_jobs=-1)
        rf.fit(X_train, y_train)
        y_pred_rf = np.clip(rf.predict(X_test), 0.0, None)
        mae_rf = mean_absolute_error(y_test, y_pred_rf)
        rmse_rf = np.sqrt(mean_squared_error(y_test, y_pred_rf))
        r2_rf = r2_score(y_test, y_pred_rf)
        results.append({
            "model": "Random Forest Regressor",
            "mae": round(float(mae_rf), 3),
            "rmse": round(float(rmse_rf), 3),
            "r2": round(float(r2_rf), 3),
            "trained_model": rf,
            "predictions": y_pred_rf
        })

        # 3. ARIMA (AutoRegressive Integrated Moving Average)
        try:
            # Fit ARIMA (1, 1, 1) on chronological train series
            arima_model = ARIMA(train_df[target_col], order=(1, 1, 1))
            arima_fit = arima_model.fit()
            y_pred_arima = np.clip(arima_fit.forecast(steps=len(test_df)), 0.0, None).values
            mae_arima = mean_absolute_error(y_test, y_pred_arima)
            rmse_arima = np.sqrt(mean_squared_error(y_test, y_pred_arima))
            r2_arima = r2_score(y_test, y_pred_arima)
        except Exception:
            # Fallback if non-convergent
            y_pred_arima = np.repeat(train_df[target_col].mean(), len(test_df))
            mae_arima = mean_absolute_error(y_test, y_pred_arima)
            rmse_arima = np.sqrt(mean_squared_error(y_test, y_pred_arima))
            r2_arima = 0.0

        results.append({
            "model": "ARIMA Time Series",
            "mae": round(float(mae_arima), 3),
            "rmse": round(float(rmse_arima), 3),
            "r2": round(float(r2_arima), 3),
            "trained_model": "ARIMA(1,1,1)",
            "predictions": y_pred_arima
        })

        # Formulate benchmark DataFrame
        eval_df = pd.DataFrame(results)[["model", "mae", "rmse", "r2"]]

        # Find best model (highest R2 or lowest RMSE)
        best_model_idx = eval_df["r2"].idxmax()
        best_model_name = eval_df.loc[best_model_idx, "model"]

        benchmark_summary = {
            "eval_df": eval_df,
            "best_model_name": best_model_name,
            "test_actuals": y_test.values,
            "test_timestamps": test_df["timestamp"].values,
            "trained_models": {r["model"]: r["trained_model"] for r in results},
            "train_size": len(train_df),
            "test_size": len(test_df)
        }

        return eval_df, benchmark_summary

    def generate_future_forecast(
        self,
        horizon_hours: int = 24,
        model_name: str = "Random Forest Regressor",
        device_id: Optional[str] = None,
        building: Optional[str] = None,
        tariff_rate: float = DEFAULT_TARIFF_INR_PER_KWH
    ) -> Dict[str, Any]:
        """
        Forecasts future electricity consumption over configurable horizons (24h, 168h/7d, 720h/30d).
        Computes prediction intervals and projected financial bills.
        """
        data = self.prepare_feature_dataset(device_id=device_id, building=building)
        if data.empty or len(data) < 72:
            return {"error": "Insufficient telemetry records for predictive modeling."}

        # Train full model on all available data
        feature_cols = [
            "hour", "dayofweek", "is_weekend", "month",
            "hour_sin", "hour_cos", "lag_1h", "lag_24h",
            "rolling_mean_6h", "rolling_mean_24h"
        ]
        target_col = "hourly_kwh"

        X_full = data[feature_cols]
        y_full = data[target_col]

        last_timestamp = data["timestamp"].max()
        future_timestamps = [last_timestamp + timedelta(hours=i + 1) for i in range(horizon_hours)]

        predicted_values = []
        lower_bounds = []
        upper_bounds = []

        if model_name == "ARIMA Time Series":
            try:
                arima = ARIMA(y_full, order=(1, 1, 1)).fit()
                forecast_res = arima.get_forecast(steps=horizon_hours)
                predicted_values = np.clip(forecast_res.predicted_mean.values, 0.0, None)
                conf_int = forecast_res.conf_int(alpha=0.05)
                lower_bounds = np.clip(conf_int.iloc[:, 0].values, 0.0, None)
                upper_bounds = np.clip(conf_int.iloc[:, 1].values, 0.0, None)
            except Exception:
                # Fallback to rolling average
                mean_val = y_full.tail(24).mean()
                predicted_values = np.repeat(mean_val, horizon_hours)
                lower_bounds = predicted_values * 0.85
                upper_bounds = predicted_values * 1.15
        else:
            if model_name == "Linear Regression":
                model = LinearRegression().fit(X_full, y_full)
            else:
                model = RandomForestRegressor(n_estimators=100, max_depth=12, random_state=42, n_jobs=-1).fit(X_full, y_full)

            # Iterative multi-step recursive forecasting
            current_history = list(y_full.values)
            for dt in future_timestamps:
                h = dt.hour
                dow = dt.dayofweek
                is_wk = 1 if dow >= 5 else 0
                mo = dt.month
                h_sin = np.sin(2 * np.pi * h / 24.0)
                h_cos = np.cos(2 * np.pi * h / 24.0)

                l1 = current_history[-1]
                l24 = current_history[-24] if len(current_history) >= 24 else l1
                rm6 = np.mean(current_history[-6:])
                rm24 = np.mean(current_history[-24:])

                feat_vector = pd.DataFrame([{
                    "hour": h, "dayofweek": dow, "is_weekend": is_wk, "month": mo,
                    "hour_sin": h_sin, "hour_cos": h_cos,
                    "lag_1h": l1, "lag_24h": l24,
                    "rolling_mean_6h": rm6, "rolling_mean_24h": rm24
                }])

                pred = float(np.clip(model.predict(feat_vector)[0], 0.0, None))
                predicted_values.append(pred)
                current_history.append(pred)

                # Estimated uncertainty bounds (+/- 12% for RF / LR)
                lower_bounds.append(round(pred * 0.88, 3))
                upper_bounds.append(round(pred * 1.12, 3))

        forecast_df = pd.DataFrame({
            "target_date": future_timestamps,
            "predicted_energy_kwh": np.round(predicted_values, 3),
            "lower_bound_kwh": np.round(lower_bounds, 3),
            "upper_bound_kwh": np.round(upper_bounds, 3)
        })

        total_predicted_kwh = float(forecast_df["predicted_energy_kwh"].sum())
        projected_cost_inr = round(total_predicted_kwh * tariff_rate, 2)
        peak_predicted_kwh = float(forecast_df["predicted_energy_kwh"].max())
        peak_timestamp = str(forecast_df.loc[forecast_df["predicted_energy_kwh"].idxmax(), "target_date"])

        # Persist predictions to database
        db_records = []
        for _, r in forecast_df.iterrows():
            db_records.append({
                "model_name": model_name,
                "horizon": f"{horizon_hours}h",
                "target_date": str(r["target_date"]),
                "predicted_energy_kwh": r["predicted_energy_kwh"],
                "lower_bound_kwh": r["lower_bound_kwh"],
                "upper_bound_kwh": r["upper_bound_kwh"],
                "actual_energy_kwh": None,
                "mae": None,
                "rmse": None,
                "r2_score": None
            })
        self.db.save_predictions(db_records)

        return {
            "model_name": model_name,
            "horizon_hours": horizon_hours,
            "forecast_df": forecast_df,
            "total_predicted_kwh": round(total_predicted_kwh, 2),
            "projected_cost_inr": projected_cost_inr,
            "peak_predicted_kwh": round(peak_predicted_kwh, 2),
            "peak_timestamp": peak_timestamp,
            "historical_df": data[["timestamp", "hourly_kwh"]].rename(columns={"hourly_kwh": "energy_kwh"}).tail(168)
        }
