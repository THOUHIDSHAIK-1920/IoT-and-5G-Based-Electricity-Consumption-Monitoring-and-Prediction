"""
VoltSense 5G - SQLite Database Schema Definitions
Normalized Relational Architecture for IoT Energy Telemetry, Device Registry, Anomalies, and Predictions.
"""

CREATE_DEVICES_TABLE = """
CREATE TABLE IF NOT EXISTS devices (
    device_id TEXT PRIMARY KEY,
    device_name TEXT NOT NULL,
    building TEXT NOT NULL,
    room TEXT NOT NULL,
    ip_address TEXT,
    mac_address TEXT,
    status TEXT DEFAULT 'ONLINE' CHECK(status IN ('ONLINE', 'OFFLINE', 'STANDBY')),
    signal_rssi INTEGER DEFAULT -65,
    firmware_version TEXT DEFAULT 'v2.4.1-esp32',
    nominal_power_w REAL DEFAULT 5000.0,
    load_category TEXT DEFAULT 'General',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

CREATE_READINGS_TABLE = """
CREATE TABLE IF NOT EXISTS readings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    device_id TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    voltage REAL NOT NULL,
    current REAL NOT NULL,
    active_power REAL NOT NULL,
    apparent_power REAL NOT NULL,
    energy_kwh REAL NOT NULL,
    frequency REAL NOT NULL,
    power_factor REAL NOT NULL,
    is_simulated INTEGER DEFAULT 1 CHECK(is_simulated IN (0, 1)),
    transmission_protocol TEXT DEFAULT '5G_URLLC',
    latency_ms REAL DEFAULT 2.8,
    packet_loss INTEGER DEFAULT 0 CHECK(packet_loss IN (0, 1)),
    FOREIGN KEY(device_id) REFERENCES devices(device_id) ON DELETE CASCADE,
    UNIQUE(device_id, timestamp)
);
"""

CREATE_ANOMALIES_TABLE = """
CREATE TABLE IF NOT EXISTS anomalies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    device_id TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    metric TEXT NOT NULL,
    detected_value REAL NOT NULL,
    expected_range TEXT NOT NULL,
    severity TEXT NOT NULL CHECK(severity IN ('LOW', 'MEDIUM', 'CRITICAL')),
    detection_method TEXT NOT NULL CHECK(detection_method IN ('Isolation Forest', 'Z-Score', 'IQR Rule', 'Electrical Limit')),
    reason TEXT NOT NULL,
    resolved INTEGER DEFAULT 0 CHECK(resolved IN (0, 1)),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(device_id) REFERENCES devices(device_id) ON DELETE CASCADE
);
"""

CREATE_PREDICTIONS_TABLE = """
CREATE TABLE IF NOT EXISTS predictions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    model_name TEXT NOT NULL,
    horizon TEXT NOT NULL,
    target_date TEXT NOT NULL,
    predicted_energy_kwh REAL NOT NULL,
    lower_bound_kwh REAL,
    upper_bound_kwh REAL,
    actual_energy_kwh REAL,
    mae REAL,
    rmse REAL,
    r2_score REAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

CREATE_MQTT_LOGS_TABLE = """
CREATE TABLE IF NOT EXISTS mqtt_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    topic TEXT NOT NULL,
    payload TEXT NOT NULL,
    qos INTEGER DEFAULT 1,
    latency_ms REAL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

CREATE_INDEXES = """
CREATE INDEX IF NOT EXISTS idx_readings_device_time ON readings(device_id, timestamp);
CREATE INDEX IF NOT EXISTS idx_readings_timestamp ON readings(timestamp);
CREATE INDEX IF NOT EXISTS idx_anomalies_time ON anomalies(timestamp);
CREATE INDEX IF NOT EXISTS idx_devices_building ON devices(building);
"""
