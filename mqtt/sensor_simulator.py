"""P_311: Knowledge-Driven IoT Fault Diagnosis Assistant.

Module: mqtt/sensor_simulator.py
Simulates IoT telemetry for an industrial centrifugal pump and publishes
structured JSON messages over MQTT to the Mosquitto broker.
"""

import argparse
import datetime
import json
import logging
from pathlib import Path
import random
import signal
import sys
import time
from typing import Any, Dict

# Ensure project root is in sys.path regardless of execution directory
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import paho.mqtt.client as mqtt
from config import (
    DEFAULT_DEVICE_ID,
    MQTT_BROKER_HOST,
    MQTT_BROKER_PORT,
    MQTT_KEEPALIVE_SECONDS,
    MQTT_TELEMETRY_TOPIC,
    PRESSURE_NORMAL_MAX,
    PRESSURE_NORMAL_MIN,
    TELEMETRY_PUBLISH_INTERVAL,
    TEMP_NORMAL_MAX,
    TEMP_NORMAL_MIN,
    VIB_NORMAL_MAX,
    VIB_NORMAL_MIN,
)

logging.basicConfig(
    stream=sys.stdout,
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("SensorSimulator")

# Global flag for graceful termination
_RUNNING = True


def _signal_handler(signum: int, frame: Any) -> None:
    """Handle termination signals (Ctrl+C) gracefully."""
    global _RUNNING
    logger.info("Shutdown signal received (%d). Terminating simulator cleanly...", signum)
    _RUNNING = False


def generate_baseline_telemetry(device_id: str = DEFAULT_DEVICE_ID) -> Dict[str, Any]:
    """Generate a single healthy baseline telemetry reading formatted as a dictionary.

    Values drift smoothly within the nominal healthy ranges defined in config.py.
    """
    timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
    # Baseline normal values with realistic precision
    temp = round(random.uniform(TEMP_NORMAL_MIN + 3.0, TEMP_NORMAL_MAX - 5.0), 2)
    vib = round(random.uniform(VIB_NORMAL_MIN + 0.2, VIB_NORMAL_MAX - 0.3), 2)
    pressure = round(random.uniform(PRESSURE_NORMAL_MIN + 0.3, PRESSURE_NORMAL_MAX - 0.3), 2)

    return {
        "device_id": device_id,
        "timestamp": timestamp,
        "temperature": temp,
        "vibration": vib,
        "pressure": pressure,
    }


def on_connect(
    client: mqtt.Client,
    userdata: Any,
    flags: mqtt.ConnectFlags,
    rc: mqtt.ReasonCode,
    properties: Any = None,
) -> None:
    """Paho MQTT 2.x on_connect callback."""
    if rc.is_failure:
        logger.error("Failed to connect to MQTT broker: %s", rc)
    else:
        logger.info(
            "Connected to Mosquitto broker at %s:%d (Reason: %s)",
            MQTT_BROKER_HOST,
            MQTT_BROKER_PORT,
            rc,
        )


def on_publish(
    client: mqtt.Client,
    userdata: Any,
    mid: int,
    rc: mqtt.ReasonCode = None,
    properties: Any = None,
) -> None:
    """Paho MQTT 2.x on_publish callback."""
    logger.debug("Message MID %d successfully acknowledged by broker.", mid)


def run_simulator(
    host: str = MQTT_BROKER_HOST,
    port: int = MQTT_BROKER_PORT,
    topic: str = MQTT_TELEMETRY_TOPIC,
    device_id: str = DEFAULT_DEVICE_ID,
    interval: float = TELEMETRY_PUBLISH_INTERVAL,
    count: int | None = None,
) -> int:
    """Run the telemetry simulator loop publishing JSON telemetry messages."""
    global _RUNNING
    _RUNNING = True

    # Register OS signal handlers for clean shutdown
    signal.signal(signal.SIGINT, _signal_handler)
    signal.signal(signal.SIGTERM, _signal_handler)

    # Initialize Paho MQTT Client using 2.x API
    client = mqtt.Client(
        callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
        client_id=f"simulator_{device_id}",
    )
    client.on_connect = on_connect
    client.on_publish = on_publish

    try:
        logger.info("Connecting to broker at %s:%d...", host, port)
        client.connect(host, port, keepalive=MQTT_KEEPALIVE_SECONDS)
        client.loop_start()
    except Exception as exc:
        logger.error("Broker connection failed: %s", exc)
        return 1

    published_count = 0
    try:
        logger.info(
            "Beginning telemetry streaming on topic '%s' (interval=%.1fs, count=%s)...",
            topic,
            interval,
            "infinite" if count is None else count,
        )
        while _RUNNING:
            payload_dict = generate_baseline_telemetry(device_id=device_id)
            payload_str = json.dumps(payload_dict)

            result = client.publish(topic, payload_str, qos=1)
            result.wait_for_publish(timeout=5.0)

            logger.info(
                "[PUBLISHED] Device=%s | Temp=%.2f C | Vib=%.2f mm/s | Press=%.2f bar",
                payload_dict["device_id"],
                payload_dict["temperature"],
                payload_dict["vibration"],
                payload_dict["pressure"],
            )

            published_count += 1
            if count is not None and published_count >= count:
                logger.info("Reached target message count (%d). Stopping simulator.", count)
                break

            time.sleep(interval)
    except KeyboardInterrupt:
        logger.info("KeyboardInterrupt received.")
    finally:
        logger.info("Disconnecting simulator client from broker...")
        client.loop_stop()
        client.disconnect()
        logger.info("Simulator shutdown complete. Total messages published: %d", published_count)

    return 0


def main() -> int:
    """Parse command line arguments and execute simulator."""
    parser = argparse.ArgumentParser(
        description="P_311 IoT Telemetry Simulator (Centrifugal Pump)"
    )
    parser.add_argument(
        "--host", default=MQTT_BROKER_HOST, help="MQTT broker host (default: from config.py)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=MQTT_BROKER_PORT,
        help="MQTT broker port (default: from config.py)",
    )
    parser.add_argument(
        "--topic",
        default=MQTT_TELEMETRY_TOPIC,
        help="MQTT topic to publish (default: from config.py)",
    )
    parser.add_argument(
        "--device-id",
        default=DEFAULT_DEVICE_ID,
        help="Device ID identifier (default: from config.py)",
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=TELEMETRY_PUBLISH_INTERVAL,
        help="Publishing interval in seconds (default: 1.0)",
    )
    parser.add_argument(
        "--count",
        type=int,
        default=None,
        help="Total messages to publish before exit (default: infinite)",
    )

    args = parser.parse_args()
    return run_simulator(
        host=args.host,
        port=args.port,
        topic=args.topic,
        device_id=args.device_id,
        interval=args.interval,
        count=args.count,
    )


if __name__ == "__main__":
    sys.exit(main())
