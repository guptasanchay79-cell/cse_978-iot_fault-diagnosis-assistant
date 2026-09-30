"""P_311: Knowledge-Driven IoT Fault Diagnosis Assistant.

Main entry point module.
Coordinates the end-to-end telemetry subscription, fault detection,
knowledge base retrieval, and local LLM diagnosis pipeline.
"""

import sys
import logging
from config import (
    MQTT_BROKER_HOST,
    MQTT_BROKER_PORT,
    MQTT_TELEMETRY_TOPIC,
    DEFAULT_DEVICE_ID,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("P311_Main")


def main() -> int:
    """Print system status and explain pipeline architecture."""
    logger.info("==============================================================")
    logger.info("P_311: Knowledge-Driven IoT Fault Diagnosis Assistant")
    logger.info("Status: Stage 1 Baseline Verified")
    logger.info("Broker Target: %s:%d", MQTT_BROKER_HOST, MQTT_BROKER_PORT)
    logger.info("Telemetry Topic: %s", MQTT_TELEMETRY_TOPIC)
    logger.info("Monitored Device: %s", DEFAULT_DEVICE_ID)
    logger.info("==============================================================")
    logger.info(
        "Run 'python mqtt/sensor_simulator.py' to generate telemetry (Stage 2/3)."
    )
    logger.info(
        "Full real-time streaming pipeline will be orchestrated in Stage 8."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
