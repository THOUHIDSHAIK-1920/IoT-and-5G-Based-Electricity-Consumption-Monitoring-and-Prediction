"""
VoltSense 5G - SQLite Database Manager
Thread-safe SQLite persistent storage for IoT readings, device states, anomaly logs, and ML predictions.
"""
import sqlite3
import pandas as pd
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

from config import DB_PATH, DEFAULT_CAMPUS_DEVICES
from database.schema import (
    CREATE_DEVICES_TABLE,
    CREATE_READINGS_TABLE,
    CREATE_ANOMALIES_TABLE,
    CREATE_PREDICTIONS_TABLE,
    CREATE_MQTT_LOGS_TABLE,
    CREATE_INDEXES
)


class DatabaseManager:
    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = Path(db_path) if db_path else DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.init_db()

    def get_connection(self) -> sqlite3.Connection:
        """Returns SQLite connection with WAL journal mode and row factory."""
        conn = sqlite3.connect(str(self.db_path), timeout=30.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA foreign_keys=ON;")
        return conn

    def init_db(self):
        """Initializes tables, indexes, and default campus devices if empty."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(CREATE_DEVICES_TABLE)
            cursor.execute(CREATE_READINGS_TABLE)
            cursor.execute(CREATE_ANOMALIES_TABLE)
            cursor.execute(CREATE_PREDICTIONS_TABLE)
            cursor.execute(CREATE_MQTT_LOGS_TABLE)
            cursor.executescript(CREATE_INDEXES)
            conn.commit()

            # Seed default devices if table is empty
            cursor.execute("SELECT COUNT(*) as count FROM devices")
            if cursor.fetchone()["count"] == 0:
                for dev in DEFAULT_CAMPUS_DEVICES:
                    cursor.execute("""
                        INSERT OR IGNORE INTO devices 
                        (device_id, device_name, building, room, ip_address, mac_address, status, nominal_power_w, load_category)
                        VALUES (?, ?, ?, ?, ?, ?, 'ONLINE', ?, ?)
                    """, (
                        dev["device_id"],
                        dev["device_name"],
                        dev["building"],
                        dev["room"],
                        dev["ip_address"],
                        dev["mac_address"],
                        dev.get("nominal_power_w", 5000.0),
                        dev.get("load_category", "General")
                    ))
                conn.commit()

    # ---------------------------------------------------------
    # Device Management
    # ---------------------------------------------------------
    def get_devices(self) -> List[Dict[str, Any]]:
        """Retrieves all registered devices with their latest telemetry timestamp."""
        query = """
            SELECT d.*, 
                   MAX(r.timestamp) as last_reading_time,
                   r.active_power as latest_power_w,
                   r.voltage as latest_voltage_v
            FROM devices d
            LEFT JOIN readings r ON d.device_id = r.device_id
            GROUP BY d.device_id
            ORDER BY d.building, d.room
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query)
            return [dict(row) for row in cursor.fetchall()]

    def get_device(self, device_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves a single device by ID."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM devices WHERE device_id = ?", (device_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def add_device(self, device_data: Dict[str, Any]) -> bool:
        """Registers a new IoT smart meter."""
        query = """
            INSERT INTO devices (device_id, device_name, building, room, ip_address, mac_address, status, signal_rssi, firmware_version, nominal_power_w, load_category)
            VALUES (:device_id, :device_name, :building, :room, :ip_address, :mac_address, :status, :signal_rssi, :firmware_version, :nominal_power_w, :load_category)
        """
        defaults = {
            "status": "ONLINE",
            "signal_rssi": -65,
            "firmware_version": "v2.4.1-esp32",
            "nominal_power_w": 5000.0,
            "load_category": "General"
        }
        full_data = {**defaults, **device_data}
        try:
            with self.get_connection() as conn:
                conn.execute(query, full_data)
                conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

    def update_device(self, device_id: str, update_data: Dict[str, Any]) -> bool:
        """Updates device registration parameters."""
        fields = ", ".join([f"{k} = :{k}" for k in update_data.keys()])
        query = f"UPDATE devices SET {fields}, last_seen = CURRENT_TIMESTAMP WHERE device_id = :device_id"
        update_data["device_id"] = device_id
        with self.get_connection() as conn:
            cursor = conn.execute(query, update_data)
            conn.commit()
            return cursor.rowcount > 0

    def delete_device(self, device_id: str) -> bool:
        """Removes a device and cascades readings deletion."""
        with self.get_connection() as conn:
            cursor = conn.execute("DELETE FROM devices WHERE device_id = ?", (device_id,))
            conn.commit()
            return cursor.rowcount > 0

    # ---------------------------------------------------------
    # Readings Ingestion & Storage
    # ---------------------------------------------------------
    def insert_reading(self, reading: Dict[str, Any]) -> bool:
        """Inserts a single sensor reading; ignores duplicate timestamps for same device."""
        query = """
            INSERT OR IGNORE INTO readings 
            (device_id, timestamp, voltage, current, active_power, apparent_power, energy_kwh, frequency, power_factor, is_simulated, transmission_protocol, latency_ms, packet_loss)
            VALUES (:device_id, :timestamp, :voltage, :current, :active_power, :apparent_power, :energy_kwh, :frequency, :power_factor, :is_simulated, :transmission_protocol, :latency_ms, :packet_loss)
        """
        with self.get_connection() as conn:
            cursor = conn.execute(query, reading)
            # Update device last_seen and status
            conn.execute("UPDATE devices SET last_seen = :timestamp, status = 'ONLINE' WHERE device_id = :device_id", {
                "device_id": reading["device_id"],
                "timestamp": reading["timestamp"]
            })
            conn.commit()
            return cursor.rowcount > 0

    def insert_readings_bulk(self, readings: List[Dict[str, Any]]) -> int:
        """Bulk inserts telemetry records inside a single transaction."""
        if not readings:
            return 0
        query = """
            INSERT OR IGNORE INTO readings 
            (device_id, timestamp, voltage, current, active_power, apparent_power, energy_kwh, frequency, power_factor, is_simulated, transmission_protocol, latency_ms, packet_loss)
            VALUES (:device_id, :timestamp, :voltage, :current, :active_power, :apparent_power, :energy_kwh, :frequency, :power_factor, :is_simulated, :transmission_protocol, :latency_ms, :packet_loss)
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.executemany(query, readings)
            inserted_count = cursor.rowcount
            conn.commit()
            return inserted_count

    # ---------------------------------------------------------
    # Data Querying & Analytics Helpers
    # ---------------------------------------------------------
    def get_readings(self, 
                     device_id: Optional[str] = None, 
                     building: Optional[str] = None,
                     start_time: Optional[str] = None, 
                     end_time: Optional[str] = None,
                     limit: Optional[int] = None,
                     order: str = "ASC") -> pd.DataFrame:
        """Retrieves telemetry dataframe with optional multi-dimensional filters."""
        query = """
            SELECT r.*, d.device_name, d.building, d.room
            FROM readings r
            JOIN devices d ON r.device_id = d.device_id
            WHERE 1=1
        """
        params = []
        if device_id and device_id != "ALL":
            query += " AND r.device_id = ?"
            params.append(device_id)
        if building and building != "ALL":
            query += " AND d.building = ?"
            params.append(building)
        if start_time:
            query += " AND r.timestamp >= ?"
            params.append(start_time)
        if end_time:
            query += " AND r.timestamp <= ?"
            params.append(end_time)

        query += f" ORDER BY r.timestamp {order}"
        if limit:
            query += f" LIMIT {int(limit)}"

        with self.get_connection() as conn:
            df = pd.read_sql_query(query, conn, params=params)
            if not df.empty:
                df["timestamp"] = pd.to_datetime(df["timestamp"])
            return df

    def get_latest_reading_for_each_device(self) -> pd.DataFrame:
        """Returns the single latest reading for every registered device."""
        query = """
            SELECT r.*, d.device_name, d.building, d.room, d.status as device_status
            FROM readings r
            JOIN (
                SELECT device_id, MAX(timestamp) as max_time
                FROM readings
                GROUP BY device_id
            ) latest ON r.device_id = latest.device_id AND r.timestamp = latest.max_time
            JOIN devices d ON r.device_id = d.device_id
        """
        with self.get_connection() as conn:
            df = pd.read_sql_query(query, conn)
            if not df.empty:
                df["timestamp"] = pd.to_datetime(df["timestamp"])
            return df

    def get_daily_consumption(self, device_id: Optional[str] = None, building: Optional[str] = None) -> pd.DataFrame:
        """Computes daily energy consumption by subtracting daily start from daily end kWh or summing delta."""
        query = """
            SELECT 
                DATE(r.timestamp) as date,
                r.device_id,
                d.device_name,
                d.building,
                MAX(r.energy_kwh) - MIN(r.energy_kwh) as daily_energy_kwh,
                MAX(r.active_power) as peak_power_w,
                AVG(r.active_power) as avg_power_w,
                AVG(r.voltage) as avg_voltage_v,
                AVG(r.power_factor) as avg_power_factor
            FROM readings r
            JOIN devices d ON r.device_id = d.device_id
            WHERE 1=1
        """
        params = []
        if device_id and device_id != "ALL":
            query += " AND r.device_id = ?"
            params.append(device_id)
        if building and building != "ALL":
            query += " AND d.building = ?"
            params.append(building)

        query += " GROUP BY DATE(r.timestamp), r.device_id ORDER BY date ASC"

        with self.get_connection() as conn:
            df = pd.read_sql_query(query, conn, params=params)
            return df

    def get_hourly_aggregate(self, device_id: Optional[str] = None) -> pd.DataFrame:
        """Aggregates energy consumption by hour of the day (0-23) for diurnal pattern analysis."""
        query = """
            SELECT 
                CAST(strftime('%H', timestamp) AS INTEGER) as hour,
                AVG(active_power) as avg_power_w,
                MAX(active_power) as max_power_w,
                MIN(active_power) as min_power_w,
                AVG(power_factor) as avg_power_factor,
                AVG(voltage) as avg_voltage_v
            FROM readings
            WHERE 1=1
        """
        params = []
        if device_id and device_id != "ALL":
            query += " AND device_id = ?"
            params.append(device_id)
        query += " GROUP BY hour ORDER BY hour ASC"

        with self.get_connection() as conn:
            return pd.read_sql_query(query, conn, params=params)

    # ---------------------------------------------------------
    # Anomalies Management
    # ---------------------------------------------------------
    def insert_anomaly(self, anomaly: Dict[str, Any]) -> int:
        """Logs a detected consumption or electrical anomaly."""
        query = """
            INSERT INTO anomalies (device_id, timestamp, metric, detected_value, expected_range, severity, detection_method, reason, resolved)
            VALUES (:device_id, :timestamp, :metric, :detected_value, :expected_range, :severity, :detection_method, :reason, 0)
        """
        with self.get_connection() as conn:
            cursor = conn.execute(query, anomaly)
            conn.commit()
            return cursor.lastrowid

    def insert_anomalies_bulk(self, anomalies: List[Dict[str, Any]]) -> int:
        """Bulk inserts detected anomaly events."""
        if not anomalies:
            return 0
        query = """
            INSERT INTO anomalies (device_id, timestamp, metric, detected_value, expected_range, severity, detection_method, reason, resolved)
            VALUES (:device_id, :timestamp, :metric, :detected_value, :expected_range, :severity, :detection_method, :reason, 0)
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.executemany(query, anomalies)
            conn.commit()
            return cursor.rowcount

    def get_anomalies(self, device_id: Optional[str] = None, severity: Optional[str] = None, limit: int = 100) -> pd.DataFrame:
        """Fetches anomalies with device details."""
        query = """
            SELECT a.*, d.device_name, d.building, d.room
            FROM anomalies a
            JOIN devices d ON a.device_id = d.device_id
            WHERE 1=1
        """
        params = []
        if device_id and device_id != "ALL":
            query += " AND a.device_id = ?"
            params.append(device_id)
        if severity and severity != "ALL":
            query += " AND a.severity = ?"
            params.append(severity)

        query += f" ORDER BY a.timestamp DESC LIMIT {int(limit)}"
        with self.get_connection() as conn:
            df = pd.read_sql_query(query, conn, params=params)
            if not df.empty:
                df["timestamp"] = pd.to_datetime(df["timestamp"])
            return df

    def resolve_anomaly(self, anomaly_id: int) -> bool:
        """Marks an anomaly as acknowledged/resolved."""
        with self.get_connection() as conn:
            cursor = conn.execute("UPDATE anomalies SET resolved = 1 WHERE id = ?", (anomaly_id,))
            conn.commit()
            return cursor.rowcount > 0

    # ---------------------------------------------------------
    # Predictions Storage
    # ---------------------------------------------------------
    def save_predictions(self, predictions: List[Dict[str, Any]]) -> int:
        """Saves generated forecast rows with evaluation metrics."""
        if not predictions:
            return 0
        query = """
            INSERT INTO predictions (model_name, horizon, target_date, predicted_energy_kwh, lower_bound_kwh, upper_bound_kwh, actual_energy_kwh, mae, rmse, r2_score)
            VALUES (:model_name, :horizon, :target_date, :predicted_energy_kwh, :lower_bound_kwh, :upper_bound_kwh, :actual_energy_kwh, :mae, :rmse, :r2_score)
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.executemany(query, predictions)
            conn.commit()
            return cursor.rowcount

    def get_latest_predictions(self, model_name: Optional[str] = None, horizon: Optional[str] = None) -> pd.DataFrame:
        """Fetches recent machine learning predictions."""
        query = "SELECT * FROM predictions WHERE 1=1"
        params = []
        if model_name:
            query += " AND model_name = ?"
            params.append(model_name)
        if horizon:
            query += " AND horizon = ?"
            params.append(horizon)
        query += " ORDER BY target_date ASC"
        with self.get_connection() as conn:
            return pd.read_sql_query(query, conn, params=params)

    # ---------------------------------------------------------
    # MQTT Telemetry Logging
    # ---------------------------------------------------------
    def log_mqtt(self, topic: str, payload: str, qos: int = 1, latency_ms: Optional[float] = None):
        """Logs an incoming MQTT packet."""
        with self.get_connection() as conn:
            conn.execute(
                "INSERT INTO mqtt_logs (topic, payload, qos, latency_ms) VALUES (?, ?, ?, ?)",
                (topic, payload, qos, latency_ms)
            )
            conn.commit()

    def get_mqtt_logs(self, limit: int = 40) -> pd.DataFrame:
        """Retrieves raw MQTT packet stream logs."""
        with self.get_connection() as conn:
            return pd.read_sql_query(
                f"SELECT * FROM mqtt_logs ORDER BY timestamp DESC LIMIT {int(limit)}", conn
            )

    # ---------------------------------------------------------
    # CSV Import / Export & Maintenance
    # ---------------------------------------------------------
    def export_readings_csv(self) -> str:
        """Exports all readings to CSV string."""
        df = self.get_readings(order="ASC")
        return df.to_csv(index=False)

    def import_readings_csv(self, file_content_or_path) -> Tuple[int, int]:
        """Imports readings from CSV with verification and duplicate rejection."""
        if isinstance(file_content_or_path, (str, Path)):
            df = pd.read_csv(file_content_or_path)
        else:
            df = pd.read_csv(file_content_or_path)

        required_cols = {"device_id", "timestamp", "voltage", "current", "active_power", "energy_kwh"}
        if not required_cols.issubset(df.columns):
            missing = required_cols - set(df.columns)
            raise ValueError(f"Missing mandatory CSV columns: {missing}")

        # Compute apparent power and power factor if absent
        if "apparent_power" not in df.columns:
            df["apparent_power"] = df["voltage"] * df["current"]
        if "power_factor" not in df.columns:
            df["power_factor"] = (df["active_power"] / df["apparent_power"]).clip(0.1, 1.0).fillna(0.92)
        if "frequency" not in df.columns:
            df["frequency"] = 50.0
        if "is_simulated" not in df.columns:
            df["is_simulated"] = 0
        if "transmission_protocol" not in df.columns:
            df["transmission_protocol"] = "CSV_IMPORT"
        if "latency_ms" not in df.columns:
            df["latency_ms"] = 0.0
        if "packet_loss" not in df.columns:
            df["packet_loss"] = 0

        # Ensure devices exist
        unique_devs = df["device_id"].unique()
        with self.get_connection() as conn:
            cursor = conn.cursor()
            for dev_id in unique_devs:
                cursor.execute("""
                    INSERT OR IGNORE INTO devices (device_id, device_name, building, room)
                    VALUES (?, ?, 'Imported Site', 'General Facility')
                """, (dev_id, f"Imported Device {dev_id}"))
            conn.commit()

        readings_records = df.to_dict(orient="records")
        initial_count = self.get_total_readings_count()
        self.insert_readings_bulk(readings_records)
        new_count = self.get_total_readings_count()
        inserted = new_count - initial_count
        skipped = len(readings_records) - inserted
        return inserted, skipped

    def get_total_readings_count(self) -> int:
        """Returns total count of stored readings."""
        with self.get_connection() as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM readings")
            return cursor.fetchone()[0]

    def clear_readings(self):
        """Clears all readings and anomalies (for test resets)."""
        with self.get_connection() as conn:
            conn.execute("DELETE FROM readings")
            conn.execute("DELETE FROM anomalies")
            conn.execute("DELETE FROM predictions")
            conn.execute("DELETE FROM mqtt_logs")
            conn.commit()
