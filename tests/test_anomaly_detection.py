"""
VoltSense 5G - Unit Tests for Anomaly Detection Engine
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
from modules.anomaly_detection import AnomalyDetector


@pytest.fixture
def anomaly_test_env(tmp_path):
    """Sets up a database populated with baseline telemetry plus injected anomalies."""
    db_file = tmp_path / "test_anomaly.db"
    db = DatabaseManager(db_file)

    # Generate 50 normal hourly readings for a single device
    base_time = datetime(2026, 3, 1, 0, 0, 0)
    readings = []
    for h in range(50):
        t = base_time + timedelta(hours=h)
        readings.append({
            "device_id": "DEV_BLD_A_01",
            "timestamp": t.strftime("%Y-%m-%d %H:%M:%S"),
            "voltage": 230.0 + np.random.normal(0, 1.5),
            "current": 10.0 + np.random.normal(0, 0.5),
            "active_power": 2100.0 + np.random.normal(0, 50),
            "apparent_power": 2300.0,
            "energy_kwh": 1000.0 + (h * 2.1),
            "frequency": 50.0,
            "power_factor": 0.92,
            "is_simulated": 1,
            "transmission_protocol": "5G_URLLC",
            "latency_ms": 2.4,
            "packet_loss": 0
        })

    # Inject Anomaly 1: Severe power spike (10x normal power)
    readings[20]["active_power"] = 28000.0
    readings[20]["current"] = 125.0

    # Inject Anomaly 2: Voltage brownout (175V)
    readings[35]["voltage"] = 175.0

    # Inject Anomaly 3: Severe Low Power Factor (0.55)
    readings[42]["power_factor"] = 0.55

    db.insert_readings_bulk(readings)
    detector = AnomalyDetector(db)
    return db, detector


def test_statistical_anomaly_detection(anomaly_test_env):
    db, detector = anomaly_test_env
    anomalies = detector.scan_and_log_anomalies(device_id="DEV_BLD_A_01", method="STATISTICAL")
    assert not anomalies.empty

    # Verify that the 28kW spike was identified
    spike_events = anomalies[anomalies["metric"].str.contains("Active Power")]
    assert len(spike_events) > 0
    assert spike_events.iloc[0]["detected_value"] >= 20000.0

    # Verify that the voltage brownout was identified
    voltage_events = anomalies[anomalies["metric"].str.contains("Voltage")]
    assert len(voltage_events) > 0
    assert voltage_events.iloc[0]["severity"] == "CRITICAL"


def test_isolation_forest_anomaly_detection(anomaly_test_env):
    db, detector = anomaly_test_env
    anomalies = detector.scan_and_log_anomalies(device_id="DEV_BLD_A_01", method="ISOLATION_FOREST", sensitivity=0.06)
    assert not anomalies.empty
    methods = anomalies["detection_method"].unique()
    assert "Isolation Forest" in methods
