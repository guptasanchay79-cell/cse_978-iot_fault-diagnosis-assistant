"""P_311: Knowledge-Driven IoT Fault Diagnosis Assistant.

Unit and integration tests for Stage 2 MQTT telemetry pipeline.
Tests payload validation, broker connectivity, and malformed message resilience.
"""

import json
import time
import unittest
import paho.mqtt.client as mqtt

from config import (
    DEFAULT_DEVICE_ID,
    MQTT_BROKER_HOST,
    MQTT_BROKER_PORT,
    MQTT_TELEMETRY_TOPIC,
)
from mqtt.mqtt_subscriber import TelemetrySubscriber, validate_telemetry_payload
from mqtt.sensor_simulator import generate_baseline_telemetry


class TestPayloadValidation(unittest.TestCase):
    """Test schema and data-type validation logic for MQTT payloads."""

    def test_valid_payload_dict(self):
        """Test that a well-formed telemetry payload validates successfully."""
        data = generate_baseline_telemetry(device_id="pump_test_01")
        json_bytes = json.dumps(data).encode("utf-8")
        is_valid, parsed, err = validate_telemetry_payload(json_bytes)
        self.assertTrue(is_valid)
        self.assertIsNotNone(parsed)
        self.assertEqual(err, "")
        self.assertEqual(parsed["device_id"], "pump_test_01")
        self.assertIsInstance(parsed["temperature"], (int, float))
        self.assertIsInstance(parsed["vibration"], (int, float))
        self.assertIsInstance(parsed["pressure"], (int, float))

    def test_invalid_json_syntax(self):
        """Test that broken JSON syntax is rejected cleanly."""
        bad_json = b"{device_id: pump_01, bad_syntax"
        is_valid, parsed, err = validate_telemetry_payload(bad_json)
        self.assertFalse(is_valid)
        self.assertIsNone(parsed)
        self.assertIn("Invalid JSON syntax", err)

    def test_missing_required_field(self):
        """Test that payloads missing expected sensor fields are rejected."""
        incomplete = {
            "device_id": "pump_01",
            "timestamp": "2026-10-01T00:00:00Z",
            "temperature": 55.0,
            # missing vibration and pressure
        }
        is_valid, parsed, err = validate_telemetry_payload(json.dumps(incomplete))
        self.assertFalse(is_valid)
        self.assertIsNone(parsed)
        self.assertIn("Missing required fields", err)
        self.assertIn("vibration", err)

    def test_non_numeric_sensor_reading(self):
        """Test that strings passed as sensor values are rejected."""
        non_numeric = {
            "device_id": "pump_01",
            "timestamp": "2026-10-01T00:00:00Z",
            "temperature": "OVERHEATING_HIGH",
            "vibration": 1.2,
            "pressure": 5.0,
        }
        is_valid, parsed, err = validate_telemetry_payload(json.dumps(non_numeric))
        self.assertFalse(is_valid)
        self.assertIsNone(parsed)
        self.assertIn("Field 'temperature' must be a number", err)

    def test_boolean_sensor_reading(self):
        """Test that boolean values (which inherit from int in Python) are rejected."""
        bool_val = {
            "device_id": "pump_01",
            "timestamp": "2026-10-01T00:00:00Z",
            "temperature": 50.0,
            "vibration": True,
            "pressure": 5.0,
        }
        is_valid, parsed, err = validate_telemetry_payload(json.dumps(bool_val))
        self.assertFalse(is_valid)
        self.assertIn("Field 'vibration' must be a number", err)


class TestMQTTBrokerEndToEnd(unittest.TestCase):
    """Integration test verifying publish and subscribe over the local Mosquitto broker."""

    def test_end_to_end_delivery_and_malformed_handling(self):
        """Publish valid and malformed messages, verifying subscriber processes both safely."""
        test_topic = f"{MQTT_TELEMETRY_TOPIC}/stage2_test"
        received_readings = []

        def on_reading(data):
            received_readings.append(data)

        # 1. Start subscriber
        subscriber = TelemetrySubscriber(
            host=MQTT_BROKER_HOST,
            port=MQTT_BROKER_PORT,
            topic=test_topic,
            on_reading_callback=on_reading,
        )
        subscriber.start()
        time.sleep(1.0)  # Allow MQTT connection & subscription to establish

        # 2. Publisher client
        publisher = mqtt.Client(
            callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
            client_id="test_publisher",
        )
        publisher.connect(MQTT_BROKER_HOST, MQTT_BROKER_PORT, keepalive=30)
        publisher.loop_start()

        try:
            # Send 2 valid messages
            for i in range(2):
                valid_data = {
                    "device_id": DEFAULT_DEVICE_ID,
                    "timestamp": f"2026-10-01T00:00:0{i}Z",
                    "temperature": 52.0 + i,
                    "vibration": 1.5 + (i * 0.1),
                    "pressure": 5.0 - (i * 0.1),
                }
                publisher.publish(test_topic, json.dumps(valid_data), qos=1)

            # Send 1 malformed JSON message (syntax error)
            publisher.publish(test_topic, "NOT_JSON_AT_ALL_<<<MALFORMED>>>", qos=1)

            # Send 1 malformed schema message (missing pressure)
            publisher.publish(test_topic, json.dumps({"device_id": "test", "timestamp": "now"}), qos=1)

            # Send 1 more valid message
            last_valid = {
                "device_id": DEFAULT_DEVICE_ID,
                "timestamp": "2026-10-01T00:00:03Z",
                "temperature": 54.0,
                "vibration": 1.8,
                "pressure": 4.9,
            }
            publisher.publish(test_topic, json.dumps(last_valid), qos=1)

            # Wait for message delivery
            time.sleep(2.0)

            # Assertions
            self.assertEqual(subscriber.messages_received, 5)
            self.assertEqual(subscriber.valid_messages, 3)
            self.assertEqual(subscriber.malformed_messages, 2)
            self.assertEqual(len(received_readings), 3)

        finally:
            publisher.loop_stop()
            publisher.disconnect()
            subscriber.stop()


if __name__ == "__main__":
    unittest.main()
