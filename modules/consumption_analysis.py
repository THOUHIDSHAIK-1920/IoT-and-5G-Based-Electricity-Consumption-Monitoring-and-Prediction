"""
VoltSense 5G - Module 2: Electricity Consumption Analysis Engine
Performs hourly, daily, weekly, monthly aggregations, peak demand identification, and tariff billing calculations.
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple

from database.database import DatabaseManager
from utils.calculations import (
    calculate_energy_cost,
    calculate_time_of_day_cost,
    calculate_power_factor_efficiency,
    calculate_load_factor,
    calculate_carbon_emissions
)
from config import (
    DEFAULT_TARIFF_INR_PER_KWH,
    PEAK_TARIFF_INR_PER_KWH,
    OFF_PEAK_TARIFF_INR_PER_KWH
)


class ConsumptionAnalyzer:
    """
    Analyzes historical and real-time electricity telemetry data.
    """
    def __init__(self, db: DatabaseManager):
        self.db = db

    def get_realtime_metrics(self, device_id: Optional[str] = None) -> Dict[str, Any]:
        """Returns the most up-to-date instantaneous electrical readings."""
        if device_id and device_id != "ALL":
            df = self.db.get_readings(device_id=device_id, limit=1, order="DESC")
        else:
            df = self.db.get_latest_reading_for_each_device()

        if df.empty:
            return {
                "voltage": 230.0,
                "current": 0.0,
                "active_power": 0.0,
                "apparent_power": 0.0,
                "energy_kwh": 0.0,
                "power_factor": 0.92,
                "frequency": 50.0,
                "timestamp": "N/A"
            }

        return {
            "voltage": round(float(df["voltage"].mean()), 1),
            "current": round(float(df["current"].sum()), 2),
            "active_power": round(float(df["active_power"].sum()), 1),
            "apparent_power": round(float(df["apparent_power"].sum()), 1),
            "energy_kwh": round(float(df["energy_kwh"].sum()), 2),
            "power_factor": round(float(df["power_factor"].mean()), 3),
            "frequency": round(float(df["frequency"].mean()), 2),
            "timestamp": str(df["timestamp"].iloc[-1])
        }

    def analyze_historical_consumption(
        self, 
        device_id: Optional[str] = None, 
        building: Optional[str] = None,
        tariff_rate: float = DEFAULT_TARIFF_INR_PER_KWH
    ) -> Dict[str, Any]:
        """
        Executes comprehensive historical energy audit across multiple time granularities.
        """
        df = self.db.get_readings(device_id=device_id, building=building, order="ASC")
        if df.empty:
            return self._empty_analysis(tariff_rate)

        # Ensure datetime
        if not pd.api.types.is_datetime64_any_dtype(df["timestamp"]):
            df["timestamp"] = pd.to_datetime(df["timestamp"])

        # Calculate incremental kWh by device
        df = df.sort_values(["device_id", "timestamp"])
        df["prev_kwh"] = df.groupby("device_id")["energy_kwh"].shift(1)
        df["delta_kwh"] = (df["energy_kwh"] - df["prev_kwh"]).clip(lower=0.0)
        df["delta_kwh"] = df["delta_kwh"].fillna(df["active_power"] / 1000.0)

        total_kwh = float(df["delta_kwh"].sum())
        total_cost = calculate_energy_cost(total_kwh, tariff_rate)
        co2_emissions = calculate_carbon_emissions(total_kwh)

        # Peak Demand Identification
        peak_idx = df["active_power"].idxmax()
        peak_row = df.loc[peak_idx]
        peak_demand_w = float(peak_row["active_power"])
        peak_timestamp = str(peak_row["timestamp"])
        peak_device = str(peak_row.get("device_name", peak_row["device_id"]))
        avg_power_w = float(df["active_power"].mean())
        load_factor = calculate_load_factor(avg_power_w, peak_demand_w)

        # Daily breakdown
        df["date"] = df["timestamp"].dt.date
        daily_df = df.groupby("date").agg({
            "delta_kwh": "sum",
            "active_power": ["max", "mean"],
            "power_factor": "mean",
            "voltage": "mean"
        }).reset_index()
        daily_df.columns = ["date", "daily_energy_kwh", "peak_power_w", "avg_power_w", "avg_power_factor", "avg_voltage_v"]
        daily_df["date"] = daily_df["date"].astype(str)
        daily_df["cost_inr"] = (daily_df["daily_energy_kwh"] * tariff_rate).round(2)

        # Weekly breakdown (Last 7 days vs Prior 7 days)
        last_date = df["timestamp"].max()
        cutoff_7d = last_date - timedelta(days=7)
        cutoff_14d = last_date - timedelta(days=14)

        current_week_df = df[df["timestamp"] >= cutoff_7d]
        prior_week_df = df[(df["timestamp"] >= cutoff_14d) & (df["timestamp"] < cutoff_7d)]

        curr_week_kwh = float(current_week_df["delta_kwh"].sum())
        prior_week_kwh = float(prior_week_df["delta_kwh"].sum()) if not prior_week_df.empty else curr_week_kwh

        week_change_pct = ((curr_week_kwh - prior_week_kwh) / max(1.0, prior_week_kwh)) * 100.0

        # Monthly breakdown
        df["year_month"] = df["timestamp"].dt.strftime("%Y-%m")
        monthly_df = df.groupby("year_month").agg({
            "delta_kwh": "sum",
            "active_power": "max"
        }).reset_index()
        monthly_df.columns = ["month", "total_energy_kwh", "peak_power_w"]
        monthly_df["estimated_bill_inr"] = (monthly_df["total_energy_kwh"] * tariff_rate).round(2)

        # Time-of-Day (ToD) breakdown and potential savings
        tod_analysis = calculate_time_of_day_cost(df)

        # Power factor efficiency audit
        avg_pf = float(df["power_factor"].mean())
        pf_audit = calculate_power_factor_efficiency(avg_pf, total_kwh, total_cost)

        return {
            "total_kwh": round(total_kwh, 2),
            "total_cost_inr": round(total_cost, 2),
            "co2_emissions_kg": round(co2_emissions, 1),
            "avg_power_w": round(avg_power_w, 1),
            "peak_demand_w": round(peak_demand_w, 1),
            "peak_timestamp": peak_timestamp,
            "peak_device": peak_device,
            "load_factor": load_factor,
            "avg_power_factor": round(avg_pf, 3),
            "curr_week_kwh": round(curr_week_kwh, 2),
            "curr_week_cost_inr": round(curr_week_kwh * tariff_rate, 2),
            "prior_week_kwh": round(prior_week_kwh, 2),
            "week_change_pct": round(week_change_pct, 1),
            "daily_df": daily_df,
            "monthly_df": monthly_df,
            "tod_analysis": tod_analysis,
            "pf_audit": pf_audit,
            "tariff_rate": tariff_rate
        }

    def _empty_analysis(self, tariff_rate: float) -> Dict[str, Any]:
        """Fallback empty state."""
        return {
            "total_kwh": 0.0,
            "total_cost_inr": 0.0,
            "co2_emissions_kg": 0.0,
            "avg_power_w": 0.0,
            "peak_demand_w": 0.0,
            "peak_timestamp": "N/A",
            "peak_device": "N/A",
            "load_factor": 0.0,
            "avg_power_factor": 0.92,
            "curr_week_kwh": 0.0,
            "curr_week_cost_inr": 0.0,
            "prior_week_kwh": 0.0,
            "week_change_pct": 0.0,
            "daily_df": pd.DataFrame(),
            "monthly_df": pd.DataFrame(),
            "tod_analysis": {},
            "pf_audit": {"status": "NO_DATA", "penalty_inr": 0.0, "incentive_inr": 0.0, "recommendation": "No data."},
            "tariff_rate": tariff_rate
        }
