"""P_311: Knowledge-Driven IoT Fault Diagnosis Assistant.

Module: mqtt/mqtt_subscriber.py
Subscribes to telemetry topics, validates JSON schemas and data types,
safely handles malformed messages without crashing, and prepares readings
for the fault detection engine.
"""

import argparse
import json
import logging
from pathlib import Path
import signal
import sys
from typing import Any, Callable, Dict, Optional, Tuple

# Ensure project root is in sys.path regardless of execution directory
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import paho.mqtt.client as mqtt
from config import (
    MQTT_BROKER_HOST,
    MQTT_BROKER_PORT,
    MQTT_KEEPALIVE_SECONDS,
    MQTT_TELEMETRY_TOPIC,
)

logging.basicConfig(
    stream=sys.stdout,
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("MQTTSubscriber")

_RUNNING = True


def _signal_handler(signum: int, frame: Any) -> None:
    """Handle termination signals (Ctrl+C) gracefully."""
    global _RUNNING
    logger.info("Shutdown signal received (%d). Terminating subscriber cleanly...", signum)
    _RUNNING = False


def validate_telemetry_payload(raw_payload: str | bytes) -> Tuple[bool, Optional[Dict[str, Any]], str]:
    """Validate that raw message bytes/string is well-formed JSON matching the telemetry schema.

    Returns:
        (is_valid, parsed_dict_or_none, error_message_or_empty)
    """
    # 1. Decode UTF-8 string
    if isinstance(raw_payload, bytes):
        try:
            payload_str = raw_payload.decode("utf-8")
        except UnicodeDecodeError as exc:
            return False, None, f"UTF-8 decode error: {exc}"
    else:
        payload_str = raw_payload

    # 2. Parse JSON
    try:
        data = json.loads(payload_str)
    except json.JSONDecodeError as exc:
        return False, None, f"Invalid JSON syntax: {exc}"

    if not isinstance(data, dict):
        return False, None, f"Expected JSON object, got {type(data).__name__}"

    # 3. Validate required fields
    required_fields = ["device_id", "timestamp", "temperature", "vibration", "pressure"]
    missing = [f for f in required_fields if f not in data]
    if missing:
        return False, None, f"Missing required fields: {', '.join(missing)}"

    # 4. Validate types
    if not isinstance(data["device_id"], str) or not data["device_id"].strip():
        return False, None, "Field 'device_id' must be a non-empty string"

    if not isinstance(data["timestamp"], str) or not data["timestamp"].strip():
        return False, None, "Field 'timestamp' must be a non-empty string"

    for num_field in ["temperature", "vibration", "pressure"]:
        val = data[num_field]
        if not isinstance(val, (int, float)) or isinstance(val, bool):
            return False, None, f"Field '{num_field}' must be a number, got {type(val).__name__}"

    return True, data, ""


class TelemetrySubscriber:
    """Manages MQTT subscription, message parsing, and graceful lifecycle."""

    def __init__(
        self,
        host: str = MQTT_BROKER_HOST,
        port: int = MQTT_BROKER_PORT,
        topic: str = MQTT_TELEMETRY_TOPIC,
        on_reading_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
        persist_to_db: bool = False,
    ) -> None:
        self.host = host
        self.port = port
        self.topic = topic
        self.on_reading_callback = on_reading_callback
        self.persist_to_db = persist_to_db

        self.messages_received: int = 0
        self.valid_messages: int = 0
        self.malformed_messages: int = 0

        self.detector = None
        if self.persist_to_db:
            try:
                from diagnosis.fault_detector import FaultDetector
                self.detector = FaultDetector()
            except Exception:
                pass

        self.client = mqtt.Client(
            callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
            client_id="p311_telemetry_subscriber",
        )
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message
        self.client.on_disconnect = self._on_disconnect

    def _on_connect(
        self,
        client: mqtt.Client,
        userdata: Any,
        flags: mqtt.ConnectFlags,
        rc: mqtt.ReasonCode,
        properties: Any = None,
    ) -> None:
        if rc.is_failure:
            logger.error("Failed to connect to MQTT broker: %s", rc)
            return

        logger.info("Connected to Mosquitto broker at %s:%d (Reason: %s)", self.host, self.port, rc)
        client.subscribe(self.topic, qos=1)
        logger.info("Subscribed to telemetry topic: '%s'", self.topic)

    def _on_disconnect(
        self,
        client: mqtt.Client,
        userdata: Any,
        flags: mqtt.DisconnectFlags,
        rc: mqtt.ReasonCode,
        properties: Any = None,
    ) -> None:
        logger.info("Disconnected from MQTT broker (Reason: %s)", rc)

    def _on_message(
        self,
        client: mqtt.Client,
        userdata: Any,
        message: mqtt.MQTTMessage,
    ) -> None:
        self.messages_received += 1
        is_valid, data, err_msg = validate_telemetry_payload(message.payload)

        if not is_valid:
            self.malformed_messages += 1
            raw_sample = message.payload[:100]
            logger.warning(
                "[MALFORMED MESSAGE] %s | Raw payload: %r (Skipped without crashing)",
                err_msg,
                raw_sample,
            )
            return

        self.valid_messages += 1
        logger.info(
            "[RECEIVED] Device=%s | Temp=%.2f C | Vib=%.2f mm/s | Press=%.2f bar",
            data["device_id"],
            data["temperature"],
            data["vibration"],
            data["pressure"],
        )

        if self.persist_to_db:
            fault_status = "normal"
            if self.detector is not None:
                try:
                    detection = self.detector.process_reading(data)
                    if detection and detection.get("has_fault"):
                        fault_status = detection.get("fault_category", "fault_detected")
                except Exception:
                    pass
            try:
                from database.db import insert_sensor_reading
                insert_sensor_reading(data, fault_status=fault_status)
            except Exception as dbe:
                logger.debug("Database insert failed: %s", dbe)

        if self.on_reading_callback is not None:
            try:
                self.on_reading_callback(data)
            except Exception as exc:
                logger.error("Error in downstream reading callback: %s", exc)

    def start(self) -> None:
        """Connect to the broker and start background network loop."""
        logger.info("Connecting to Mosquitto broker at %s:%d...", self.host, self.port)
        self.client.connect(self.host, self.port, keepalive=MQTT_KEEPALIVE_SECONDS)
        self.client.loop_start()

    def stop(self) -> None:
        """Stop background network loop and disconnect."""
        logger.info("Stopping telemetry subscriber...")
        self.client.loop_stop()
        self.client.disconnect()
        logger.info(
            "Subscriber stopped. Total: %d, Valid: %d, Malformed: %d",
            self.messages_received,
            self.valid_messages,
            self.malformed_messages,
        )


def run_subscriber(
    host: str = MQTT_BROKER_HOST,
    port: int = MQTT_BROKER_PORT,
    topic: str = MQTT_TELEMETRY_TOPIC,
    max_messages: Optional[int] = None,
    persist_db: bool = False,
) -> int:
    """Run subscriber loop until Ctrl+C or max_messages reached."""
    global _RUNNING
    _RUNNING = True

    signal.signal(signal.SIGINT, _signal_handler)
    signal.signal(signal.SIGTERM, _signal_handler)

    subscriber = TelemetrySubscriber(host=host, port=port, topic=topic, persist_to_db=persist_db)
    try:
        subscriber.start()
        logger.info("Subscriber active. Waiting for telemetry (Press Ctrl+C to stop)...")
        while _RUNNING:
            if max_messages is not None and subscriber.messages_received >= max_messages:
                logger.info("Reached maximum requested messages (%d). Exiting.", max_messages)
                break
            signal.pause() if hasattr(signal, "pause") else sys.stdout.flush()
            import time
            time.sleep(0.5)
    except KeyboardInterrupt:
        logger.info("KeyboardInterrupt caught.")
    finally:
        subscriber.stop()

    return 0


def main() -> int:
    """CLI argument parser for subscriber."""
    parser = argparse.ArgumentParser(
        description="P_311 MQTT Telemetry Subscriber (Centrifugal Pump)"
    )
    parser.add_argument("--host", default=MQTT_BROKER_HOST, help="MQTT broker host")
    parser.add_argument("--port", type=int, default=MQTT_BROKER_PORT, help="MQTT broker port")
    parser.add_argument("--topic", default=MQTT_TELEMETRY_TOPIC, help="Topic to subscribe")
    parser.add_argument(
        "--persist-db",
        action="store_true",
        default=True,
        help="Persist valid incoming sensor readings to PostgreSQL sensor_readings table (default: True)",
    )
    parser.add_argument(
        "--no-db",
        dest="persist_db",
        action="store_false",
        help="Disable database persistence",
    )
    parser.add_argument(
        "--max-messages",
        type=int,
        default=None,
        help="Exit after receiving N messages (default: run continuously)",
    )
    args = parser.parse_args()
    return run_subscriber(
        host=args.host,
        port=args.port,
        topic=args.topic,
        max_messages=args.max_messages,
        persist_db=args.persist_db,
    )


if __name__ == "__main__":
    sys.exit(main())
