"""
VoltSense 5G - Module 1: IoT Data Acquisition Engine
Handles electrical sensor simulation, device registration, ESP32/ESP8266 firmware architecture, and physics validation.
"""
import time
import random
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple

from config import (
    NOMINAL_VOLTAGE_V,
    NOMINAL_FREQUENCY_HZ,
    TARGET_POWER_FACTOR,
    DEFAULT_CAMPUS_DEVICES
)
from utils.calculations import (
    calculate_apparent_power,
    calculate_active_power,
    calculate_energy_increment_kwh
)
from database.database import DatabaseManager


class SensorSimulator:
    """
    Simulates real-time high-fidelity electrical measurements for campus smart meters.
    Calculations strictly adhere to AC single-phase power physics.
    """
    def __init__(self, db: DatabaseManager):
        self.db = db

    def generate_single_reading(
        self, 
        device_id: str, 
        load_multiplier: float = 1.0, 
        inject_anomaly_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Synthesizes a single instantaneous sensor packet for a specific device.
        """
        device = self.db.get_device(device_id)
        if not device:
            device = {
                "device_id": device_id,
                "nominal_power_w": 5000.0,
                "building": "General Building",
                "room": "Main Panel"
            }

        nominal_w = float(device.get("nominal_power_w", 5000.0))
        now = datetime.now()
        hour = now.hour

        # Diurnal base scaling
        if 8 <= hour <= 18:
            time_factor = 0.75 + 0.25 * np.sin(((hour - 8) / 10.0) * np.pi)
        else:
            time_factor = 0.20 + 0.08 * np.sin((hour / 7.0) * np.pi)

        # Baseline active power with load multiplier and sensor noise
        noise = random.uniform(0.96, 1.04)
        active_power_w = nominal_w * time_factor * load_multiplier * noise

        # Grid parameters
        voltage_v = round(random.gauss(NOMINAL_VOLTAGE_V, 2.0), 1)
        voltage_v = max(210.0, min(245.0, voltage_v))
        frequency_hz = round(random.gauss(NOMINAL_FREQUENCY_HZ, 0.05), 2)
        power_factor = round(random.gauss(TARGET_POWER_FACTOR, 0.015), 3)
        power_factor = max(0.80, min(0.98, power_factor))

        # Handle explicit anomaly injection
        if inject_anomaly_type == "POWER_SPIKE":
            active_power_w = nominal_w * 3.2
        elif inject_anomaly_type == "VOLTAGE_SAG":
            voltage_v = 178.0
        elif inject_anomaly_type == "LOW_POWER_FACTOR":
            power_factor = 0.52
        elif inject_anomaly_type == "VOLTAGE_SURGE":
            voltage_v = 268.0

        # Current calculation: I = P / (V * PF)
        current_a = round(active_power_w / (voltage_v * power_factor), 2)

        # Re-enforce exact physics relationships
        apparent_power_va = calculate_apparent_power(voltage_v, current_a)
        active_power_w = calculate_active_power(voltage_v, current_a, power_factor)

        # Get latest accumulated energy from DB
        latest_df = self.db.get_readings(device_id=device_id, limit=1, order="DESC")
        if not latest_df.empty:
            last_energy = float(latest_df["energy_kwh"].iloc[0])
            last_time = pd.to_datetime(latest_df["timestamp"].iloc[0])
            elapsed_seconds = max(1.0, min(3600.0, (now - last_time.to_pydatetime()).total_seconds()))
        else:
            last_energy = 1000.0
            elapsed_seconds = 3600.0

        # Incremental energy accumulation
        delta_kwh = calculate_energy_increment_kwh(active_power_w, elapsed_seconds)
        new_energy_kwh = round(last_energy + delta_kwh, 4)

        return {
            "device_id": device_id,
            "timestamp": now.strftime("%Y-%m-%d %H:%M:%S"),
            "voltage": voltage_v,
            "current": current_a,
            "active_power": active_power_w,
            "apparent_power": apparent_power_va,
            "energy_kwh": new_energy_kwh,
            "frequency": frequency_hz,
            "power_factor": power_factor,
            "is_simulated": 1,
            "transmission_protocol": "5G_URLLC",
            "latency_ms": round(random.uniform(1.8, 3.8), 2),
            "packet_loss": 0
        }

    def simulate_tick_for_all_devices(self) -> List[Dict[str, Any]]:
        """Generates and commits a real-time tick for all registered active devices."""
        devices = self.db.get_devices()
        new_readings = []
        for dev in devices:
            if dev.get("status") != "OFFLINE":
                reading = self.generate_single_reading(dev["device_id"])
                self.db.insert_reading(reading)
                new_readings.append(reading)
        return new_readings


# ESP32 Integration Specs & Arduino C++ Code Blueprint
ESP32_FIRMWARE_SOURCE = """/*
 * ==============================================================================
 * VoltSense 5G - Smart Energy Meter Firmware (ESP32 / ESP8266 + PZEM-004T v3.0)
 * Protocol: MQTT over 5G Cellular Gateway / Wi-Fi | JSON Telemetry Transmission
 * ==============================================================================
 */

#include <WiFi.h>
#include <PubSubClient.h>
#include <PZEM004Tv30.h>
#include <ArduinoJson.h>

// Hardware Pinout Configuration (HardwareSerial 2)
#define PZEM_RX_PIN 16
#define PZEM_TX_PIN 17
#define STATUS_LED_PIN 2

// Network & MQTT Settings
const char* WIFI_SSID       = "Campus_IoT_5G_Network";
const char* WIFI_PASSWORD   = "VoltSenseSecure#2026";
const char* MQTT_BROKER     = "broker.emqx.io";
const int   MQTT_PORT       = 1883;
const char* MQTT_TOPIC      = "voltsense/v1/telemetry";
const char* DEVICE_ID       = "DEV_BLD_B_01";

HardwareSerial PzemSerial(2);
PZEM004Tv30 pzem(PzemSerial, PZEM_RX_PIN, PZEM_TX_PIN);
WiFiClient espClient;
PubSubClient mqttClient(espClient);

void setup() {
    Serial.begin(115200);
    pinMode(STATUS_LED_PIN, OUTPUT);
    digitalWrite(STATUS_LED_PIN, LOW);
    
    // Connect to 5G Industrial Gateway / Wi-Fi
    Serial.print("Connecting to 5G NR Backhaul: ");
    Serial.println(WIFI_SSID);
    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
    while (WiFi.status() != WL_CONNECTED) {
        delay(500);
        Serial.print(".");
    }
    Serial.println("\\n5G Radio Link Established! IP: " + WiFi.localIP().toString());
    
    mqttClient.setServer(MQTT_BROKER, MQTT_PORT);
}

void reconnectMQTT() {
    while (!mqttClient.connected()) {
        Serial.print("Connecting to VoltSense MQTT Ingestion Broker...");
        if (mqttClient.connect(DEVICE_ID)) {
            Serial.println("CONNECTED!");
            digitalWrite(STATUS_LED_PIN, HIGH);
        } else {
            Serial.print("Failed (rc=");
            Serial.print(mqttClient.state());
            Serial.println("). Retrying in 3s...");
            delay(3000);
        }
    }
}

void loop() {
    if (!mqttClient.connected()) {
        digitalWrite(STATUS_LED_PIN, LOW);
        reconnectMQTT();
    }
    mqttClient.loop();

    // Acquire electrical parameters from PZEM-004T
    float voltage   = pzem.voltage();
    float current   = pzem.current();
    float power     = pzem.power();
    float energy    = pzem.energy();      // in kWh
    float frequency = pzem.frequency();
    float pf        = pzem.pf();

    // Verify sensor response sanity
    if (!isnan(voltage) && !isnan(current) && !isnan(power)) {
        StaticJsonDocument<256> doc;
        doc["device_id"]      = DEVICE_ID;
        doc["timestamp"]      = millis();
        doc["voltage"]        = round(voltage * 10) / 10.0;
        doc["current"]        = round(current * 100) / 100.0;
        doc["active_power"]   = round(power * 10) / 10.0;
        doc["apparent_power"] = round((voltage * current) * 10) / 10.0;
        doc["energy_kwh"]     = round(energy * 1000) / 1000.0;
        doc["frequency"]      = round(frequency * 10) / 10.0;
        doc["power_factor"]   = round(pf * 100) / 100.0;
        doc["rssi"]           = WiFi.RSSI();

        char buffer[256];
        serializeJson(doc, buffer);

        // Publish over 5G Slice URLLC QoS 1
        mqttClient.publish(MQTT_TOPIC, buffer, true);
        Serial.println("Published Telemetry: " + String(buffer));
    } else {
        Serial.println("PZEM Sensor Read Timeout / UART CRC Error!");
    }

    // Telemetry sampling interval: 2000ms
    delay(2000);
}
"""
