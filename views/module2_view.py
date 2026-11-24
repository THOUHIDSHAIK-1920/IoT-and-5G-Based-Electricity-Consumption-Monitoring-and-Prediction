"""
VoltSense 5G - View: Module 2 – Electricity Consumption Analysis & Anomaly Detection
Hourly, daily, weekly, monthly aggregations, tariff bill estimation, and dual-engine anomaly detection.
"""
import streamlit as st
import pandas as pd
from typing import Dict, Any

from database.database import DatabaseManager
from modules.consumption_analysis import ConsumptionAnalyzer
from modules.anomaly_detection import AnomalyDetector
from utils.charts import (
    create_diurnal_hourly_chart,
    create_daily_consumption_bar_chart,
    create_anomaly_scatter_chart
)
from config import DEFAULT_TARIFF_INR_PER_KWH


def render_module2_view(
    db: DatabaseManager, 
    analyzer: ConsumptionAnalyzer, 
    detector: AnomalyDetector
):
    """Renders Module 2 UI."""
    st.markdown("""
        <div class="voltsense-header">
            <div class="voltsense-title-box">
                <h1>Module 2: Consumption Analysis & Anomaly Detection</h1>
                <div class="voltsense-tagline">Multi-Period Energy Aggregations, Tariff Cost Modeling, and Dual-Engine Anomaly Detection</div>
            </div>
            <div>
                <span class="badge-hw-ready">Module 2 Active</span>
            </div>
        </div>
    """, unsafe_allow_html=True)

    tab_realtime, tab_historical, tab_cost, tab_anomalies = st.tabs([
        "⚡ A. Real-Time Consumption Monitoring",
        "📊 B. Historical Consumption Analysis",
        "💰 C. Energy Cost Calculation & Advisory",
        "⚠️ D. Anomaly Detection & Diagnostics"
    ])

    devices = db.get_devices()
    dev_lookup = {d["device_id"]: d for d in devices}

    # Global Filter Bar for Module 2
    f_col1, f_col2, f_col3 = st.columns([2, 2, 2])
    with f_col1:
        buildings = ["ALL"] + sorted(list({d["building"] for d in devices}))
        sel_bld = st.selectbox("Building Filter:", options=buildings, key="m2_bld_filter")
    with f_col2:
        filtered_devs = devices if sel_bld == "ALL" else [d for d in devices if d["building"] == sel_bld]
        dev_choices = ["ALL"] + [d["device_id"] for d in filtered_devs]
        sel_dev = st.selectbox("Smart Meter / Room Filter:", options=dev_choices, key="m2_dev_filter", format_func=lambda x: "All Sub-meters" if x == "ALL" else f"{x} ({dev_lookup.get(x, {}).get('room', '')})")
    with f_col3:
        tariff_input = st.number_input("Configured Tariff (₹/kWh):", min_value=1.0, max_value=40.0, value=DEFAULT_TARIFF_INR_PER_KWH, step=0.25, key="m2_tariff")

    # Fetch analysis data
    analysis = analyzer.analyze_historical_consumption(device_id=sel_dev, building=sel_bld, tariff_rate=tariff_input)

    # --------------------------------------------------------------------------
    # TAB A: Real-Time Consumption Monitoring
    # --------------------------------------------------------------------------
    with tab_realtime:
        st.markdown("<div class='section-header-box'><h2>Real-Time Consumption Pulse</h2><p>Live active power and electrical parameter monitoring for selected facility zones</p></div>", unsafe_allow_html=True)

        live_data = analyzer.get_realtime_metrics(sel_dev)

        rc1, rc2, rc3, rc4, rc5 = st.columns(5)
        rc1.metric("Active Power", f"{live_data['active_power']:,.1f} W")
        rc2.metric("Grid Voltage", f"{live_data['voltage']:.1f} V")
        rc3.metric("Load Current", f"{live_data['current']:.2f} A")
        rc4.metric("Power Factor", f"{live_data['power_factor']:.3f}")
        rc5.metric("Frequency", f"{live_data['frequency']:.2f} Hz")

        st.markdown("<br/>", unsafe_allow_html=True)
        readings_df = db.get_readings(device_id=sel_dev, building=sel_bld, limit=120, order="DESC")
        if not readings_df.empty:
            readings_df = readings_df.sort_values("timestamp")
            from utils.charts import create_realtime_power_chart
            fig_p = create_realtime_power_chart(readings_df)
            st.plotly_chart(fig_p, use_container_width=True)

    # --------------------------------------------------------------------------
    # TAB B: Historical Consumption Analysis
    # --------------------------------------------------------------------------
    with tab_historical:
        st.markdown("<div class='section-header-box'><h2>Historical Consumption & Load Profiling</h2><p>Hourly diurnal curves, daily energy bars, weekly comparisons, and peak load identification</p></div>", unsafe_allow_html=True)

        # Diurnal 24h Profile
        hourly_df = db.get_hourly_aggregate(device_id=sel_dev)
        if not hourly_df.empty:
            fig_diurnal = create_diurnal_hourly_chart(hourly_df)
            st.plotly_chart(fig_diurnal, use_container_width=True)

        st.markdown("<br/>", unsafe_allow_html=True)

        # Daily Energy Consumption & Costs Bar Chart
        if not analysis["daily_df"].empty:
            fig_daily = create_daily_consumption_bar_chart(analysis["daily_df"], tariff_rate=tariff_input)
            st.plotly_chart(fig_daily, use_container_width=True)

        # Weekly & Monthly Summary Cards
        w_c1, w_c2, w_c3 = st.columns(3)
        with w_c1:
            st.markdown(f"""
                <div class="kpi-card">
                    <div class="kpi-title">📅 Past 7 Days Energy</div>
                    <div class="kpi-value">{analysis['curr_week_kwh']:,.1f} <span style="font-size:0.9rem;color:#94A3B8">kWh</span></div>
                    <div class="kpi-subtext">Est. Cost: ₹{analysis['curr_week_cost_inr']:,.2f}</div>
                </div>
            """, unsafe_allow_html=True)
        with w_c2:
            change_color = "#EF4444" if analysis['week_change_pct'] > 0 else "#10B981"
            st.markdown(f"""
                <div class="kpi-card">
                    <div class="kpi-title">📈 Week-over-Week Shift</div>
                    <div class="kpi-value" style="color:{change_color}">{analysis['week_change_pct']:+.1f}%</div>
                    <div class="kpi-subtext">Prior 7d: {analysis['prior_week_kwh']:,.1f} kWh</div>
                </div>
            """, unsafe_allow_html=True)
        with w_c3:
            st.markdown(f"""
                <div class="kpi-card">
                    <div class="kpi-title">🏆 Peak Consumption Demand</div>
                    <div class="kpi-value">{analysis['peak_demand_w']:,.0f} <span style="font-size:0.9rem;color:#94A3B8">W</span></div>
                    <div class="kpi-subtext">Recorded at: {analysis['peak_timestamp'][:16]}</div>
                </div>
            """, unsafe_allow_html=True)

        # Monthly Consumption Table
        if not analysis["monthly_df"].empty:
            st.markdown("<b>Monthly Aggregated Usage:</b>", unsafe_allow_html=True)
            st.dataframe(
                analysis["monthly_df"],
                column_config={
                    "month": st.column_config.TextColumn("Billing Month"),
                    "total_energy_kwh": st.column_config.NumberColumn("Total Consumption (kWh)", format="%.2f"),
                    "peak_power_w": st.column_config.NumberColumn("Max Recorded Power (W)", format="%.1f"),
                    "estimated_bill_inr": st.column_config.NumberColumn(f"Estimated Bill (₹ @ ₹{tariff_input}/kWh)", format="₹%.2f")
                },
                use_container_width=True,
                hide_index=True
            )

    # --------------------------------------------------------------------------
    # TAB C: Energy Cost Calculation
    # --------------------------------------------------------------------------
    with tab_cost:
        st.markdown("<div class='section-header-box'><h2>Energy Cost Calculation & Financial Advisory</h2><p>Standard tariff modeling, Time-of-Day (ToD) optimization, and power factor penalty analysis</p></div>", unsafe_allow_html=True)

        # Statutory Bill Disclaimer
        st.markdown("""
            <div class="simulation-disclaimer">
                <span>⚠️ <b>Regulatory Notice:</b> Estimated energy costs are computed based on configured tariff slabs for internal facility budget forecasting and departmental chargeback. This is not an official statutory DISCOM utility electricity bill.</span>
            </div>
        """, unsafe_allow_html=True)

        st.info(f"**Mathematical Formula Applied:**\n$$\\text{{Energy Cost (₹)}} = \\text{{Total Energy Consumption (kWh)}} \\times \\text{{Electricity Tariff (₹/kWh)}} = {analysis['total_kwh']:,.2f} \\times ₹{tariff_input:.2f} = \\mathbf{{₹{analysis['total_cost_inr']:,.2f}}}$$")

        c_k1, c_k2, c_k3 = st.columns(3)
        with c_k1:
            st.metric("Total Cumulative Consumption", f"{analysis['total_kwh']:,.2f} kWh")
        with c_k2:
            st.metric("Estimated Total Electricity Bill", f"₹{analysis['total_cost_inr']:,.2f}")
        with c_k3:
            st.metric("CO2 Carbon Footprint", f"{analysis['co2_emissions_kg']:,.1f} kg CO2e")

        st.markdown("<br/>", unsafe_allow_html=True)

        # Time-of-Day (ToD) Breakdown
        tod = analysis["tod_analysis"]
        if tod:
            st.markdown("<div class='section-header-box'><h3>Time-of-Day (ToD) Multi-Tier Tariff Breakdown</h3><p>Evaluates cost distribution across Peak, Normal, and Off-Peak operating hours</p></div>", unsafe_allow_html=True)

            tod_c1, tod_c2, tod_c3 = st.columns(3)
            with tod_c1:
                st.markdown(f"""
                    <div class="kpi-card">
                        <div class="kpi-title" style="color:#EF4444;">🔴 Peak Hours (ToD Surcharge)</div>
                        <div class="kpi-value">{tod['peak_kwh']:,.1f} <span style="font-size:0.9rem;color:#94A3B8">kWh</span></div>
                        <div class="kpi-subtext">Peak Cost: ₹{tod['peak_cost_inr']:,.2f} (@ ₹10.50/kWh)</div>
                    </div>
                """, unsafe_allow_html=True)
            with tod_c2:
                st.markdown(f"""
                    <div class="kpi-card">
                        <div class="kpi-title" style="color:#38BDF8;">🔵 Normal Hours (Base Rate)</div>
                        <div class="kpi-value">{tod['normal_kwh']:,.1f} <span style="font-size:0.9rem;color:#94A3B8">kWh</span></div>
                        <div class="kpi-subtext">Normal Cost: ₹{tod['normal_cost_inr']:,.2f} (@ ₹{tariff_input}/kWh)</div>
                    </div>
                """, unsafe_allow_html=True)
            with tod_c3:
                st.markdown(f"""
                    <div class="kpi-card">
                        <div class="kpi-title" style="color:#10B981;">🟢 Off-Peak Hours (Discounted)</div>
                        <div class="kpi-value">{tod['off_peak_kwh']:,.1f} <span style="font-size:0.9rem;color:#94A3B8">kWh</span></div>
                        <div class="kpi-subtext">Off-Peak Cost: ₹{tod['off_peak_cost_inr']:,.2f} (@ ₹5.20/kWh)</div>
                    </div>
                """, unsafe_allow_html=True)

            st.success(f"💡 **Demand-Side Management (DSM) Opportunity:** By shifting 20% of flexible thermal/computing loads from peak hours (09:00-13:00) to off-peak night hours, the campus can save approximately **₹{tod['potential_tod_savings_inr']:,.2f}** per billing cycle.")

        # Power Factor Penalty / Incentive Audit
        pf_audit = analysis["pf_audit"]
        st.markdown("<br/>", unsafe_allow_html=True)
        st.markdown("<div class='section-header-box'><h3>Power Factor Efficiency & APFC Capacitor Audit</h3></div>", unsafe_allow_html=True)
        pf_c1, pf_c2 = st.columns([1, 2])
        with pf_c1:
            pf_status_color = "#10B981" if pf_audit["status"] == "OPTIMAL" else ("#EF4444" if pf_audit["status"] == "PENALTY_RISK" else "#38BDF8")
            st.markdown(f"""
                <div class="kpi-card">
                    <div class="kpi-title">Average Power Factor</div>
                    <div class="kpi-value" style="color:{pf_status_color};">{pf_audit['avg_power_factor']}</div>
                    <div class="kpi-subtext">Status: <b>{pf_audit['status']}</b></div>
                </div>
            """, unsafe_allow_html=True)
        with pf_c2:
            st.markdown(f"""
                <div class="kpi-card">
                    <div class="kpi-title">Efficiency Advisory</div>
                    <div style="color:#CBD5E1;font-size:0.9rem;line-height:1.6;">{pf_audit['recommendation']}</div>
                </div>
            """, unsafe_allow_html=True)

    # --------------------------------------------------------------------------
    # TAB D: Anomaly Detection
    # --------------------------------------------------------------------------
    with tab_anomalies:
        st.markdown("<div class='section-header-box'><h2>Intelligent Anomaly Detection & Grid Diagnostics</h2><p>Multi-dimensional outlier discovery using Statistical Z-score/IQR and Scikit-learn Isolation Forest</p></div>", unsafe_allow_html=True)

        # Anomaly Detection Controls
        ad_c1, ad_c2, ad_c3 = st.columns([2, 2, 2])
        with ad_c1:
            ad_method = st.selectbox("Detection Model:", ["HYBRID", "STATISTICAL", "ISOLATION_FOREST"], format_func=lambda x: "Hybrid (Statistical Rules + Isolation Forest)" if x == "HYBRID" else ("Statistical (Z-Score & Voltage Sag/Surge Rules)" if x == "STATISTICAL" else "Machine Learning (Isolation Forest)"))
        with ad_c2:
            sensitivity_rate = st.slider("Outlier Contamination Sensitivity:", min_value=0.01, max_value=0.10, value=0.03, step=0.01)
        with ad_c3:
            st.write("")
            st.write("")
            if st.button("🔍 Execute Anomaly Detection Scan", use_container_width=True, type="primary"):
                with st.spinner("Executing statistical limit checks and Isolation Forest inference..."):
                    anom_results = detector.scan_and_log_anomalies(
                        device_id=sel_dev,
                        sensitivity=sensitivity_rate,
                        method=ad_method
                    )
                    st.success(f"Anomaly scan completed. Total identified events: {len(anom_results)}")

        # Fetch anomalies
        anomalies_df = db.get_anomalies(device_id=sel_dev)

        anom_k1, anom_k2, anom_k3, anom_k4 = st.columns(4)
        crit_count = len(anomalies_df[anomalies_df["severity"] == "CRITICAL"]) if not anomalies_df.empty else 0
        med_count = len(anomalies_df[anomalies_df["severity"] == "MEDIUM"]) if not anomalies_df.empty else 0
        low_count = len(anomalies_df[anomalies_df["severity"] == "LOW"]) if not anomalies_df.empty else 0
        total_anom = len(anomalies_df)

        anom_k1.metric("Total Identified Anomalies", f"{total_anom}")
        anom_k2.metric("Critical Electrical Threats", f"{crit_count}", delta="High Priority" if crit_count > 0 else "Normal", delta_color="inverse")
        anom_k3.metric("Medium Deviation Events", f"{med_count}")
        anom_k4.metric("Low Deviation Outliers", f"{low_count}")

        # Anomaly Timeline Scatter Chart
        st.markdown("<br/>", unsafe_allow_html=True)
        readings_full = db.get_readings(device_id=sel_dev, limit=400, order="DESC")
        if not readings_full.empty:
            readings_full = readings_full.sort_values("timestamp")
            fig_anom_scatter = create_anomaly_scatter_chart(readings_full, anomalies_df)
            st.plotly_chart(fig_anom_scatter, use_container_width=True)

        # Anomaly Log Table
        st.markdown("<br/>", unsafe_allow_html=True)
        st.markdown("<div class='section-header-box'><h3>Comprehensive Anomaly Incident Register</h3></div>", unsafe_allow_html=True)
        
        if not anomalies_df.empty:
            st.dataframe(
                anomalies_df[[
                    "id", "timestamp", "device_id", "device_name", 
                    "metric", "detected_value", "expected_range", 
                    "severity", "detection_method", "reason"
                ]],
                column_config={
                    "id": st.column_config.NumberColumn("Event ID"),
                    "timestamp": st.column_config.DatetimeColumn("Timestamp", format="YYYY-MM-DD HH:mm"),
                    "device_id": st.column_config.TextColumn("Device ID"),
                    "device_name": st.column_config.TextColumn("Monitoring Station"),
                    "metric": st.column_config.TextColumn("Disturbed Parameter"),
                    "detected_value": st.column_config.NumberColumn("Detected Value", format="%.2f"),
                    "expected_range": st.column_config.TextColumn("Acceptable Envelope"),
                    "severity": st.column_config.TextColumn("Severity"),
                    "detection_method": st.column_config.TextColumn("Algorithm"),
                    "reason": st.column_config.TextColumn("Physical Diagnostic")
                },
                use_container_width=True,
                hide_index=True
            )
        else:
            st.info("No anomalies recorded. Run a scan above or inject a controlled test spike from Module 1.")
