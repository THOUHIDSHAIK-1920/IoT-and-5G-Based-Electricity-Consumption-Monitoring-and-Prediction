"""
VoltSense 5G - View: Executive Dashboard Overview
High-level operational overview, real-time electrical telemetry, building breakdowns, and quick actions.
"""
import streamlit as st
import pandas as pd
from typing import Dict, Any

from config import COLORS, DEFAULT_TARIFF_INR_PER_KWH
from database.database import DatabaseManager
from modules.iot_acquisition import SensorSimulator
from modules.consumption_analysis import ConsumptionAnalyzer
from utils.charts import (
    create_gauge_chart,
    create_realtime_power_chart,
    create_device_breakdown_pie
)


def render_dashboard_view(db: DatabaseManager, sim: SensorSimulator, analyzer: ConsumptionAnalyzer):
    """Renders the executive dashboard overview."""
    st.markdown("""
        <div class="voltsense-header">
            <div class="voltsense-title-box">
                <h1>VoltSense 5G</h1>
                <div class="voltsense-tagline">Intelligent Energy Monitoring, Real-Time Insights and Predictive Consumption Analytics</div>
            </div>
            <div>
                <span class="badge-hw-ready"><span class="status-dot status-dot-online"></span> 5G URLLC Active</span>
            </div>
        </div>
    """, unsafe_allow_html=True)

    # Simulation Notice Banner
    st.markdown("""
        <div class="simulation-disclaimer">
            <span>ℹ️ <b>Academic Demonstration Mode:</b> Running on physics-compliant 3GPP Rel-16 simulated 5G data. Physical hardware interface (ESP32 / PZEM-004T) is architected and ready for live MQTT ingestion.</span>
        </div>
    """, unsafe_allow_html=True)

    # Top Controls Bar
    col_ctrl1, col_ctrl2, col_ctrl3 = st.columns([2, 2, 2])
    with col_ctrl1:
        devices = db.get_devices()
        dev_options = ["ALL"] + [d["device_id"] for d in devices]
        selected_dev = st.selectbox(
            "Filter Monitoring Node:", 
            options=dev_options, 
            format_func=lambda x: "All Campus Nodes (Aggregate)" if x == "ALL" else f"{x} - {next((d['device_name'] for d in devices if d['device_id'] == x), x)}"
        )
    with col_ctrl2:
        tariff_val = st.number_input("Electricity Tariff (₹/kWh):", min_value=1.0, max_value=50.0, value=DEFAULT_TARIFF_INR_PER_KWH, step=0.25)
    with col_ctrl3:
        st.write("")
        st.write("")
        if st.button("⚡ Inject Live 5G Telemetry Tick", use_container_width=True, type="primary"):
            new_records = sim.simulate_tick_for_all_devices()
            st.toast(f"Generated and transmitted {len(new_records)} sensor packets via 5G URLLC slice!", icon="📡")

    # Fetch live and aggregated metrics
    live_metrics = analyzer.get_realtime_metrics(selected_dev)
    hist_analysis = analyzer.analyze_historical_consumption(selected_dev, tariff_rate=tariff_val)
    anomalies_df = db.get_anomalies(device_id=selected_dev, limit=10)

    # KPI Top Metrics Cards (6-column responsive grid)
    k1, k2, k3, k4, k5, k6 = st.columns(6)
    with k1:
        st.markdown(f"""
            <div class="kpi-card">
                <div class="kpi-title">⚡ Active Power</div>
                <div class="kpi-value">{live_metrics['active_power']:,.1f} <span style="font-size:0.9rem;color:#94A3B8">W</span></div>
                <div class="kpi-subtext">Apparent: {live_metrics['apparent_power']:,.1f} VA</div>
            </div>
        """, unsafe_allow_html=True)
    with k2:
        st.markdown(f"""
            <div class="kpi-card">
                <div class="kpi-title">🔋 Total Energy</div>
                <div class="kpi-value">{hist_analysis['total_kwh']:,.1f} <span style="font-size:0.9rem;color:#94A3B8">kWh</span></div>
                <div class="kpi-subtext">Campus Aggregate</div>
            </div>
        """, unsafe_allow_html=True)
    with k3:
        st.markdown(f"""
            <div class="kpi-card">
                <div class="kpi-title">💰 Est. Energy Bill</div>
                <div class="kpi-value">₹{hist_analysis['total_cost_inr']:,.2f}</div>
                <div class="kpi-subtext">@ ₹{tariff_val}/kWh</div>
            </div>
        """, unsafe_allow_html=True)
    with k4:
        st.markdown(f"""
            <div class="kpi-card">
                <div class="kpi-title">📈 Peak Demand</div>
                <div class="kpi-value">{hist_analysis['peak_demand_w']:,.0f} <span style="font-size:0.9rem;color:#94A3B8">W</span></div>
                <div class="kpi-subtext">Load Factor: {hist_analysis['load_factor']}</div>
            </div>
        """, unsafe_allow_html=True)
    with k5:
        anom_count = len(anomalies_df)
        badge_cls = "kpi-badge-danger" if anom_count > 0 else "kpi-badge-positive"
        st.markdown(f"""
            <div class="kpi-card">
                <div class="kpi-title">⚠️ Flagged Outliers</div>
                <div class="kpi-value">{anom_count} <span class="{badge_cls}">Alerts</span></div>
                <div class="kpi-subtext">Real-time scan</div>
            </div>
        """, unsafe_allow_html=True)
    with k6:
        active_cnt = len([d for d in devices if d.get("status") == "ONLINE"])
        st.markdown(f"""
            <div class="kpi-card">
                <div class="kpi-title">📡 5G Smart Meters</div>
                <div class="kpi-value">{active_cnt}/{len(devices)} <span style="font-size:0.9rem;color:#10B981">Online</span></div>
                <div class="kpi-subtext">Latency ~2.8 ms (URLLC)</div>
            </div>
        """, unsafe_allow_html=True)

    st.markdown("<br/>", unsafe_allow_html=True)

    # Middle Row: Real-Time Power Telemetry Chart & Instantaneous Gauges
    col_chart, col_gauges = st.columns([3, 2])

    with col_chart:
        st.markdown("<div class='section-header-box'><h2>Live Electrical Power Stream</h2><p>Synchronous comparison of Active Real Power (W) vs Apparent Complex Power (VA)</p></div>", unsafe_allow_html=True)
        readings_df = db.get_readings(device_id=selected_dev, limit=80, order="DESC")
        if not readings_df.empty:
            readings_df = readings_df.sort_values("timestamp")
            fig_power = create_realtime_power_chart(readings_df)
            st.plotly_chart(fig_power, use_container_width=True)
        else:
            st.info("No telemetry readings available in current selection window.")

    with col_gauges:
        st.markdown("<div class='section-header-box'><h2>Parameter Health Gauges</h2><p>Instantaneous electrical parameters from active monitoring nodes</p></div>", unsafe_allow_html=True)
        g_c1, g_c2 = st.columns(2)
        with g_c1:
            fig_v = create_gauge_chart(
                value=live_metrics["voltage"],
                title="Grid Voltage",
                min_val=180.0,
                max_val=270.0,
                unit="V",
                warning_val=245.0,
                danger_val=255.0,
                color_bar="#38BDF8"
            )
            st.plotly_chart(fig_v, use_container_width=True)
        with g_c2:
            fig_i = create_gauge_chart(
                value=live_metrics["current"],
                title="Current Load",
                min_val=0.0,
                max_val=120.0,
                unit="A",
                warning_val=80.0,
                danger_val=100.0,
                color_bar="#F59E0B"
            )
            st.plotly_chart(fig_i, use_container_width=True)

        g_c3, g_c4 = st.columns(2)
        with g_c3:
            fig_f = create_gauge_chart(
                value=live_metrics["frequency"],
                title="Frequency",
                min_val=48.0,
                max_val=52.0,
                unit="Hz",
                warning_val=50.5,
                danger_val=51.0,
                color_bar="#10B981"
            )
            st.plotly_chart(fig_f, use_container_width=True)
        with g_c4:
            fig_pf = create_gauge_chart(
                value=live_metrics["power_factor"],
                title="Power Factor",
                min_val=0.5,
                max_val=1.0,
                unit="cos φ",
                warning_val=0.88,
                danger_val=0.80,
                color_bar="#A855F7"
            )
            st.plotly_chart(fig_pf, use_container_width=True)

    # Bottom Row: Device Breakdown & Recent Anomaly Alerts
    col_bottom_left, col_bottom_right = st.columns([1, 1])

    with col_bottom_left:
        st.markdown("<div class='section-header-box'><h2>Campus Building Load Distribution</h2><p>Share of total electrical energy consumed by monitoring location</p></div>", unsafe_allow_html=True)
        all_readings = db.get_readings(order="ASC")
        if not all_readings.empty:
            fig_pie = create_device_breakdown_pie(all_readings)
            st.plotly_chart(fig_pie, use_container_width=True)

    with col_bottom_right:
        st.markdown("<div class='section-header-box'><h2>Recent Anomaly Incidents</h2><p>Latest flagged grid disturbances and abnormal consumption spikes</p></div>", unsafe_allow_html=True)
        if not anomalies_df.empty:
            anom_view = anomalies_df[["timestamp", "device_id", "metric", "detected_value", "severity", "reason"]].head(5)
            st.dataframe(
                anom_view,
                column_config={
                    "timestamp": st.column_config.DatetimeColumn("Timestamp", format="YYYY-MM-DD HH:mm"),
                    "detected_value": st.column_config.NumberColumn("Value", format="%.2f"),
                    "severity": st.column_config.TextColumn("Severity"),
                    "reason": st.column_config.TextColumn("Diagnostic")
                },
                use_container_width=True,
                hide_index=True
            )
        else:
            st.success("All smart meters operating inside nominal electrical thresholds. Zero active anomalies.")
