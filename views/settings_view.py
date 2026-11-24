"""
VoltSense 5G - View: Settings and About
System configuration, database maintenance, and academic engineering project documentation.
"""
import streamlit as st
import os
from pathlib import Path

from config import (
    APP_NAME,
    APP_TAGLINE,
    APP_VERSION,
    PROJECT_TITLE,
    DEFAULT_TARIFF_INR_PER_KWH,
    PEAK_TARIFF_INR_PER_KWH,
    OFF_PEAK_TARIFF_INR_PER_KWH,
    DB_PATH,
    SAMPLE_CSV_PATH
)
from database.database import DatabaseManager
from data.generate_sample_data import seed_database_and_save_csv


def render_settings_view(db: DatabaseManager):
    """Renders Settings and About documentation."""
    st.markdown("""
        <div class="voltsense-header">
            <div class="voltsense-title-box">
                <h1>Settings & Academic Project Documentation</h1>
                <div class="voltsense-tagline">Configuration Management, Database Maintenance, and Engineering Capstone Reference</div>
            </div>
            <div>
                <span class="badge-hw-ready">v2.4 Production</span>
            </div>
        </div>
    """, unsafe_allow_html=True)

    tab_config, tab_db, tab_about = st.tabs([
        "⚙️ Tariff & System Settings",
        "🗄️ Database & Sample Data Maintenance",
        "📖 Academic Project & Architecture Specification"
    ])

    # --------------------------------------------------------------------------
    # TAB 1: Tariff & System Settings
    # --------------------------------------------------------------------------
    with tab_config:
        st.markdown("<div class='section-header-box'><h2>Tariff & Financial Rate Configuration</h2><p>Adjust baseline and Time-of-Day (ToD) electricity billing parameters</p></div>", unsafe_allow_html=True)

        with st.form("settings_tariff_form"):
            tc1, tc2, tc3 = st.columns(3)
            with tc1:
                flat_rate = st.number_input("Standard Flat Tariff (₹/kWh):", value=DEFAULT_TARIFF_INR_PER_KWH, min_value=1.0, max_value=40.0, step=0.25)
            with tc2:
                peak_rate = st.number_input("Peak Hours Tariff (₹/kWh):", value=PEAK_TARIFF_INR_PER_KWH, min_value=1.0, max_value=50.0, step=0.25)
            with tc3:
                off_peak_rate = st.number_input("Off-Peak Tariff (₹/kWh):", value=OFF_PEAK_TARIFF_INR_PER_KWH, min_value=1.0, max_value=30.0, step=0.25)

            st.write("<b>Time-of-Day Window Definitions:</b> Peak Hours: 09:00 - 13:00 & 18:00 - 22:00 | Off-Peak: 23:00 - 06:00", unsafe_allow_html=True)
            save_tariff = st.form_submit_button("Save Tariff Settings", type="primary")
            if save_tariff:
                st.session_state["global_tariff"] = flat_rate
                st.success("Tariff settings updated successfully for active session!")

    # --------------------------------------------------------------------------
    # TAB 2: Database & Sample Data Maintenance
    # --------------------------------------------------------------------------
    with tab_db:
        st.markdown("<div class='section-header-box'><h2>SQLite Database Administration</h2><p>Manage local persistent storage, check storage volume, and re-seed sample data</p></div>", unsafe_allow_html=True)

        db_size_mb = 0.0
        if DB_PATH.exists():
            db_size_mb = os.path.getsize(DB_PATH) / (1024 * 1024)

        readings_count = db.get_total_readings_count()
        devices_count = len(db.get_devices())
        anomalies_count = len(db.get_anomalies(limit=10000))

        dc1, dc2, dc3, dc4 = st.columns(4)
        dc1.metric("Database Storage File", f"{db_size_mb:.2f} MB")
        dc2.metric("Total Stored Readings", f"{readings_count:,} rows")
        dc3.metric("Registered Devices", f"{devices_count} nodes")
        dc4.metric("Logged Anomalies", f"{anomalies_count} events")

        st.markdown("<br/>", unsafe_allow_html=True)
        st.write("<b>Database Maintenance Actions:</b>", unsafe_allow_html=True)

        act_c1, act_c2 = st.columns(2)
        with act_c1:
            if st.button("🔄 Re-Seed 30-Day Campus Benchmark Dataset", use_container_width=True):
                with st.spinner("Generating fresh 30-day realistic sample telemetry and populating SQLite..."):
                    db.clear_readings()
                    seed_database_and_save_csv()
                    st.success("Database re-seeded successfully with 4,320 physics-compliant telemetry records!")
                    st.rerun()

        with act_c2:
            if st.button("🗑️ Clear All Telemetry & Anomaly Records", use_container_width=True, type="secondary"):
                db.clear_readings()
                st.warning("Database cleared! Telemetry count is now 0.")
                st.rerun()

    # --------------------------------------------------------------------------
    # TAB 3: Academic Project & Architecture Specification
    # --------------------------------------------------------------------------
    with tab_about:
        st.markdown(f"""
            <div class='section-header-box'>
                <h2>{PROJECT_TITLE}</h2>
                <p><b>Application Name:</b> {APP_NAME} | <b>Version:</b> {APP_VERSION}</p>
                <p><i>{APP_TAGLINE}</i></p>
            </div>
        """, unsafe_allow_html=True)

        st.markdown("""
            ### 🎓 Academic Engineering Defense Guide (BTech / BE Capstone)
            
            #### 1. System Architecture Overview
            The VoltSense 5G platform is organized strictly into **three major functional modules**:
            - **Module 1: IoT Data Acquisition and 5G Communication**
              - High-precision telemetry collection: Voltage ($V$), Current ($I$), Active Real Power ($P$), Apparent Power ($S$), Energy ($kWh$), Frequency ($f$), and Power Factor ($\cos\varphi$).
              - 3GPP Rel-16 5G New Radio network slicing emulation (URLLC, eMBB, mMTC) with sub-4ms latency modeling.
              - Live MQTT ingestion bridge for ESP32 / PZEM-004T smart meters.
              - Persistent SQLite local database with index optimization.
            - **Module 2: Electricity Consumption Analysis and Anomaly Detection**
              - Multi-temporal aggregations: hourly diurnal cycles, daily kWh bar profiles, weekly WoW shifts, and monthly usage.
              - Peak demand tracking and Load Factor evaluation.
              - Tariff cost computation: Standard Flat vs Time-of-Day (ToD) differential billing.
              - Dual-engine anomaly detection: Rolling statistical Z-Score / IQR rules + Scikit-learn unsupervised Isolation Forest.
            - **Module 3: Energy Consumption Prediction and Analytics Dashboard**
              - Comparative machine learning forecasting: Linear Regression, Random Forest Regressor, and ARIMA time series.
              - Strictly chronological 80/20 train/test evaluation preventing future-data leakage.
              - Quantitative evaluation using MAE, RMSE, and $R^2$ scores with automatic best-performer tagging.
              - Multi-horizon forecasting (24h, 7d, 30d) with 95% uncertainty intervals and peak demand projection.
              - Automated ReportLab executive PDF audit generation and CSV exports.

            #### 2. Key Academic Equations & Physical Laws
            - **Single-Phase Apparent Power:** $S = V \\times I\\text{ (VA)}$
            - **Active Useful Power:** $P = V \\times I \\times \\cos\\varphi\\text{ (W)}$
            - **Accumulated Electrical Energy:** $E(t) = E(t-1) + \\frac{P(t) \\times \\Delta t}{1000 \\times 3600}\\text{ (kWh)}$
            - **Electrical Load Factor:** $\\text{Load Factor} = \\frac{\\text{Average Load (kW)}}{\\text{Peak Demand (kW)}}$
            - **Energy Cost:** $\\text{Cost (₹)} = \\text{Energy (kWh)} \\times \\text{Tariff (₹/kWh)}$
            - **Grid Emission Footprint:** $\\text{CO}_2\\text{ (kg)} = \\text{Energy (kWh)} \\times 0.82\\text{ kg CO}_2/\\text{kWh}$

            #### 3. Why 5G URLLC for Smart Grid IoT?
            Legacy 4G LTE suffers from variable latencies (40-100ms) and unpredictable jitter, making it suboptimal for automated microgrid load-shedding and rapid fault isolation. 5G Ultra-Reliable Low-Latency Communication (URLLC) guarantees **sub-5 millisecond latency** with **99.999% reliability**, enabling sub-cycle telemetry feedback and millisecond-level anomaly intervention.
        """)
