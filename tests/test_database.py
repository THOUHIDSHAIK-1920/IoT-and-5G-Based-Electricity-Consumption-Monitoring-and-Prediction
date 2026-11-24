"""
VoltSense 5G - Unit Tests for SQLite Database Storage and Ingestion
"""
import pytest
import sqlite3
import pandas as pd
from datetime import datetime
import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from database.database import DatabaseManager


@pytest.fixture
def temp_db(tmp_path):
    """Provides a fresh temporary SQLite database instance."""
    db_file = tmp_path / "test_voltsense.db"
    db = DatabaseManager(db_file)
    return db


def test_db_initialization(temp_db):
    devices = temp_db.get_devices()
    # Should be pre-seeded with default campus devices
    assert len(devices) > 0


def test_device_crud(temp_db):
    new_device = {
        "device_id": "TEST_DEV_99",
        "device_name": "Test Engineering Unit",
        "building": "Test Hall",
        "room": "Room 99",
        "ip_address": "192.168.99.1",
        "mac_address": "AA:BB:CC:DD:EE:FF",
        "nominal_power_w": 3000.0,
        "load_category": "Lab"
    }
    assert temp_db.add_device(new_device) is True
    
    # Retrieve
    dev = temp_db.get_device("TEST_DEV_99")
    assert dev is not None
    assert dev["device_name"] == "Test Engineering Unit"

    # Duplicate device ID insertion should fail gracefully
    assert temp_db.add_device(new_device) is False

    # Delete
    assert temp_db.delete_device("TEST_DEV_99") is True
    assert temp_db.get_device("TEST_DEV_99") is None


def test_reading_insertion_and_deduplication(temp_db):
    reading = {
        "device_id": "DEV_BLD_A_01",
        "timestamp": "2026-03-24 10:00:00",
        "voltage": 230.1,
        "current": 12.5,
        "active_power": 2650.0,
        "apparent_power": 2876.25,
        "energy_kwh": 1050.2,
        "frequency": 50.01,
        "power_factor": 0.92,
        "is_simulated": 1,
        "transmission_protocol": "5G_URLLC",
        "latency_ms": 2.5,
        "packet_loss": 0
    }
    # First insert succeeds
    success = temp_db.insert_reading(reading)
    assert success is True

    # Duplicate insert with identical device_id and timestamp should be ignored
    dup_success = temp_db.insert_reading(reading)
    assert dup_success is False


def test_bulk_reading_insertion_and_query(temp_db):
    readings = []
    base_time = datetime(2026, 3, 24, 12, 0, 0)
    for i in range(5):
        ts = base_time.replace(minute=i).strftime("%Y-%m-%d %H:%M:%S")
        readings.append({
            "device_id": "DEV_BLD_B_01",
            "timestamp": ts,
            "voltage": 230.0 + i,
            "current": 10.0,
            "active_power": 2100.0,
            "apparent_power": 2300.0,
            "energy_kwh": 2000.0 + (i * 0.1),
            "frequency": 50.0,
            "power_factor": 0.91,
            "is_simulated": 1,
            "transmission_protocol": "5G_URLLC",
            "latency_ms": 2.1,
            "packet_loss": 0
        })
    inserted = temp_db.insert_readings_bulk(readings)
    assert inserted == 5

    df = temp_db.get_readings(device_id="DEV_BLD_B_01")
    assert len(df) == 5
    assert "active_power" in df.columns


def test_anomaly_logging(temp_db):
    anomaly = {
        "device_id": "DEV_BLD_A_01",
        "timestamp": "2026-03-24 14:30:00",
        "metric": "Active Power (W)",
        "detected_value": 35000.0,
        "expected_range": "<= 10000 W",
        "severity": "CRITICAL",
        "detection_method": "Z-Score",
        "reason": "Unexpected Short-Circuit Power Surge"
    }
    anom_id = temp_db.insert_anomaly(anomaly)
    assert anom_id > 0

    df_anom = temp_db.get_anomalies(device_id="DEV_BLD_A_01")
    assert len(df_anom) == 1
    assert df_anom.iloc[0]["severity"] == "CRITICAL"
