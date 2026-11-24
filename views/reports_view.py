"""
VoltSense 5G - View: Reports and Export
Generates downloadable executive PDF audit reports, CSV telemetry exports, and handles CSV dataset uploads.
"""
import streamlit as st
import pandas as pd
from datetime import datetime

from database.database import DatabaseManager
from modules.consumption_analysis import ConsumptionAnalyzer
from modules.anomaly_detection import AnomalyDetector
from modules.energy_forecasting import EnergyForecastingEngine
from utils.export import generate_executive_pdf_report
from config import DEFAULT_TARIFF_INR_PER_KWH


def render_reports_view(
    db: DatabaseManager,
    analyzer: ConsumptionAnalyzer,
    detector: AnomalyDetector,
    forecaster: EnergyForecastingEngine
):
    """Renders Reports and Export interface."""
    st.markdown("""
        <div class="voltsense-header">
            <div class="voltsense-title-box">
                <h1>Energy Reports & Data Export Center</h1>
                <div class="voltsense-tagline">Automated Executive PDF Audits, CSV Data Streams, and External Sensor Ingestion</div>
            </div>
            <div>
                <span class="badge-hw-ready">Export Engine Active</span>
            </div>
        </div>
    """, unsafe_allow_html=True)

    tab_pdf, tab_csv, tab_import = st.tabs([
        "📄 Executive PDF Audit Report",
        "📥 CSV Telemetry Export",
        "📤 CSV Dataset Ingestion (Upload)"
    ])

    devices = db.get_devices()
    tariff_val = st.session_state.get("global_tariff", DEFAULT_TARIFF_INR_PER_KWH)

    # --------------------------------------------------------------------------
    # TAB 1: Executive PDF Audit Report
    # --------------------------------------------------------------------------
    with tab_pdf:
        st.markdown("<div class='section-header-box'><h2>Generate Comprehensive Energy Audit PDF</h2><p>Formulates a multi-page publication-quality audit document compiled via ReportLab</p></div>", unsafe_allow_html=True)

        st.write("The generated PDF report contains an executive KPI summary, IoT smart meter inventory, historical consumption breakdown, identified anomaly logs, machine learning evaluation benchmarks, and electrical cost breakdowns.")

        pdf_col1, pdf_col2 = st.columns([2, 2])
        with pdf_col1:
            report_tariff = st.number_input("Tariff for PDF Report (₹/kWh):", value=tariff_val, min_value=1.0, max_value=50.0, step=0.25)
        with pdf_col2:
            st.write("")
            st.write("")
            generate_btn = st.button("📑 Compile & Download Executive PDF Report", type="primary", use_container_width=True)

        if generate_btn or "cached_pdf_bytes" in st.session_state:
            if generate_btn:
                with st.spinner("Compiling academic audit PDF report..."):
                    hist_data = analyzer.analyze_historical_consumption(tariff_rate=report_tariff)
                    anomalies_df = db.get_anomalies(limit=25)
                    eval_df, _ = forecaster.evaluate_and_compare_models()
                    forecast_res = forecaster.generate_future_forecast(horizon_hours=24, tariff_rate=report_tariff)
                    forecast_df = forecast_res.get("forecast_df", pd.DataFrame())

                    summary_kpis = {
                        "total_kwh": hist_data["total_kwh"],
                        "total_cost_inr": hist_data["total_cost_inr"],
                        "peak_demand_w": hist_data["peak_demand_w"],
                        "avg_power_factor": hist_data["avg_power_factor"],
                        "co2_kg": hist_data["co2_emissions_kg"],
                        "active_devices": len(devices),
                        "anomalies_count": len(anomalies_df)
                    }

                    pdf_bytes = generate_executive_pdf_report(
                        summary_kpis=summary_kpis,
                        devices_list=devices,
                        daily_consumption_df=hist_data.get("daily_df", pd.DataFrame()),
                        anomalies_df=anomalies_df,
                        ml_eval_df=eval_df if eval_df is not None else pd.DataFrame(),
                        forecast_df=forecast_df,
                        tariff_inr=report_tariff
                    )
                    st.session_state["cached_pdf_bytes"] = pdf_bytes

            cached_bytes = st.session_state.get("cached_pdf_bytes")
            if cached_bytes:
                st.download_button(
                    label="⬇️ Click to Download VoltSense_5G_Executive_Report.pdf",
                    data=cached_bytes,
                    file_name=f"VoltSense_5G_Energy_Report_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )
                st.success("Executive PDF report generated successfully! Click above to download.")

    # --------------------------------------------------------------------------
    # TAB 2: CSV Data Export
    # --------------------------------------------------------------------------
    with tab_csv:
        st.markdown("<div class='section-header-box'><h2>Export Database Records to CSV</h2><p>Download raw telemetry data, daily consumption summaries, and flagged anomalies</p></div>", unsafe_allow_html=True)

        exp_c1, exp_c2, exp_c3 = st.columns(3)

        with exp_c1:
            st.markdown("#### 1. Full Raw Telemetry CSV")
            st.write("All stored electrical parameters with 5G latency and protocol headers.")
            raw_csv = db.export_readings_csv()
            st.download_button(
                label="⬇️ Download Raw Telemetry CSV",
                data=raw_csv,
                file_name=f"voltsense_raw_telemetry_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv",
                use_container_width=True
            )

        with exp_c2:
            st.markdown("#### 2. Daily Aggregated Energy CSV")
            st.write("Calculated daily kWh, peak power, and estimated costs per device.")
            daily_df = db.get_daily_consumption()
            if not daily_df.empty:
                daily_csv = daily_df.to_csv(index=False)
                st.download_button(
                    label="⬇️ Download Daily Energy CSV",
                    data=daily_csv,
                    file_name=f"voltsense_daily_energy_{datetime.now().strftime('%Y%m%d')}.csv",
                    mime="text/csv",
                    use_container_width=True
                )

        with exp_c3:
            st.markdown("#### 3. Flagged Anomaly Incident Log CSV")
            st.write("Historical record of all detected grid spikes and disturbances.")
            anom_df = db.get_anomalies()
            if not anom_df.empty:
                anom_csv = anom_df.to_csv(index=False)
                st.download_button(
                    label="⬇️ Download Anomaly Log CSV",
                    data=anom_csv,
                    file_name=f"voltsense_anomalies_{datetime.now().strftime('%Y%m%d')}.csv",
                    mime="text/csv",
                    use_container_width=True
                )

    # --------------------------------------------------------------------------
    # TAB 3: CSV Dataset Ingestion (Upload)
    # --------------------------------------------------------------------------
    with tab_import:
        st.markdown("<div class='section-header-box'><h2>Import External Smart Meter CSV Data</h2><p>Ingest actual physical hardware logs or custom benchmark datasets</p></div>", unsafe_allow_html=True)

        st.info("Mandatory CSV Columns: `device_id`, `timestamp` (YYYY-MM-DD HH:MM:SS), `voltage`, `current`, `active_power`, `energy_kwh`.")

        uploaded_file = st.file_uploader("Choose an Energy CSV file:", type=["csv"])
        if uploaded_file is not None:
            if st.button("📤 Validate & Ingest CSV into Database", type="primary"):
                with st.spinner("Validating columns and checking for duplicate timestamps..."):
                    try:
                        df_upload = pd.read_csv(uploaded_file)
                        inserted, skipped = db.import_readings_csv(df_upload)
                        st.success(f"CSV Ingestion Complete! Inserted: {inserted} records. Skipped: {skipped} duplicates.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Failed to ingest CSV: {str(e)}")
