"""
VoltSense 5G - Realistic Sample Energy Telemetry Generator
Generates a physics-compliant 30-day hourly dataset for campus smart meters adhering to IEEE electrical standards.
"""
import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import random
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from config import (
    DEFAULT_CAMPUS_DEVICES,
    SAMPLE_CSV_PATH,
    NOMINAL_VOLTAGE_V,
    NOMINAL_FREQUENCY_HZ,
    DB_PATH
)
from utils.calculations import calculate_apparent_power, calculate_active_power


def generate_campus_energy_dataset(days: int = 30, seed: int = 42) -> pd.DataFrame:
    """
    Synthesizes multi-device 30-day hourly telemetry with realistic diurnal load curves.
    """
    np.random.seed(seed)
    random.seed(seed)

    end_time = datetime.now().replace(minute=0, second=0, microsecond=0)
    start_time = end_time - timedelta(days=days)
    hours = int((end_time - start_time).total_seconds() // 3600)

    records = []

    # Device baseline properties
    device_specs = {
        "DEV_BLD_A_01": {"base_w": 1200, "peak_w": 9500, "pf_mean": 0.94, "energy_start": 3420.0},
        "DEV_BLD_A_02": {"base_w": 600, "peak_w": 4500, "pf_mean": 0.93, "energy_start": 1850.0},
        "DEV_BLD_B_01": {"base_w": 2500, "peak_w": 15800, "pf_mean": 0.88, "energy_start": 6200.0},
        "DEV_BLD_B_02": {"base_w": 7500, "peak_w": 19200, "pf_mean": 0.92, "energy_start": 9840.0},
        "DEV_CLS_01":   {"base_w": 400, "peak_w": 10500, "pf_mean": 0.91, "energy_start": 2100.0},
        "DEV_LIB_01":   {"base_w": 1100, "peak_w": 6800, "pf_mean": 0.95, "energy_start": 4150.0},
    }

    device_lookup = {d["device_id"]: d for d in DEFAULT_CAMPUS_DEVICES}

    for dev_id, spec in device_specs.items():
        dev_info = device_lookup.get(dev_id, {})
        current_energy_kwh = spec["energy_start"]

        for h in range(hours):
            current_dt = start_time + timedelta(hours=h)
            hour_of_day = current_dt.hour
            is_weekend = current_dt.weekday() >= 5  # Sat/Sun

            # Diurnal curve calculation (0.0 to 1.0 multiplier)
            if 0 <= hour_of_day < 7:
                # Night base load
                diurnal_factor = 0.10 + 0.05 * np.sin((hour_of_day / 7) * np.pi)
            elif 7 <= hour_of_day < 13:
                # Morning ramp-up
                diurnal_factor = 0.35 + 0.65 * ((hour_of_day - 7) / 6.0)
            elif 13 <= hour_of_day < 17:
                # Afternoon peak
                diurnal_factor = 0.90 + 0.10 * np.cos(((hour_of_day - 13) / 4.0) * np.pi)
            elif 17 <= hour_of_day < 21:
                # Evening taper
                diurnal_factor = 0.45 + 0.40 * (1.0 - (hour_of_day - 17) / 4.0)
            else:
                # Late night
                diurnal_factor = 0.18

            # Weekend reduction (academic campus load drops by 55% on weekends, except server room DEV_BLD_B_02)
            if is_weekend and dev_id != "DEV_BLD_B_02":
                diurnal_factor *= 0.35

            # Random noise (+/- 6%)
            noise = np.random.normal(1.0, 0.04)
            active_power_w = (spec["base_w"] + (spec["peak_w"] - spec["base_w"]) * diurnal_factor) * noise
            active_power_w = max(spec["base_w"] * 0.8, active_power_w)

            # Grid Voltage: 230V nominal with slight dip during peak hours
            v_dip = 4.0 if (17 <= hour_of_day <= 21) else 0.0
            voltage_v = round(float(np.random.normal(NOMINAL_VOLTAGE_V - v_dip, 2.5)), 1)
            voltage_v = max(208.0, min(246.0, voltage_v))

            # Grid Frequency: 50Hz nominal
            frequency_hz = round(float(np.random.normal(NOMINAL_FREQUENCY_HZ, 0.08)), 2)

            # Power Factor: centered around mean with non-linear load variations
            pf = round(float(np.random.normal(spec["pf_mean"], 0.015)), 3)
            pf = max(0.75, min(0.99, pf))

            # Current: I = P / (V * PF)
            current_a = round(active_power_w / (voltage_v * pf), 2)

            # Recalculate Active Power P and Apparent Power S strictly to enforce exact physics
            apparent_power_va = calculate_apparent_power(voltage_v, current_a)
            active_power_w = calculate_active_power(voltage_v, current_a, pf)

            # Energy accumulation: Delta kWh for 1 hour
            delta_kwh = active_power_w / 1000.0
            current_energy_kwh += delta_kwh

            records.append({
                "device_id": dev_id,
                "timestamp": current_dt.strftime("%Y-%m-%d %H:%M:%S"),
                "voltage": voltage_v,
                "current": current_a,
                "active_power": active_power_w,
                "apparent_power": apparent_power_va,
                "energy_kwh": round(current_energy_kwh, 3),
                "frequency": frequency_hz,
                "power_factor": pf,
                "is_simulated": 1,
                "transmission_protocol": "5G_URLLC",
                "latency_ms": round(float(np.random.normal(2.8, 0.4)), 2),
                "packet_loss": 1 if np.random.random() < 0.0001 else 0
            })

    df = pd.DataFrame(records)

    # Inject controlled, realistic anomalies for evaluation
    df = inject_controlled_anomalies(df)

    return df


def inject_controlled_anomalies(df: pd.DataFrame) -> pd.DataFrame:
    """
    Injects 4 distinct realistic grid events into specific timestamps for validation.
    """
    df = df.copy()

    # Anomaly 1: Severe Power Spike on Computer Lab 101 (Short circuit / lab equipment runaway)
    mask1 = (df["device_id"] == "DEV_BLD_B_01")
    if mask1.any():
        idx1 = df[mask1].index[int(len(df[mask1]) * 0.65)]
        df.loc[idx1, "active_power"] = 34500.0  # normally max 15.8kW
        df.loc[idx1, "current"] = 155.0
        df.loc[idx1, "apparent_power"] = df.loc[idx1, "voltage"] * 155.0

    # Anomaly 2: Midnight HVAC Leak in Admin Office (Unscheduled overnight consumption)
    mask2 = (df["device_id"] == "DEV_BLD_A_01")
    if mask2.any():
        idx2 = df[mask2].index[int(len(df[mask2]) * 0.40)]
        df.loc[idx2, "active_power"] = 13800.0
        df.loc[idx2, "current"] = 62.5
        df.loc[idx2, "apparent_power"] = df.loc[idx2, "voltage"] * 62.5

    # Anomaly 3: Capacitor Bank Failure / Extreme Low Power Factor in Lecture Hall
    mask3 = (df["device_id"] == "DEV_CLS_01")
    if mask3.any():
        idx3 = df[mask3].index[int(len(df[mask3]) * 0.75)]
        df.loc[idx3, "power_factor"] = 0.58
        df.loc[idx3, "current"] = 82.0
        df.loc[idx3, "apparent_power"] = df.loc[idx3, "voltage"] * 82.0
        df.loc[idx3, "active_power"] = df.loc[idx3, "apparent_power"] * 0.58

    # Anomaly 4: Grid Brownout / Voltage Sag in Central Library
    mask4 = (df["device_id"] == "DEV_LIB_01")
    if mask4.any():
        idx4 = df[mask4].index[int(len(df[mask4]) * 0.85)]
        df.loc[idx4, "voltage"] = 182.0
        df.loc[idx4, "apparent_power"] = 182.0 * df.loc[idx4, "current"]
        df.loc[idx4, "active_power"] = df.loc[idx4, "apparent_power"] * df.loc[idx4, "power_factor"]

    return df


def seed_database_and_save_csv():
    """Generates sample dataset and populates both CSV and SQLite database."""
    print("Generating VoltSense 5G campus energy telemetry dataset...")
    df = generate_campus_energy_dataset(days=30)
    
    # Save CSV
    SAMPLE_CSV_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(SAMPLE_CSV_PATH, index=False)
    print(f"Sample data saved to: {SAMPLE_CSV_PATH} ({len(df)} records)")

    # Insert into SQLite Database
    from database.database import DatabaseManager
    db = DatabaseManager(DB_PATH)
    initial_count = db.get_total_readings_count()
    if initial_count == 0:
        print("Populating SQLite database with initial campus telemetry...")
        db.insert_readings_bulk(df.to_dict(orient="records"))
        print(f"Database successfully populated! Total records: {db.get_total_readings_count()}")
    else:
        print(f"Database already contains {initial_count} readings. Skipping duplicate insertion.")


if __name__ == "__main__":
    seed_database_and_save_csv()
