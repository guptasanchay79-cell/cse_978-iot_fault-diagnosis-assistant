"""P_311: Stage 2 Live Demonstration Script.

Runs the subscriber and publisher concurrently to demonstrate:
1. Matching Published and Received telemetry lines.
2. Graceful logging and skipping of malformed payloads without crashing.
"""

import subprocess
import sys
import time
from pathlib import Path

# Add project root to sys.path so config and mqtt modules can be imported
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import paho.mqtt.client as mqtt
from config import MQTT_BROKER_HOST, MQTT_BROKER_PORT, MQTT_TELEMETRY_TOPIC

def main():
    print("=== STAGE 2 DEMO: LAUNCHING SUBSCRIBER ===")
    sub_proc = subprocess.Popen(
        [sys.executable, "mqtt/mqtt_subscriber.py", "--max-messages", "5"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    time.sleep(1.5)  # Let subscriber subscribe

    print("\n=== LAUNCHING SENSOR SIMULATOR (3 Valid Messages) ===")
    pub_proc = subprocess.run(
        [sys.executable, "mqtt/sensor_simulator.py", "--count", "3", "--interval", "0.5"],
        capture_output=True,
        text=True,
    )
    print(pub_proc.stdout)

    print("=== INJECTING 2 DELIBERATELY MALFORMED MESSAGES ===")
    bad_client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2)
    bad_client.connect(MQTT_BROKER_HOST, MQTT_BROKER_PORT)
    bad_client.publish(MQTT_TELEMETRY_TOPIC, "CORRUPT_RAW_DATA_12345!@#$%", qos=1)
    bad_client.publish(MQTT_TELEMETRY_TOPIC, '{"device_id": "test_missing_fields", "timestamp": "2026-10-01T00:00:00Z"}', qos=1)
    bad_client.disconnect()
    print("Injected: 1 non-JSON string, 1 schema-incomplete JSON.\n")

    sub_stdout, _ = sub_proc.communicate(timeout=10)
    print("=== SUBSCRIBER OUTPUT (Captured from Background Process) ===")
    print(sub_stdout)
    print("=== STAGE 2 DEMO COMPLETE ===")

if __name__ == "__main__":
    main()
