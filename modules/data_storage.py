"""
VoltSense 5G - Module 1: Data Storage and Ingestion Pipeline
Coordinates database persistence, CSV import/export validation, and historical data retrieval.
"""
import io
import pandas as pd
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path

from database.database import DatabaseManager
from utils.validation import validate_reading_dict, validate_csv_dataset


class DataStorageManager:
    """
    Manages telemetry ingestion, file uploads, historical retrieval and export operations.
    """
    def __init__(self, db: DatabaseManager):
        self.db = db

    def ingest_reading(self, reading_data: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """Validates and persists an individual IoT telemetry record."""
        is_valid, errors = validate_reading_dict(reading_data)
        if not is_valid:
            return False, "; ".join(errors)

        success = self.db.insert_reading(reading_data)
        if success:
            return True, None
        else:
            return False, "Database rejected insertion (likely duplicate timestamp for this device)."

    def import_csv(self, file_content) -> Tuple[bool, str, Dict[str, Any]]:
        """Imports an external energy CSV file with rigorous schema validation."""
        try:
            if isinstance(file_content, bytes):
                df = pd.read_csv(io.BytesIO(file_content))
            elif hasattr(file_content, "read"):
                df = pd.read_csv(file_content)
            else:
                df = pd.read_csv(file_content)

            is_valid, errors, stats = validate_csv_dataset(df)
            if not is_valid:
                return False, f"Validation Failed: {'; '.join(errors[:3])}", stats

            inserted, skipped = self.db.import_readings_csv(df)
            msg = f"Successfully imported {inserted} records into database ({skipped} duplicate rows skipped)."
            stats["inserted_rows"] = inserted
            stats["skipped_rows"] = skipped
            return True, msg, stats
        except Exception as e:
            return False, f"CSV Processing Error: {str(e)}", {}

    def export_csv(self) -> str:
        """Returns all database readings as a CSV formatted string."""
        return self.db.export_readings_csv()

    def get_summary_statistics(self, device_id: Optional[str] = None) -> Dict[str, Any]:
        """Calculates global dataset statistics."""
        df = self.db.get_readings(device_id=device_id)
        if df.empty:
            return {
                "total_readings": 0,
                "total_energy_kwh": 0.0,
                "avg_power_w": 0.0,
                "peak_power_w": 0.0,
                "avg_voltage_v": 230.0,
                "avg_power_factor": 0.92,
                "devices_count": len(self.db.get_devices())
            }

        # Calculate incremental energy across devices
        total_energy = df.groupby("device_id")["energy_kwh"].agg(
            lambda s: max(0.0, s.max() - s.min()) if len(s) > 1 else s.iloc[-1]
        ).sum()

        return {
            "total_readings": len(df),
            "total_energy_kwh": round(float(total_energy), 2),
            "avg_power_w": round(float(df["active_power"].mean()), 1),
            "peak_power_w": round(float(df["active_power"].max()), 1),
            "avg_voltage_v": round(float(df["voltage"].mean()), 1),
            "avg_power_factor": round(float(df["power_factor"].mean()), 3),
            "devices_count": df["device_id"].nunique()
        }
