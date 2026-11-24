"""
VoltSense 5G - View: Module 1 – IoT Data Acquisition and 5G Communication
Device registry, sensor simulation, 5G slicing telemetry, and ESP32 hardware architecture.
"""
import streamlit as st
import pandas as pd
import json
from typing import Dict, Any

from database.database import DatabaseManager
from modules.iot_acquisition import SensorSimulator, ESP32_FIRMWARE_SOURCE
from modules.communication_5g import Communication5GManager
from utils.charts import create_multi_parameter_chart, create_5g_latency_chart
from utils.validation import validate_device_registration
from config import FIVE_G_PROFILES


def render_module1_view(
    db: DatabaseManager, 
    sim: SensorSimulator, 
    comm: Communication5GManager
):
    """Renders Module 1 UI."""
    st.markdown("""
        <div class="voltsense-header">
            <div class="voltsense-title-box">
                <h1>Module 1: IoT Data Acquisition & 5G Communication</h1>
                <div class="voltsense-tagline">Sensor Measurement Ingestion, Device Registry, 3GPP Rel-16 Network Slicing & MQTT Connectivity</div>
            </div>
            <div>
                <span class="badge-hw-ready">Module 1 Active</span>
            </div>
        </div>
    """, unsafe_allow_html=True)

    tab_devices, tab_sensors, tab_5g, tab_esp32 = st.tabs([
        "📱 A. IoT Device Monitoring",
        "⚡ B. Parameter Acquisition & Simulation",
        "📡 C. 5G Communication Layer",
        "🔌 D. ESP32 / Smart Meter Hardware Integration"
    ])

    # --------------------------------------------------------------------------
    # TAB A: IoT Device Monitoring
    # --------------------------------------------------------------------------
    with tab_devices:
        st.markdown("<div class='section-header-box'><h2>Connected Smart Meter Grid</h2><p>Real-time health, physical location, and telemetry heartbeat of campus energy meters</p></div>", unsafe_allow_html=True)

        devices = db.get_devices()

        # Metrics bar for devices
        c1, c2, c3, c4 = st.columns(4)
        total_devs = len(devices)
        online_devs = len([d for d in devices if d.get("status") == "ONLINE"])
        offline_devs = len([d for d in devices if d.get("status") == "OFFLINE"])
        standby_devs = len([d for d in devices if d.get("status") == "STANDBY"])

        c1.metric("Registered Devices", f"{total_devs} Nodes")
        c2.metric("Online & Transmitting", f"{online_devs}", delta="Active 5G Link", delta_color="normal")
        c3.metric("Offline / No Link", f"{offline_devs}", delta="-0.0%", delta_color="inverse")
        c4.metric("Standby / Power Save", f"{standby_devs}")

        st.markdown("<br/>", unsafe_allow_html=True)

        # Device Cards Grid
        cols = st.columns(3)
        for i, dev in enumerate(devices):
            col_target = cols[i % 3]
            status_color = "#10B981" if dev.get("status") == "ONLINE" else ("#EF4444" if dev.get("status") == "OFFLINE" else "#F59E0B")
            status_class = f"status-dot-{dev.get('status', 'online').lower()}"

            with col_target:
                st.markdown(f"""
                    <div class="kpi-card">
                        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">
                            <span style="font-weight:700;color:#F8FAFC;font-size:1.05rem;">{dev.get('device_name')}</span>
                            <span><span class="status-dot {status_class}"></span> <b style="color:{status_color};font-size:0.8rem;">{dev.get('status')}</b></span>
                        </div>
                        <div style="font-size:0.82rem;color:#94A3B8;line-height:1.6;">
                            <b>ID:</b> <code style="color:#38BDF8;">{dev.get('device_id')}</code><br/>
                            <b>Location:</b> {dev.get('building')} — {dev.get('room')}<br/>
                            <b>IP / MAC:</b> {dev.get('ip_address', 'N/A')} | {dev.get('mac_address', 'N/A')}<br/>
                            <b>Signal Strength:</b> {dev.get('signal_rssi', -65)} dBm (5G NR RSRP)<br/>
                            <b>Nominal Power:</b> {dev.get('nominal_power_w', 5000):,.0f} W ({dev.get('load_category', 'General')})<br/>
                            <b>Last Telemetry:</b> {str(dev.get('last_reading_time', 'Pending'))[:19]}
                        </div>
                    </div>
                """, unsafe_allow_html=True)

        st.markdown("<br/>", unsafe_allow_html=True)

        # Device Registration Form (Accordion)
        with st.expander("➕ Register New IoT Smart Meter / Electrical Monitoring Point", expanded=False):
            st.write("Add a new physical or simulated smart meter to the campus energy grid.")
            with st.form("reg_device_form"):
                rf_col1, rf_col2 = st.columns(2)
                with rf_col1:
                    new_id = st.text_input("Device ID (e.g., DEV_AUD_01):", placeholder="DEV_XXX_01")
                    new_name = st.text_input("Device Name:", placeholder="Auditorium Main HVAC Meter")
                    new_bld = st.selectbox("Building / Location:", ["College Building A", "College Building B", "Computer Laboratory", "Classroom Block", "Library", "Administrative Office", "Auditorium / Sports Complex", "Campus Substation"])
                    new_room = st.text_input("Room / Distribution Panel:", placeholder="Panel DB-2B")
                with rf_col2:
                    new_ip = st.text_input("IP Address:", value="192.168.50.101")
                    new_mac = st.text_input("MAC Address:", value="84:F3:EB:E5:01:33")
                    new_p_nom = st.number_input("Nominal Rated Power (W):", min_value=100.0, max_value=100000.0, value=7500.0, step=500.0)
                    new_cat = st.selectbox("Load Category:", ["Lighting & HVAC", "Heavy Industrial / Lab", "Server & Computing", "Institutional / Office", "General"])

                submitted = st.form_submit_button("Register Smart Meter", type="primary")
                if submitted:
                    dev_payload = {
                        "device_id": new_id.strip(),
                        "device_name": new_name.strip(),
                        "building": new_bld,
                        "room": new_room.strip(),
                        "ip_address": new_ip.strip(),
                        "mac_address": new_mac.strip(),
                        "nominal_power_w": new_p_nom,
                        "load_category": new_cat
                    }
                    is_valid, errors = validate_device_registration(dev_payload)
                    if is_valid:
                        success = db.add_device(dev_payload)
                        if success:
                            st.success(f"Device '{new_name}' registered successfully!")
                            st.rerun()
                        else:
                            st.error(f"Device ID '{new_id}' already exists in registry.")
                    else:
                        st.error(f"Validation Error: {'; '.join(errors)}")

    # --------------------------------------------------------------------------
    # TAB B: Parameter Acquisition & Simulation
    # --------------------------------------------------------------------------
    with tab_sensors:
        st.markdown("<div class='section-header-box'><h2>Electricity Parameter Acquisition & Sensor Simulation</h2><p>Physics-based instantaneous electrical measurement generation with rigorous power calculations</p></div>", unsafe_allow_html=True)

        # Electrical Law Callout Cards
        p_c1, p_c2, p_c3 = st.columns(3)
        with p_c1:
            st.info("📐 **Apparent Power (S):**\n$$S = V \\times I\\text{ (VA)}$$\nTotal vector power supplied by the grid.")
        with p_c2:
            st.info("⚡ **Active Real Power (P):**\n$$P = V \\times I \\times \\cos\\varphi\\text{ (W)}$$\nActual useful work consumed by resistive loads.")
        with p_c3:
            st.info("🔋 **Accumulated Energy (kWh):**\n$$E = \\int \\frac{P(t)}{1000} dt\\text{ (kWh)}$$\nDiscrete integral of active power over elapsed time.")

        # Sensor Simulation Controls
        st.markdown("<br/>", unsafe_allow_html=True)
        sim_col1, sim_col2, sim_col3 = st.columns([2, 2, 2])

        with sim_col1:
            sim_target_dev = st.selectbox("Select Target Meter:", options=[d["device_id"] for d in devices], key="sim_dev_sel")
        with sim_col2:
            sim_load_mult = st.slider("Load Multiplier (Scaling):", min_value=0.2, max_value=2.5, value=1.0, step=0.1)
        with sim_col3:
            inject_anomaly = st.selectbox("Inject Controlled Anomaly (Test):", ["NONE", "POWER_SPIKE", "VOLTAGE_SAG", "LOW_POWER_FACTOR", "VOLTAGE_SURGE"])

        btn_c1, btn_c2 = st.columns(2)
        with btn_c1:
            if st.button("⚡ Acquire Single Reading (Step Simulator)", use_container_width=True, type="primary"):
                reading = sim.generate_single_reading(
                    device_id=sim_target_dev,
                    load_multiplier=sim_load_mult,
                    inject_anomaly_type=None if inject_anomaly == "NONE" else inject_anomaly
                )
                db.insert_reading(reading)
                st.success(f"Acquired telemetry from {sim_target_dev}: {reading['active_power']:,.1f}W @ {reading['voltage']}V (PF: {reading['power_factor']})")
                st.rerun()

        with btn_c2:
            if st.button("📡 Transmit Burst to All Smart Meters", use_container_width=True):
                new_readings = sim.simulate_tick_for_all_devices()
                st.success(f"Successfully polled and recorded {len(new_readings)} active campus devices.")
                st.rerun()

        # Multi-Parameter Time Series Chart
        st.markdown("<br/>", unsafe_allow_html=True)
        st.markdown("<div class='section-header-box'><h2>Acquired Electrical Parameter Telemetry</h2><p>Synchronous 4-channel oscilloscope view: Voltage, Current, Frequency, and Power Factor</p></div>", unsafe_allow_html=True)
        
        hist_readings = db.get_readings(device_id=sim_target_dev, limit=60, order="DESC")
        if not hist_readings.empty:
            hist_readings = hist_readings.sort_values("timestamp")
            fig_multi = create_multi_parameter_chart(hist_readings)
            st.plotly_chart(fig_multi, use_container_width=True)
        else:
            st.info("No telemetry readings available for selected device.")

    # --------------------------------------------------------------------------
    # TAB C: 5G Communication Layer
    # --------------------------------------------------------------------------
    with tab_5g:
        st.markdown("<div class='section-header-box'><h2>3GPP Release-16 5G Communication Architecture</h2><p>Network Slicing, Ultra-Reliable Low-Latency Communication (URLLC), and MQTT Broker Ingestion</p></div>", unsafe_allow_html=True)

        st.markdown("""
            <div class="simulation-disclaimer">
                <span>⚠️ <b>Clear Architecture Notice:</b> Network latency, jitter, and slicing parameters are computed according to <b>3GPP TS 23.501 Release-16 5G Core (5GC) mathematical channel models</b>. The system simulates URLLC (1-4ms), eMBB (10-22ms), and mMTC profiles. Live physical MQTT transmission is supported simultaneously.</span>
            </div>
        """, unsafe_allow_html=True)

        # Slice Selector
        slice_c1, slice_c2 = st.columns([2, 3])
        with slice_c1:
            slice_choice = st.radio(
                "Active 5G Slicing Profile:",
                options=list(FIVE_G_PROFILES.keys()),
                format_func=lambda k: FIVE_G_PROFILES[k]["name"],
                index=list(FIVE_G_PROFILES.keys()).index(comm.active_slice)
            )
            comm.set_active_slice(slice_choice)

        with slice_c2:
            curr_profile = comm.get_slice_info()
            st.markdown(f"""
                <div class="five-g-card">
                    <h3 style="color:#38BDF8;margin-top:0;">{curr_profile['name']}</h3>
                    <p style="color:#CBD5E1;font-size:0.85rem;">{curr_profile['description']}</p>
                    <div style="font-size:0.82rem;color:#94A3B8;line-height:1.7;">
                        <b>Network Slice Subnet Instance (NSSI):</b> <code style="color:#38BDF8;">{curr_profile['slice_id']}</code><br/>
                        <b>Latency Envelope:</b> {curr_profile['latency_min_ms']} - {curr_profile['latency_max_ms']} ms<br/>
                        <b>Jitter Tolerance:</b> ±{curr_profile['jitter_ms']} ms | <b>Target Reliability:</b> {(1.0 - curr_profile['packet_loss_rate']) * 100:.4f}%<br/>
                        <b>Peak Bandwidth:</b> {curr_profile['bandwidth_kbps']} kbps
                    </div>
                </div>
            """, unsafe_allow_html=True)

        # Slicing Benchmark Bar Chart
        slice_data = [
            {"slice_name": "5G URLLC", "latency_ms": 2.8},
            {"slice_name": "5G eMBB", "latency_ms": 15.4},
            {"slice_name": "5G mMTC", "latency_ms": 62.0},
            {"slice_name": "Legacy 4G LTE", "latency_ms": 78.5}
        ]
        fig_lat = create_5g_latency_chart(slice_data)
        st.plotly_chart(fig_lat, use_container_width=True)

        # MQTT Live Broker Configuration
        st.markdown("<br/>", unsafe_allow_html=True)
        st.markdown("<div class='section-header-box'><h2>Configurable MQTT Broker (Hardware & Cloud Ingestion)</h2><p>Allows external physical smart meters or gateway devices to publish real telemetry over MQTT</p></div>", unsafe_allow_html=True)

        mq_c1, mq_c2, mq_c3 = st.columns(3)
        with mq_c1:
            broker_host = st.text_input("MQTT Broker Host:", value=comm.mqtt_broker_host)
        with mq_c2:
            broker_port = st.number_input("Port:", value=comm.mqtt_broker_port, min_value=1, max_value=65535)
        with mq_c3:
            broker_topic = st.text_input("Subscription Topic:", value=comm.mqtt_topic)

        btn_mq1, btn_mq2, btn_mq3 = st.columns(3)
        with btn_mq1:
            if not comm.mqtt_connected:
                if st.button("🔗 Connect to MQTT Broker", use_container_width=True, type="primary"):
                    success, msg = comm.connect_mqtt_broker(broker_host, int(broker_port), broker_topic)
                    if success:
                        st.success(msg)
                    else:
                        st.error(msg)
            else:
                if st.button("🔌 Disconnect MQTT Broker", use_container_width=True):
                    comm.disconnect_mqtt_broker()
                    st.info("MQTT Broker disconnected.")
        with btn_mq2:
            if st.button("📤 Publish Test Telemetry Packet", use_container_width=True):
                if comm.mqtt_connected:
                    succ, msg = comm.publish_test_mqtt_packet(sim_target_dev, power_w=8500.0)
                    st.success(msg)
                else:
                    st.warning("Please connect to the MQTT broker first.")
        with btn_mq3:
            st.markdown(f"<b>MQTT Status:</b> {'🟢 CONNECTED' if comm.mqtt_connected else '⚪ DISCONNECTED'}", unsafe_allow_html=True)

        # Raw MQTT Stream Log
        mqtt_logs_df = db.get_mqtt_logs(limit=8)
        if not mqtt_logs_df.empty:
            st.write("<b>Recent MQTT Packets:</b>", unsafe_allow_html=True)
            st.dataframe(mqtt_logs_df, use_container_width=True, hide_index=True)

    # --------------------------------------------------------------------------
    # TAB D: ESP32 / Smart Meter Hardware Integration
    # --------------------------------------------------------------------------
    with tab_esp32:
        st.markdown("<div class='section-header-box'><h2>ESP32 / ESP8266 & Smart Meter Integration Architecture</h2><p>Ready-to-deploy hardware schematics, JSON telemetry schemas, and Arduino C++ firmware</p></div>", unsafe_allow_html=True)

        st.markdown("""
            ### 🛠️ Hardware Bill of Materials (BOM)
            1. **Microcontroller:** ESP32-WROOM-32D (Dual-Core 240MHz, 4MB Flash, Wi-Fi & Bluetooth).
            2. **Energy Measurement IC:** PZEM-004T v3.0 (AC 80-260V, 0-100A with TTL UART Modbus RTU).
            3. **Current Sensor:** 100A Split-Core Current Transformer (CT coil).
            4. **5G Cellular Modem (Optional Hardware Path):** SIM8200EA-M2 5G NR Shield or Industrial 5G CPE Gateway.
            5. **Power Supply:** Hi-Link HLK-PM01 5V/3W Step-Down AC-DC Converter.
        """)

        st.markdown("### 📋 JSON Telemetry Payload Schema")
        example_json = {
            "device_id": "DEV_BLD_B_01",
            "timestamp": 1774345200000,
            "voltage": 230.4,
            "current": 24.5,
            "active_power": 5200.0,
            "apparent_power": 5644.8,
            "energy_kwh": 3410.25,
            "frequency": 50.02,
            "power_factor": 0.92,
            "rssi": -62
        }
        st.code(json.dumps(example_json, indent=2), language="json")

        st.markdown("### 💻 Production Arduino C++ Firmware (Ready to Flash)")
        st.code(ESP32_FIRMWARE_SOURCE, language="cpp")
