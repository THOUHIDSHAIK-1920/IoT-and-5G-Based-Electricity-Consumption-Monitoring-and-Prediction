"""
VoltSense 5G - Module 1: 5G Communication Layer & MQTT Ingestion Engine
Provides 3GPP Rel-16 network slicing simulation and real-world MQTT broker connectivity.
"""
import time
import json
import random
import threading
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime

from config import FIVE_G_PROFILES
from database.database import DatabaseManager
from utils.validation import validate_reading_dict

# Optional paho-mqtt integration
try:
    import paho.mqtt.client as mqtt
    PAHO_AVAILABLE = True
except ImportError:
    PAHO_AVAILABLE = False


class Communication5GManager:
    """
    Simulates 5G New Radio (NR) network slicing behavior and bridges to live MQTT brokers.
    """
    def __init__(self, db: DatabaseManager):
        self.db = db
        self.active_slice = "URLLC"
        self.packet_counter = 0
        self.total_bytes = 0
        self.packet_loss_count = 0
        self.last_transmission_time = None
        self.status = "ONLINE (SIMULATED 5G NR)"
        
        # Real MQTT Broker state
        self.mqtt_connected = False
        self.mqtt_broker_host = "broker.emqx.io"
        self.mqtt_broker_port = 1883
        self.mqtt_topic = "voltsense/v1/telemetry"
        self.mqtt_client = None
        self.mqtt_thread = None

    def set_active_slice(self, slice_key: str):
        """Switches 5G network slicing emulation profile."""
        if slice_key in FIVE_G_PROFILES:
            self.active_slice = slice_key

    def get_slice_info(self) -> Dict[str, Any]:
        """Returns active 5G slice characteristics."""
        return FIVE_G_PROFILES.get(self.active_slice, FIVE_G_PROFILES["URLLC"])

    def transmit_reading(self, reading_dict: Dict[str, Any]) -> Dict[str, Any]:
        """
        Emulates transmission of an IoT reading across the selected 5G network slice.
        Calculates mathematical delay, jitter, packet size, and delivery verification.
        """
        profile = self.get_slice_info()
        self.packet_counter += 1

        # Calculate latency based on slice profile distribution
        base_latency = random.uniform(profile["latency_min_ms"], profile["latency_max_ms"])
        jitter = random.uniform(-profile["jitter_ms"], profile["jitter_ms"])
        latency_ms = round(max(0.8, base_latency + jitter), 2)

        # Check simulated packet loss
        is_dropped = (random.random() < profile["packet_loss_rate"])
        if is_dropped:
            self.packet_loss_count += 1

        # Approximate payload size in bytes
        payload_str = json.dumps(reading_dict)
        payload_bytes = len(payload_str.encode('utf-8'))
        self.total_bytes += payload_bytes
        self.last_transmission_time = datetime.now()

        # Update telemetry packet with transmission headers
        transmitted_packet = reading_dict.copy()
        transmitted_packet["transmission_protocol"] = f"5G_{self.active_slice}"
        transmitted_packet["latency_ms"] = latency_ms
        transmitted_packet["packet_loss"] = 1 if is_dropped else 0

        # Persist to DB if not dropped
        if not is_dropped:
            self.db.insert_reading(transmitted_packet)

        return {
            "packet_id": self.packet_counter,
            "status": "DROPPED (CHANNEL ERROR)" if is_dropped else "DELIVERED (ACK 200)",
            "latency_ms": latency_ms,
            "slice": profile["name"],
            "slice_id": profile["slice_id"],
            "payload_bytes": payload_bytes,
            "bandwidth_utilization_kbps": round(payload_bytes * 8 / (latency_ms + 0.1), 1),
            "timestamp": self.last_transmission_time.strftime("%H:%M:%S.%f")[:-3],
            "is_simulated": True
        }

    def get_network_telemetry_stats(self) -> Dict[str, Any]:
        """Returns consolidated network metrics for UI dashboard."""
        profile = self.get_slice_info()
        loss_pct = (self.packet_loss_count / max(1, self.packet_counter)) * 100.0

        return {
            "active_slice_key": self.active_slice,
            "active_slice_name": profile["name"],
            "slice_id": profile["slice_id"],
            "status": self.status,
            "packet_count": self.packet_counter,
            "total_kbytes": round(self.total_bytes / 1024.0, 2),
            "loss_pct": round(loss_pct, 4),
            "avg_latency_ms": round((profile["latency_min_ms"] + profile["latency_max_ms"]) / 2.0, 1),
            "last_transmission": self.last_transmission_time.strftime("%Y-%m-%d %H:%M:%S") if self.last_transmission_time else "Awaiting Data",
            "is_simulated": True,
            "mqtt_connected": self.mqtt_connected,
            "mqtt_broker": f"{self.mqtt_broker_host}:{self.mqtt_broker_port}"
        }

    # ---------------------------------------------------------
    # Live MQTT Broker Client
    # ---------------------------------------------------------
    def connect_mqtt_broker(self, host: str, port: int, topic: str) -> Tuple[bool, str]:
        """Initiates real MQTT connection to specified broker."""
        if not PAHO_AVAILABLE:
            return False, "paho-mqtt library is not installed in the environment."

        try:
            self.mqtt_broker_host = host
            self.mqtt_broker_port = port
            self.mqtt_topic = topic

            def on_connect(client, userdata, flags, rc, properties=None):
                if rc == 0:
                    self.mqtt_connected = True
                    client.subscribe(self.mqtt_topic)
                    self.db.log_mqtt("SYSTEM", f"Subscribed to topic: {self.mqtt_topic}", qos=1)

            def on_message(client, userdata, msg):
                try:
                    payload_raw = msg.payload.decode("utf-8")
                    data = json.loads(payload_raw)
                    # Validate and persist
                    is_valid, errors = validate_reading_dict(data)
                    if is_valid:
                        data["is_simulated"] = 0
                        data["transmission_protocol"] = "LIVE_MQTT"
                        self.db.insert_reading(data)
                        self.db.log_mqtt(msg.topic, f"Successfully parsed reading from {data.get('device_id')}")
                    else:
                        self.db.log_mqtt(msg.topic, f"Validation warning: {errors}")
                except Exception as ex:
                    self.db.log_mqtt(msg.topic, f"Parse error: {str(ex)}")

            client_id = f"voltsense-server-{random.randint(1000, 9999)}"
            # Handle paho-mqtt v2 vs v1 callback API
            try:
                self.mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=client_id)
            except AttributeError:
                self.mqtt_client = mqtt.Client(client_id=client_id)

            self.mqtt_client.on_connect = on_connect
            self.mqtt_client.on_message = on_message

            self.mqtt_client.connect_async(self.mqtt_broker_host, self.mqtt_broker_port, 60)
            self.mqtt_client.loop_start()
            self.mqtt_connected = True
            return True, f"Connected asynchronously to MQTT broker at {host}:{port}"
        except Exception as e:
            self.mqtt_connected = False
            return False, f"MQTT connection failed: {str(e)}"

    def disconnect_mqtt_broker(self):
        """Disconnects live MQTT client."""
        if self.mqtt_client:
            try:
                self.mqtt_client.loop_stop()
                self.mqtt_client.disconnect()
            except Exception:
                pass
            self.mqtt_connected = False

    def publish_test_mqtt_packet(self, device_id: str, power_w: float) -> Tuple[bool, str]:
        """Publishes a test packet over MQTT to verify broker loopback."""
        if not self.mqtt_connected or not self.mqtt_client:
            return False, "MQTT client is not connected."

        payload = {
            "device_id": device_id,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "voltage": 230.2,
            "current": round(power_w / (230.2 * 0.92), 2),
            "active_power": power_w,
            "apparent_power": round(power_w / 0.92, 1),
            "energy_kwh": 1250.5,
            "frequency": 50.0,
            "power_factor": 0.92,
            "is_simulated": 0
        }
        res = self.mqtt_client.publish(self.mqtt_topic, json.dumps(payload), qos=1)
        return True, f"Dispatched test telemetry packet (MID: {res.mid})"
