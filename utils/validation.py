"""
VoltSense 5G - Data Validation and Quality Assurance Engine
Ensures physical plausibility of electrical sensor measurements, validates device inputs and uploaded CSV datasets.
"""
import re
from typing import Dict, Any, List, Tuple
import pandas as pd


def validate_reading_dict(reading: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    Validates physical plausibility of incoming IoT electrical telemetry packet.
    """
    errors = []
    
    # Required keys
    req_keys = ["device_id", "timestamp", "voltage", "current", "active_power"]
    for k in req_keys:
        if k not in reading or reading[k] is None:
            errors.append(f"Missing mandatory telemetry field: '{k}'")
            return False, errors

    # Physical limits checks
    try:
        v = float(reading["voltage"])
        i = float(reading["current"])
        p = float(reading["active_power"])
        pf = float(reading.get("power_factor", 0.92))
        f = float(reading.get("frequency", 50.0))

        if not (100.0 <= v <= 300.0):
            errors.append(f"Voltage out of plausible AC range (100V - 300V): got {v}V")

        if i < 0.0 or i > 500.0:
            errors.append(f"Current out of physical range (0A - 500A): got {i}A")

        if p < 0.0 or p > 200000.0:
            errors.append(f"Active power out of physical range (0W - 200kW): got {p}W")

        if not (0.05 <= pf <= 1.0):
            errors.append(f"Power factor must be between 0.05 and 1.0: got {pf}")

        if not (45.0 <= f <= 65.0):
            errors.append(f"Frequency out of grid sync bounds (45Hz - 65Hz): got {f}Hz")

        # Physical law: Active Power P <= Apparent Power S (V * I)
        apparent_s = v * i
        if p > (apparent_s * 1.08):  # allow 8% sensor noise margin
            errors.append(f"Physical law violation: Active Power ({p}W) exceeds Apparent Power S ({apparent_s:.1f}VA)")

    except (ValueError, TypeError) as e:
        errors.append(f"Data type conversion failure: {str(e)}")

    return len(errors) == 0, errors


def validate_csv_dataset(df: pd.DataFrame) -> Tuple[bool, List[str], Dict[str, Any]]:
    """
    Validates structure and data hygiene of user-uploaded energy CSV datasets.
    """
    errors = []
    stats = {}

    if df.empty:
        return False, ["Uploaded CSV is empty"], stats

    required_cols = {"device_id", "timestamp", "voltage", "current", "active_power", "energy_kwh"}
    missing = required_cols - set(df.columns)
    if missing:
        errors.append(f"Missing required columns in CSV header: {', '.join(missing)}")
        return False, errors, stats

    # Parse timestamps
    try:
        df_parsed_time = pd.to_datetime(df["timestamp"], errors="coerce")
        null_times = df_parsed_time.isna().sum()
        if null_times > 0:
            errors.append(f"Found {null_times} rows with unparseable timestamp formats.")
    except Exception as e:
        errors.append(f"Timestamp parsing error: {str(e)}")

    # Check numeric columns
    numeric_cols = ["voltage", "current", "active_power", "energy_kwh"]
    for col in numeric_cols:
        non_numeric = pd.to_numeric(df[col], errors="coerce").isna().sum()
        if non_numeric > 0:
            errors.append(f"Column '{col}' contains {non_numeric} non-numeric entries.")

    # Check negative values
    if (df["voltage"] < 0).any():
        errors.append("Negative voltage values detected.")
    if (df["current"] < 0).any():
        errors.append("Negative current values detected.")
    if (df["active_power"] < 0).any():
        errors.append("Negative active power values detected.")
    if (df["energy_kwh"] < 0).any():
        errors.append("Negative accumulated energy values detected.")

    stats["total_rows"] = len(df)
    stats["unique_devices"] = df["device_id"].nunique()
    stats["devices"] = list(df["device_id"].unique())
    stats["min_voltage"] = float(df["voltage"].min())
    stats["max_voltage"] = float(df["voltage"].max())
    stats["max_power_w"] = float(df["active_power"].max())

    is_valid = len(errors) == 0
    return is_valid, errors, stats


def validate_device_registration(device_dict: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    Validates registration fields for an IoT smart meter.
    """
    errors = []
    dev_id = str(device_dict.get("device_id", "")).strip()
    name = str(device_dict.get("device_name", "")).strip()
    building = str(device_dict.get("building", "")).strip()
    ip = str(device_dict.get("ip_address", "")).strip()
    mac = str(device_dict.get("mac_address", "")).strip()

    if not dev_id:
        errors.append("Device ID cannot be empty.")
    elif not re.match(r"^[A-Za-z0-9_\-]+$", dev_id):
        errors.append("Device ID must contain only alphanumeric characters, dashes, and underscores.")

    if not name:
        errors.append("Device Name cannot be empty.")

    if not building:
        errors.append("Building / Location cannot be empty.")

    if ip:
        ip_pattern = r"^(\d{1,3}\.){3}\d{1,3}$"
        if not re.match(ip_pattern, ip):
            errors.append(f"Invalid IPv4 format: '{ip}'")

    if mac:
        mac_pattern = r"^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$"
        if not re.match(mac_pattern, mac):
            errors.append(f"Invalid MAC address format (expected XX:XX:XX:XX:XX:XX): '{mac}'")

    return len(errors) == 0, errors
