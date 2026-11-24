# VoltSense 5G
### IoT and 5G-Based Electricity Consumption Monitoring and Prediction
> **Tagline:** Intelligent Energy Monitoring, Real-Time Insights and Predictive Consumption Analytics.  
> **Target:** Final-Year B.Tech / B.E. Electrical & Computer Engineering Capstone Project & Enterprise IoT SaaS Platform.

---

## 🌟 Executive Summary

**VoltSense 5G** is a full-stack, enterprise-grade industrial IoT energy intelligence platform that collects electrical telemetry from distributed smart meters, models low-latency 5G New Radio (NR) communication layers, computes real-time power parameters, identifies abnormal electrical spikes, and forecasts future energy consumption using comparative Machine Learning models (**Linear Regression**, **Random Forest Regressor**, and **ARIMA Time Series**).

The application is structured into **exactly three major functional modules** designed for academic defensibility and commercial SaaS energy management.

---

## 🏗️ Exactly Three Major Modules

```
VoltSense 5G Architecture
│
├── MODULE 1: IoT Data Acquisition & 5G Communication
│   ├── IoT Smart Meter Registry & Health Monitoring
│   ├── Electrical Parameter Acquisition (V, I, P, S, kWh, f, cos φ)
│   ├── 3GPP Rel-16 5G Slicing Simulation (URLLC, eMBB, mMTC)
│   ├── Live MQTT Broker Telemetry Ingestion (paho-mqtt)
│   └── ESP32 / PZEM-004T Hardware Firmware & Schematics
│
├── MODULE 2: Electricity Consumption Analysis & Anomaly Detection
│   ├── Real-Time Parameter Waveforms & Gauges
│   ├── Historical Consumption (Hourly Diurnal, Daily, Weekly WoW, Monthly)
│   ├── Peak Demand Tracking & Load Factor Computation
│   ├── Dynamic Electricity Tariff Billing (Flat vs Time-of-Day Surcharge)
│   └── Dual-Engine Anomaly Detection (Statistical Z-Score/IQR + Isolation Forest)
│
└── MODULE 3: Energy Consumption Prediction & Analytics Dashboard
    ├── Multi-Model Forecasting (Linear Regression, Random Forest, ARIMA)
    ├── Chronological Train/Test Benchmarking (MAE, RMSE, R² Score)
    ├── Multi-Horizon Forecasts (24h, 7d, 30d) with 95% Uncertainty Intervals
    ├── Executive Decision-Support Analytics (Peak Shaving & Carbon Footprint)
    └── Automated Audit PDF Report (ReportLab) & CSV Telemetry Exports
```

---

## 📐 Mathematical & Electrical Foundations

All calculations strictly adhere to **IEEE 1459-2010 AC Power Standards**:

1. **Apparent Power ($S$):**
   $$S = V \times I \quad (\text{VA})$$
2. **Active Real Power ($P$):**
   $$P = V \times I \times \cos\varphi \quad (\text{Watts, W})$$
3. **Reactive Power ($Q$):**
   $$Q = \sqrt{S^2 - P^2} \quad (\text{VAR})$$
4. **Energy Accumulation ($E$):**
   $$E(t) = E(t-1) + \left(\frac{P(t)}{1000} \times \frac{\Delta t}{3600}\right) \quad (\text{kWh})$$
5. **Electrical Load Factor:**
   $$\text{Load Factor} = \frac{\text{Average Load (kW)}}{\text{Peak Demand (kW)}} \quad (0.0 \text{ to } 1.0)$$
6. **Energy Cost Estimation:**
   $$\text{Cost (₹)} = \text{Total Consumption (kWh)} \times \text{Tariff (₹/kWh)}$$
7. **Carbon Emissions (Scope 2):**
   $$\text{CO}_2\text{ (kg)} = \text{Energy (kWh)} \times 0.82\text{ kg CO}_2\text{/kWh}$$

---

## 📡 5G Communication Layer (3GPP Release-16)

VoltSense 5G models 3GPP Rel-16 Network Slicing profiles:
- **5G URLLC (Ultra-Reliable Low-Latency Communication):** Sub-4ms latency with 99.999% reliability for mission-critical substation load shedding.
- **5G eMBB (Enhanced Mobile Broadband):** 10-22ms latency for high-bandwidth harmonic waveform transmission.
- **5G mMTC (massive Machine-Type Communications):** Low-power, high-density sensor telemetry.
- **Legacy 4G LTE Fallback:** 40-90ms cellular fallback.

> **Academic Notice:** Network metrics are simulated via 3GPP Release-16 statistical channel models. Physical MQTT connectivity is supported concurrently for hardware gateways.

---

## 🤖 Machine Learning Predictive Engine

VoltSense 5G implements three distinct supervised and time-series algorithms:
1. **Linear Regression:** Captures calendar periodicities, cyclic diurnal hours ($\sin/\cos$), and lagged energy terms.
2. **Random Forest Regressor:** Captures non-linear equipment interactions, peak-hour surges, and weekend drops (`n_estimators=100, max_depth=12`).
3. **ARIMA Time Series ($p=1, d=1, q=1$):** AutoRegressive Integrated Moving Average for univariate time-series projection.

### 🛡️ Strict Chronological Validation (Zero Data Leakage)
To ensure rigorous academic standards, models are trained on the **first 80% chronological observations** and evaluated on the **final 20% unseen test horizon**. Random shuffling is forbidden to prevent temporal data leakage.
- **MAE:** Mean Absolute Error (kWh)
- **RMSE:** Root Mean Squared Error (kWh)
- **$R^2$ Score:** Coefficient of determination (Goodness of Fit)

---

## 🛠️ Hardware Integration (ESP32 + PZEM-004T)

The platform provides complete C++ Arduino source code (`modules/iot_acquisition.py`) for:
- **Microcontroller:** ESP32-WROOM-32D (Dual-Core 240MHz).
- **Sensor:** PZEM-004T v3.0 AC Energy Meter (80-260V, 0-100A).
- **Protocol:** MQTT over 5G Cellular Gateway or Wi-Fi.
- **Payload:** JSON with hardware telemetry and RSSI signal.

---

## 🚀 Quickstart & Execution Guide

### 1. Requirements
Ensure Python 3.10+ is installed.

### 2. Install Dependencies
```bash
cd c:\smilewell\VoltSense-5G
pip install -r requirements.txt
```

### 3. Generate Benchmark Dataset & Seed SQLite
```bash
python data/generate_sample_data.py
```

### 4. Run the Streamlit Application
From the `VoltSense-5G` directory:
```bash
streamlit run app.py
```
Or directly from the workspace root:
```bash
streamlit run app.py
```

### 5. Execute Automated Test Suite
```bash
python -m pytest tests/ -v
```
All 19 test cases across calculations, database operations, anomaly detection, and forecasting will execute and validate.

---

## 📊 Project Deliverables Summary
- **SaaS Web App:** High-end dark theme (`#101827`, `#2563EB`, `#06B6D4`, `#10B981`).
- **Database:** SQLite with WAL mode, foreign keys, and indexes (`data/voltsense.db`).
- **Reports:** Automated ReportLab multi-page executive audit PDF and CSV downloads.
- **Hardware Docs:** Complete ESP32 wiring and Arduino code.
