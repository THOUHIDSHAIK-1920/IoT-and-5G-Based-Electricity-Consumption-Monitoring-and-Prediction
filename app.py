"""
VoltSense 5G - Main Streamlit Web Application
IoT and 5G-Based Electricity Consumption Monitoring and Prediction
Intelligent Energy Monitoring, Real-Time Insights and Predictive Consumption Analytics.
"""
import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st

# Streamlit Page Config
st.set_page_config(
    page_title="VoltSense 5G - IoT Energy Platform",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Load Custom CSS Theme
from config import ASSETS_DIR, APP_NAME, APP_TAGLINE, DEFAULT_TARIFF_INR_PER_KWH
css_file = ASSETS_DIR / "styles.css"
if css_file.exists():
    with open(css_file, "r", encoding="utf-8") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# Initialize Core Services (cached in session_state)
from database.database import DatabaseManager
from modules.iot_acquisition import SensorSimulator
from modules.communication_5g import Communication5GManager
from modules.consumption_analysis import ConsumptionAnalyzer
from modules.anomaly_detection import AnomalyDetector
from modules.energy_forecasting import EnergyForecastingEngine

if "db" not in st.session_state:
    st.session_state["db"] = DatabaseManager()
    # Check if database has records; if not, seed initial data
    if st.session_state["db"].get_total_readings_count() == 0:
        from data.generate_sample_data import seed_database_and_save_csv
        seed_database_and_save_csv()

if "sim" not in st.session_state:
    st.session_state["sim"] = SensorSimulator(st.session_state["db"])

if "comm" not in st.session_state:
    st.session_state["comm"] = Communication5GManager(st.session_state["db"])

if "analyzer" not in st.session_state:
    st.session_state["analyzer"] = ConsumptionAnalyzer(st.session_state["db"])

if "detector" not in st.session_state:
    st.session_state["detector"] = AnomalyDetector(st.session_state["db"])

if "forecaster" not in st.session_state:
    st.session_state["forecaster"] = EnergyForecastingEngine(st.session_state["db"])

db = st.session_state["db"]
sim = st.session_state["sim"]
comm = st.session_state["comm"]
analyzer = st.session_state["analyzer"]
detector = st.session_state["detector"]
forecaster = st.session_state["forecaster"]

# Views
from views.dashboard_view import render_dashboard_view
from views.module1_view import render_module1_view
from views.module2_view import render_module2_view
from views.module3_view import render_module3_view
from views.reports_view import render_reports_view
from views.settings_view import render_settings_view

# ==============================================================================
# Sidebar Navigation & Operational Status
# ==============================================================================
with st.sidebar:
    st.markdown("""
        <div style="padding: 10px 0 16px 0; border-bottom: 1px solid #334155; margin-bottom: 14px;">
            <div style="display:flex;align-items:center;gap:10px;">
                <span style="font-size:2rem;">⚡</span>
                <div>
                    <h2 style="margin:0;font-size:1.45rem;font-weight:800;background:linear-gradient(90deg,#38BDF8,#818CF8);-webkit-background-clip:text;-webkit-text-fill-color:transparent;">VoltSense 5G</h2>
                    <span style="font-size:0.75rem;color:#94A3B8;letter-spacing:0.04em;">SMART GRID IoT PLATFORM</span>
                </div>
            </div>
        </div>
    """, unsafe_allow_html=True)

    nav_options = [
        "1. Dashboard Overview",
        "2. Module 1 – IoT Data Acquisition & 5G",
        "3. Module 2 – Consumption Analysis & Anomalies",
        "4. Module 3 – ML Prediction & Analytics",
        "5. Reports and Export",
        "6. Settings and About"
    ]

    selected_nav = st.radio(
        "Navigation Menu:",
        options=nav_options,
        index=0,
        label_visibility="collapsed"
    )

    st.markdown("<br/>", unsafe_allow_html=True)
    st.markdown("""
        <div style="background:#0F172A;border:1px solid #334155;border-radius:8px;padding:12px;margin-bottom:14px;font-size:0.82rem;color:#CBD5E1;">
            <div style="font-weight:700;color:#F8FAFC;margin-bottom:6px;display:flex;justify-content:space-between;">
                <span>📡 Network Link</span>
                <span style="color:#10B981;">● Online</span>
            </div>
            <div><b>5G Slice:</b> URLLC (Rel-16)</div>
            <div><b>Simulated Latency:</b> ~2.8 ms</div>
            <div><b>Protocol:</b> MQTT / TCP / 5G NR</div>
        </div>
    """, unsafe_allow_html=True)

    # Global Quick Simulation Pulse Button
    if st.button("⚡ Live Telemetry Step", use_container_width=True):
        new_ticks = sim.simulate_tick_for_all_devices()
        st.toast(f"Synchronized {len(new_ticks)} campus meters via 5G NR!", icon="⚡")
        st.rerun()

    st.markdown("""
        <div style="font-size:0.75rem;color:#64748B;text-align:center;margin-top:20px;padding-top:12px;border-top:1px solid #1E293B;">
            <b>VoltSense 5G</b> v2.4.0<br/>
            BTech Engineering Capstone Project
        </div>
    """, unsafe_allow_html=True)

# ==============================================================================
# Route to Selected Module View
# ==============================================================================
if selected_nav == "1. Dashboard Overview":
    render_dashboard_view(db, sim, analyzer)
elif selected_nav == "2. Module 1 – IoT Data Acquisition & 5G":
    render_module1_view(db, sim, comm)
elif selected_nav == "3. Module 2 – Consumption Analysis & Anomalies":
    render_module2_view(db, analyzer, detector)
elif selected_nav == "4. Module 3 – ML Prediction & Analytics":
    render_module3_view(db, forecaster)
elif selected_nav == "5. Reports and Export":
    render_reports_view(db, analyzer, detector, forecaster)
elif selected_nav == "6. Settings and About":
    render_settings_view(db)
