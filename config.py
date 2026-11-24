"""
VoltSense 5G - Global Configuration and System Constants
Intelligent Energy Monitoring, Real-Time Insights and Predictive Consumption Analytics.
"""
from pathlib import Path

# Application Metadata
APP_NAME = "VoltSense 5G"
APP_TAGLINE = "Intelligent Energy Monitoring, Real-Time Insights and Predictive Consumption Analytics"
APP_VERSION = "2.4.0 (Enterprise IoT Edition)"
PROJECT_TITLE = "IoT and 5G-Based Electricity Consumption Monitoring and Prediction"

# Base Paths
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
ASSETS_DIR = BASE_DIR / "assets"
DB_PATH = DATA_DIR / "voltsense.db"
SAMPLE_CSV_PATH = DATA_DIR / "sample_energy_data.csv"

# Electrical Nominal Specifications (Single-Phase AC standard)
NOMINAL_VOLTAGE_V = 230.0
VOLTAGE_MIN_NORMAL_V = 205.0
VOLTAGE_MAX_NORMAL_V = 250.0
VOLTAGE_CRITICAL_LOW_V = 185.0
VOLTAGE_CRITICAL_HIGH_V = 260.0

NOMINAL_FREQUENCY_HZ = 50.0
FREQUENCY_TOLERANCE_HZ = 0.5  # 49.5 - 50.5 Hz normal grid operating band

TARGET_POWER_FACTOR = 0.92
MIN_ACCEPTABLE_POWER_FACTOR = 0.85

# Default Financial & Tariff Settings (in Indian Rupees ₹)
DEFAULT_TARIFF_INR_PER_KWH = 7.50
PEAK_TARIFF_INR_PER_KWH = 10.50
OFF_PEAK_TARIFF_INR_PER_KWH = 5.20

# Time-of-Day (ToD) Peak Hours: 09:00 - 13:00 and 18:00 - 22:00
PEAK_HOURS = {9, 10, 11, 12, 18, 19, 20, 21}
OFF_PEAK_HOURS = {23, 0, 1, 2, 3, 4, 5}

# 5G Communication Layer Simulation Profiles (3GPP Rel-16 Specifications)
FIVE_G_PROFILES = {
    "URLLC": {
        "name": "5G URLLC (Ultra-Reliable Low-Latency Communication)",
        "description": "Sub-millisecond transmission for mission-critical substation monitoring",
        "latency_min_ms": 1.5,
        "latency_max_ms": 4.5,
        "jitter_ms": 0.4,
        "packet_loss_rate": 0.00001,
        "bandwidth_kbps": 10000,
        "slice_id": "SST-1 / SD-000001"
    },
    "eMBB": {
        "name": "5G eMBB (Enhanced Mobile Broadband)",
        "description": "High-throughput telemetry for detailed harmonic waveform streaming",
        "latency_min_ms": 10.0,
        "latency_max_ms": 22.0,
        "jitter_ms": 1.8,
        "packet_loss_rate": 0.001,
        "bandwidth_kbps": 100000,
        "slice_id": "SST-2 / SD-000002"
    },
    "mMTC": {
        "name": "5G mMTC (massive Machine-Type Communications)",
        "description": "High device density energy-efficient telemetry (NB-IoT / eMTC over 5G Core)",
        "latency_min_ms": 45.0,
        "latency_max_ms": 90.0,
        "jitter_ms": 7.5,
        "packet_loss_rate": 0.01,
        "bandwidth_kbps": 250,
        "slice_id": "SST-3 / SD-000003"
    },
    "4G_FALLBACK": {
        "name": "Legacy 4G LTE Fallback",
        "description": "Cellular fallback when 5G New Radio (NR) carrier aggregation is unavailable",
        "latency_min_ms": 40.0,
        "latency_max_ms": 110.0,
        "jitter_ms": 15.0,
        "packet_loss_rate": 0.02,
        "bandwidth_kbps": 5000,
        "slice_id": "LTE-Cat-4"
    }
}

# Campus Monitoring Sites & Devices
DEFAULT_CAMPUS_DEVICES = [
    {
        "device_id": "DEV_BLD_A_01",
        "device_name": "Main Admin Substation",
        "building": "College Building A",
        "room": "Administrative Office",
        "ip_address": "192.168.10.101",
        "mac_address": "84:F3:EB:A1:01:10",
        "nominal_power_w": 8500.0,
        "load_category": "Institutional / Office"
    },
    {
        "device_id": "DEV_BLD_A_02",
        "device_name": "Faculty Wing Smart Meter",
        "building": "College Building A",
        "room": "Faculty Chambers",
        "ip_address": "192.168.10.102",
        "mac_address": "84:F3:EB:A1:01:20",
        "nominal_power_w": 4200.0,
        "load_category": "Lighting & HVAC"
    },
    {
        "device_id": "DEV_BLD_B_01",
        "device_name": "Computer Lab 101 Meter",
        "building": "College Building B",
        "room": "Computer Laboratory",
        "ip_address": "192.168.20.101",
        "mac_address": "84:F3:EB:B2:01:11",
        "nominal_power_w": 14500.0,
        "load_category": "High Non-Linear Computing"
    },
    {
        "device_id": "DEV_BLD_B_02",
        "device_name": "AI Cluster & Server Room",
        "building": "College Building B",
        "room": "Computer Laboratory",
        "ip_address": "192.168.20.102",
        "mac_address": "84:F3:EB:B2:01:22",
        "nominal_power_w": 18500.0,
        "load_category": "24/7 Server Load"
    },
    {
        "device_id": "DEV_CLS_01",
        "device_name": "Lecture Hall Complex Meter",
        "building": "Classroom Block",
        "room": "Rooms 201-208",
        "ip_address": "192.168.30.101",
        "mac_address": "84:F3:EB:C3:01:05",
        "nominal_power_w": 9800.0,
        "load_category": "Intermittent Academic Load"
    },
    {
        "device_id": "DEV_LIB_01",
        "device_name": "Central Library Energy Node",
        "building": "Library",
        "room": "Main Reading Hall",
        "ip_address": "192.168.40.101",
        "mac_address": "84:F3:EB:D4:01:09",
        "nominal_power_w": 6200.0,
        "load_category": "HVAC & Continuous Lighting"
    }
]

# SaaS UI Brand Colors
COLORS = {
    "navy_deep": "#101827",
    "navy_surface": "#0F172A",
    "slate_card": "#1E293B",
    "slate_border": "#334155",
    "slate_muted": "#64748B",
    "text_light": "#F8FAFC",
    "electric_blue": "#2563EB",
    "cyan": "#06B6D4",
    "emerald": "#10B981",
    "amber": "#F59E0B",
    "rose": "#EF4444",
    "purple": "#8B5CF6"
}
