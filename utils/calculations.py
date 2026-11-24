"""
VoltSense 5G - Electrical and Financial Calculations Engine
Implements mathematically rigorous electrical engineering relationships and tariff formulas.
"""
import math
import pandas as pd
from typing import Dict, Any, Tuple, Optional
from config import (
    DEFAULT_TARIFF_INR_PER_KWH,
    PEAK_TARIFF_INR_PER_KWH,
    OFF_PEAK_TARIFF_INR_PER_KWH,
    PEAK_HOURS,
    OFF_PEAK_HOURS,
    NOMINAL_VOLTAGE_V,
    NOMINAL_FREQUENCY_HZ,
    TARGET_POWER_FACTOR
)

# Indian Grid Baseline Emission Factor (CEA CO2 Baseline Database v19)
GRID_EMISSION_FACTOR_KG_CO2_PER_KWH = 0.82


def calculate_apparent_power(voltage_v: float, current_a: float) -> float:
    """
    Computes single-phase apparent power in Volt-Amperes (VA).
    Formula: S = V * I
    """
    return round(float(voltage_v) * float(current_a), 2)


def calculate_active_power(voltage_v: float, current_a: float, power_factor: float) -> float:
    """
    Computes single-phase active power in Watts (W).
    Formula: P = V * I * Power_Factor
    """
    pf_clamped = max(0.05, min(1.0, float(power_factor)))
    return round(float(voltage_v) * float(current_a) * pf_clamped, 2)


def calculate_reactive_power(apparent_power_va: float, active_power_w: float) -> float:
    """
    Computes reactive power in Volt-Amperes Reactive (VAR).
    Formula: Q = sqrt(S^2 - P^2)
    """
    s = float(apparent_power_va)
    p = float(active_power_w)
    if s < p:
        s = p
    return round(math.sqrt(max(0.0, s**2 - p**2)), 2)


def calculate_energy_increment_kwh(power_w: float, duration_seconds: float) -> float:
    """
    Computes incremental electrical energy consumed over a specified duration.
    Energy (kWh) = (Power in Watts / 1000) * (duration in seconds / 3600)
    """
    power_kw = float(power_w) / 1000.0
    duration_hours = float(duration_seconds) / 3600.0
    return power_kw * duration_hours


def calculate_energy_cost(
    energy_kwh: float, 
    tariff_inr_per_kwh: float = DEFAULT_TARIFF_INR_PER_KWH
) -> float:
    """
    Computes standard energy cost in INR (₹).
    Formula: Cost = Energy (kWh) * Tariff (₹/kWh)
    """
    return round(float(energy_kwh) * float(tariff_inr_per_kwh), 2)


def calculate_time_of_day_cost(readings_df: pd.DataFrame) -> Dict[str, Any]:
    """
    Calculates Time-of-Day (ToD) tariff bill with peak, normal, and off-peak breakdowns.
    """
    if readings_df.empty:
        return {
            "total_kwh": 0.0,
            "peak_kwh": 0.0,
            "off_peak_kwh": 0.0,
            "normal_kwh": 0.0,
            "base_bill_inr": 0.0,
            "tod_bill_inr": 0.0,
            "peak_cost_inr": 0.0,
            "off_peak_cost_inr": 0.0,
            "normal_cost_inr": 0.0,
            "potential_tod_savings_inr": 0.0
        }

    df = readings_df.copy()
    if not pd.api.types.is_datetime64_any_dtype(df["timestamp"]):
        df["timestamp"] = pd.to_datetime(df["timestamp"])

    df["hour"] = df["timestamp"].dt.hour
    
    # Calculate incremental kWh between sequential rows per device
    df = df.sort_values(["device_id", "timestamp"])
    df["prev_kwh"] = df.groupby("device_id")["energy_kwh"].shift(1)
    df["delta_kwh"] = (df["energy_kwh"] - df["prev_kwh"]).clip(lower=0.0)
    # If first row or delta is null/zero, approximate from active_power if delta is 0
    df["delta_kwh"] = df["delta_kwh"].fillna(df["active_power"] / 1000.0)

    total_kwh = df["delta_kwh"].sum()
    
    # Hour classifications
    peak_mask = df["hour"].isin(PEAK_HOURS)
    off_peak_mask = df["hour"].isin(OFF_PEAK_HOURS)
    normal_mask = ~peak_mask & ~off_peak_mask

    peak_kwh = df.loc[peak_mask, "delta_kwh"].sum()
    off_peak_kwh = df.loc[off_peak_mask, "delta_kwh"].sum()
    normal_kwh = df.loc[normal_mask, "delta_kwh"].sum()

    peak_cost = peak_kwh * PEAK_TARIFF_INR_PER_KWH
    off_peak_cost = off_peak_kwh * OFF_PEAK_TARIFF_INR_PER_KWH
    normal_cost = normal_kwh * DEFAULT_TARIFF_INR_PER_KWH
    tod_bill = peak_cost + off_peak_cost + normal_cost

    base_bill = total_kwh * DEFAULT_TARIFF_INR_PER_KWH
    # Potential savings if 20% of peak load is shifted to off-peak hours
    shiftable_kwh = peak_kwh * 0.20
    tod_savings = shiftable_kwh * (PEAK_TARIFF_INR_PER_KWH - OFF_PEAK_TARIFF_INR_PER_KWH)

    return {
        "total_kwh": round(float(total_kwh), 2),
        "peak_kwh": round(float(peak_kwh), 2),
        "off_peak_kwh": round(float(off_peak_kwh), 2),
        "normal_kwh": round(float(normal_kwh), 2),
        "base_bill_inr": round(float(base_bill), 2),
        "tod_bill_inr": round(float(tod_bill), 2),
        "peak_cost_inr": round(float(peak_cost), 2),
        "off_peak_cost_inr": round(float(off_peak_cost), 2),
        "normal_cost_inr": round(float(normal_cost), 2),
        "potential_tod_savings_inr": round(float(tod_savings), 2)
    }


def calculate_power_factor_efficiency(avg_power_factor: float, total_kwh: float, base_bill_inr: float) -> Dict[str, Any]:
    """
    Evaluates power factor health, low PF penalties, and APFC capacitor savings.
    Standard regulatory threshold: 0.90 lag.
    Penalty: 1% per 0.01 drop below 0.90.
    Incentive: 0.5% rebate if PF > 0.95.
    """
    pf = max(0.5, min(1.0, float(avg_power_factor)))
    status = "OPTIMAL"
    penalty_inr = 0.0
    incentive_inr = 0.0
    recommendation = "Power factor is within high efficiency threshold. APFC capacitor banks operating nominally."

    if pf < 0.90:
        status = "PENALTY_RISK"
        drop_points = int((0.90 - pf) * 100)
        penalty_percentage = min(15.0, drop_points * 1.0)
        penalty_inr = round(base_bill_inr * (penalty_percentage / 100.0), 2)
        recommendation = (
            f"Power factor ({pf:.2f}) is below grid threshold (0.90). "
            f"Estimated utility surcharge penalty: ₹{penalty_inr:.2f}. "
            "Install automatic power factor correction (APFC) capacitors to avoid surcharges."
        )
    elif pf >= 0.95:
        status = "INCENTIVE_ELIGIBLE"
        incentive_inr = round(base_bill_inr * 0.01, 2)
        recommendation = f"Excellent power factor ({pf:.2f}). Grid rebate of up to ₹{incentive_inr:.2f} applicable."

    return {
        "status": status,
        "avg_power_factor": round(pf, 3),
        "penalty_inr": penalty_inr,
        "incentive_inr": incentive_inr,
        "recommendation": recommendation
    }


def calculate_load_factor(avg_power_w: float, peak_power_w: float) -> float:
    """
    Computes electrical load factor: Ratio of average load to peak load.
    Load Factor = Avg Load / Peak Load (0.0 to 1.0)
    High load factor (>0.70) signifies efficient, balanced equipment utilization.
    """
    if peak_power_w <= 0:
        return 0.0
    return round(min(1.0, float(avg_power_w) / float(peak_power_w)), 3)


def calculate_carbon_emissions(energy_kwh: float) -> float:
    """
    Estimates greenhouse gas CO2 emissions in kilograms (kg CO2e).
    """
    return round(float(energy_kwh) * GRID_EMISSION_FACTOR_KG_CO2_PER_KWH, 2)
