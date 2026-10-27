"""P_311: Knowledge-Driven IoT Fault Diagnosis Assistant.

Main Orchestration Entry Point (Stage 8).
Subscribes to live MQTT telemetry, executes explainable anomaly detection,
queries the local RAG knowledge base upon fault confirmation,
synthesizes a grounded diagnostic report via the local LLM,
and persists structured records to data/diagnoses_log.jsonl.
"""

import argparse
import datetime
import json
import logging
from pathlib import Path
import signal
import sys
import time
from typing import Any, Dict, List, Optional

# Ensure project root is in sys.path
_PROJECT_ROOT = Path(__file__).resolve().parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from config import (
    DATA_DIR,
    DEFAULT_DEVICE_ID,
    LLM_DIAGNOSIS_COOLDOWN_SECONDS,
    MQTT_BROKER_HOST,
    MQTT_BROKER_PORT,
    MQTT_TELEMETRY_TOPIC,
    RAG_TOP_K,
)
from database.db import insert_diagnosis, insert_sensor_reading, is_database_available
from diagnosis.fault_detector import FaultDetector
from llm.client import LocalLLMClient
from mqtt.mqtt_subscriber import TelemetrySubscriber
from rag.retriever import TFIDFRetriever

logging.basicConfig(
    stream=sys.stdout,
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("P311_Main")

_RUNNING = True


def _signal_handler(signum: int, frame: Any) -> None:
    """Handle termination signals (Ctrl+C) gracefully."""
    global _RUNNING
    logger.info("Shutdown signal received (%d). Terminating P_311 Assistant cleanly...", signum)
    _RUNNING = False


class FaultDiagnosisPipeline:
    """End-to-end coordinator for MQTT, detection, RAG retrieval, and local LLM reasoning."""

    def __init__(
        self,
        broker_host: str = MQTT_BROKER_HOST,
        broker_port: int = MQTT_BROKER_PORT,
        topic: str = MQTT_TELEMETRY_TOPIC,
        cooldown_seconds: float = LLM_DIAGNOSIS_COOLDOWN_SECONDS,
        top_k: int = RAG_TOP_K,
        max_diagnoses: Optional[int] = None,
    ) -> None:
        self.broker_host = broker_host
        self.broker_port = broker_port
        self.topic = topic
        self.cooldown_seconds = cooldown_seconds
        self.top_k = top_k
        self.max_diagnoses = max_diagnoses

        # Subsystems
        self.detector = FaultDetector()
        self.retriever = TFIDFRetriever()
        self.llm_client = LocalLLMClient()

        # Telemetry & Diagnosis state tracking
        self.total_readings_received = 0
        self.total_diagnoses_generated = 0
        self.last_diagnosis_time: Dict[str, float] = {}

        # Log file paths
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        self.jsonl_log = DATA_DIR / "diagnoses_log.jsonl"
        self.text_log = DATA_DIR / "diagnoses.log"

        # MQTT Subscriber
        self.subscriber = TelemetrySubscriber(
            host=self.broker_host,
            port=self.broker_port,
            topic=self.topic,
            on_reading_callback=self._handle_telemetry,
        )

    def _handle_telemetry(self, reading: Dict[str, Any]) -> None:
        """Callback executed for every incoming valid telemetry reading."""
        self.total_readings_received += 1
        fault_data = self.detector.process_reading(reading)

        # Determine predicted fault status from detector
        fault_status = "normal"
        if fault_data and fault_data.get("has_fault"):
            fault_status = fault_data.get("fault_category", "fault_detected")

        # Persist actual sensor reading to PostgreSQL sensor_readings table
        try:
            reading_to_save = dict(reading)
            reading_to_save["fault_status"] = fault_status
            insert_sensor_reading(reading_to_save, fault_status=fault_status)
        except Exception as dbe:
            logger.debug("Database insert skipped/failed for reading: %s", dbe)

        # If machine is healthy, remain silent and return
        if not fault_data or not fault_data.get("has_fault"):
            return

        category = fault_data.get("fault_category", "unknown")
        now = time.time()
        last_time = self.last_diagnosis_time.get(category, 0.0)
        elapsed = now - last_time

        # Enforce diagnostic cooldown per category to avoid spamming the LLM
        if elapsed < self.cooldown_seconds:
            remaining = self.cooldown_seconds - elapsed
            logger.debug(
                "[COOLDOWN] Fault '%s' persists. Suppressing LLM call for %.1fs.",
                category,
                remaining,
            )
            return

        # Execute RAG Retrieval
        self.last_diagnosis_time[category] = now
        self.total_diagnoses_generated += 1
        query = fault_data.get("query", "")

        logger.info("Executing RAG retrieval for fault: '%s'...", category)
        retrieved_chunks = self.retriever.retrieve(query, top_k=self.top_k)

        # Execute Local LLM Diagnosis
        logger.info("Generating grounded diagnosis via Local LLM...")
        llm_result = self.llm_client.generate(fault_data, retrieved_chunks)

        # Display polished diagnostic report to terminal
        self._display_report(fault_data, retrieved_chunks, llm_result)

        # Persist structured record to data/
        self._persist_record(fault_data, retrieved_chunks, llm_result)

    def _display_report(
        self,
        fault: Dict[str, Any],
        chunks: List[Dict[str, Any]],
        llm_result: Dict[str, Any],
    ) -> None:
        """Render a clean, professional CLI diagnostic banner."""
        sections = llm_result.get("sections", {})
        readings = fault.get("readings", {})
        device_id = fault.get("device_id", DEFAULT_DEVICE_ID)
        category = fault.get("fault_category", "Unknown").upper()

        border = "=" * 78
        print(f"\n{border}")
        print(f"  P_311 INDUSTRIAL FAULT DIAGNOSIS REPORT #{self.total_diagnoses_generated}")
        print(f"  Device: {device_id} | Condition: {category} | Time: {fault.get('timestamp')}")
        print(f"  Telemetry: Temp={readings.get('temperature')}°C | Vib={readings.get('vibration')} mm/s | Press={readings.get('pressure')} bar")
        print(f"  Runtime: {llm_result.get('runtime')} (Latency: {llm_result.get('latency_seconds')}s)")
        print(f"{border}")

        print(f"\n[1. LIKELY FAULT]\n  {sections.get('likely_fault', 'N/A')}\n")
        print(f"[2. WHY - EVIDENCE]\n  {sections.get('why', 'N/A')}\n")
        print(f"[3. RECOMMENDED CHECKS]\n  {sections.get('recommended_checks', 'N/A')}\n")
        print(f"[4. CONFIDENCE & LIMITATIONS]\n  {sections.get('confidence_limitations', 'N/A')}\n")

        print("  Retrieved Knowledge Sources:")
        for c in chunks:
            print(f"   • {c.get('source_file')} (Score: {c.get('score'):.4f}) -> {c.get('section_title')}")
        print(f"{border}\n")

    def _persist_record(
        self,
        fault: Dict[str, Any],
        chunks: List[Dict[str, Any]],
        llm_result: Dict[str, Any],
    ) -> None:
        """Write structured JSONL and formatted text log records."""
        record = {
            "diagnosis_id": self.total_diagnoses_generated,
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "device_id": fault.get("device_id"),
            "fault_category": fault.get("fault_category"),
            "symptoms": fault.get("symptoms"),
            "readings": fault.get("readings"),
            "rolling_stats": fault.get("rolling_stats"),
            "retrieved_sources": [
                {
                    "source_file": c.get("source_file"),
                    "score": c.get("score"),
                    "section": c.get("section_title"),
                }
                for c in chunks
            ],
            "llm_runtime": llm_result.get("runtime"),
            "latency_seconds": llm_result.get("latency_seconds"),
            "diagnosis_text": llm_result.get("response"),
        }

        # Append to JSONL log
        with open(self.jsonl_log, "a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")

        # Persist to PostgreSQL fault_incidents table
        try:
            insert_diagnosis({
                "timestamp": record["timestamp"],
                "device_id": record["device_id"],
                "fault_category": record["fault_category"],
                "symptoms": record["symptoms"],
                "readings": record["readings"],
                "retrieved_sources": record["retrieved_sources"],
                "diagnosis_text": record["diagnosis_text"],
                "likely_fault": llm_result.get("sections", {}).get("likely_fault", ""),
                "why": llm_result.get("sections", {}).get("why", ""),
                "recommended_checks": llm_result.get("sections", {}).get("recommended_checks", ""),
                "confidence_limitations": llm_result.get("sections", {}).get("confidence_limitations", ""),
                "sections": llm_result.get("sections", {}),
                "runtime": record["llm_runtime"],
                "latency_seconds": record["latency_seconds"],
            })
        except Exception as dbe:
            logger.warning("Failed to persist diagnosis report to PostgreSQL: %s", dbe)

        # Append to human-readable text log
        with open(self.text_log, "a", encoding="utf-8") as f:
            f.write(
                f"[{record['timestamp']}] Diagnosis #{self.total_diagnoses_generated} for {record['device_id']}\n"
                f"Category: {record['fault_category']}\n"
                f"Symptoms: {'; '.join(record['symptoms'])}\n"
                f"Top Source: {record['retrieved_sources'][0]['source_file'] if record['retrieved_sources'] else 'None'}\n"
                f"{llm_result.get('response')}\n"
                f"{'-'*70}\n"
            )

    def start(self) -> None:
        """Start the pipeline subscriber."""
        logger.info("Starting Fault Diagnosis Pipeline...")
        logger.info("Broker: %s:%d | Topic: %s", self.broker_host, self.broker_port, self.topic)
        self.subscriber.start()

    def stop(self) -> None:
        """Stop the pipeline cleanly."""
        logger.info("Shutting down Fault Diagnosis Pipeline...")
        self.subscriber.stop()
        logger.info(
            "Shutdown complete. Total telemetry messages: %d, Diagnoses generated: %d.",
            self.total_readings_received,
            self.total_diagnoses_generated,
        )


def run_pipeline(
    host: str = MQTT_BROKER_HOST,
    port: int = MQTT_BROKER_PORT,
    topic: str = MQTT_TELEMETRY_TOPIC,
    cooldown: float = LLM_DIAGNOSIS_COOLDOWN_SECONDS,
    max_diagnoses: Optional[int] = None,
) -> int:
    """Run pipeline until Ctrl+C or max_diagnoses reached."""
    global _RUNNING
    _RUNNING = True

    signal.signal(signal.SIGINT, _signal_handler)
    signal.signal(signal.SIGTERM, _signal_handler)

    pipeline = FaultDiagnosisPipeline(
        broker_host=host,
        broker_port=port,
        topic=topic,
        cooldown_seconds=cooldown,
        max_diagnoses=max_diagnoses,
    )

    try:
        pipeline.start()
        logger.info("Assistant is listening for telemetry. (Press Ctrl+C to stop)...")
        while _RUNNING:
            if max_diagnoses is not None and pipeline.total_diagnoses_generated >= max_diagnoses:
                logger.info("Target diagnosis count reached (%d). Exiting.", max_diagnoses)
                break
            time.sleep(0.5)
    except KeyboardInterrupt:
        logger.info("KeyboardInterrupt caught.")
    finally:
        pipeline.stop()

    return 0


def main() -> int:
    """Parse CLI arguments and launch assistant."""
    parser = argparse.ArgumentParser(
        description="P_311: Knowledge-Driven IoT Fault Diagnosis Assistant (Main)"
    )
    parser.add_argument("--broker", default=MQTT_BROKER_HOST, help="MQTT broker host")
    parser.add_argument("--port", type=int, default=MQTT_BROKER_PORT, help="MQTT broker port")
    parser.add_argument("--topic", default=MQTT_TELEMETRY_TOPIC, help="MQTT telemetry topic")
    parser.add_argument(
        "--cooldown",
        type=float,
        default=LLM_DIAGNOSIS_COOLDOWN_SECONDS,
        help="Seconds between repeated diagnoses for same fault (default: 30.0)",
    )
    parser.add_argument(
        "--max-diagnoses",
        type=int,
        default=None,
        help="Exit after generating N diagnoses (default: run indefinitely)",
    )

    args = parser.parse_args()
    return run_pipeline(
        host=args.broker,
        port=args.port,
        topic=args.topic,
        cooldown=args.cooldown,
        max_diagnoses=args.max_diagnoses,
    )


if __name__ == "__main__":
    sys.exit(main())
