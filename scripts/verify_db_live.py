"""P_311: Knowledge-Driven IoT Fault Diagnosis Assistant.

Verification Script for Windows PostgreSQL:
1. Verifies connectivity to PostgreSQL on Windows.
2. Verifies database and table existence (fault_incidents, telemetry_readings).
3. Inserts a test telemetry record and reads it back.
4. Inserts a test diagnosis record and reads it back.
5. Tests the retention pruning procedure.
"""

from datetime import datetime, timezone
import json
import logging
from pathlib import Path
import sys

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from db.connection import get_db_connection, is_database_available
from db.repository import (
    get_recent_diagnoses,
    insert_diagnosis,
    insert_telemetry_batch,
    prune_old_telemetry,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] VerifyLive: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    stream=sys.stdout,
)
logger = logging.getLogger("VerifyLive")


def run_checks() -> bool:
    logger.info("--- Step 1: Checking PostgreSQL Connectivity ---")
    if not is_database_available(force_check=True):
        logger.error("Database connection failed!")
        return False
    logger.info("PASS: Database is reachable and responding.")

    logger.info("--- Step 2: Verifying Tables ---")
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                ORDER BY table_name;
            """)
            tables = [row["table_name"] for row in cur.fetchall()]
            logger.info(f"Public tables found: {tables}")
            if "fault_incidents" not in tables or "telemetry_readings" not in tables:
                logger.error("Required tables missing!")
                return False
    logger.info("PASS: All required tables exist.")

    logger.info("--- Step 3: Insert and Read-Back Telemetry Record ---")
    now_iso = datetime.now(timezone.utc).isoformat()
    test_reading = {
        "device_id": "test_pump_verify",
        "timestamp": now_iso,
        "temperature": 56.78,
        "vibration": 1.45,
        "pressure": 5.12,
        "mode": "normal",
    }
    inserted_count = insert_telemetry_batch([test_reading])
    if inserted_count != 1:
        logger.error(f"Failed to insert test telemetry record! Count: {inserted_count}")
        return False

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM telemetry_readings WHERE device_id = %s ORDER BY timestamp DESC LIMIT 1;",
                ("test_pump_verify",),
            )
            read_back = cur.fetchone()
            if not read_back:
                logger.error("Could not read back inserted telemetry record!")
                return False
            logger.info(f"Read back telemetry: {read_back['device_id']}, T={read_back['temperature']}, V={read_back['vibration']}, P={read_back['pressure']}")
            assert abs(read_back["temperature"] - 56.78) < 1e-4
            assert abs(read_back["vibration"] - 1.45) < 1e-4
            assert abs(read_back["pressure"] - 5.12) < 1e-4
    logger.info("PASS: Telemetry record inserted and read back successfully.")

    logger.info("--- Step 4: Insert and Read-Back Diagnosis Record ---")
    test_diag_ts = datetime.now(timezone.utc).isoformat()
    test_diag = {
        "timestamp": test_diag_ts,
        "device_id": "test_pump_verify",
        "fault_category": "bearing_wear",
        "symptoms": ["vibration 4.8 mm/s exceeding ISO threshold"],
        "readings": {"temperature": 58.5, "vibration": 4.8, "pressure": 5.0},
        "retrieved_sources": [{"source": "KB01_bearing_inner_raceway_fatigue.md", "section": "Diagnostics", "score": 0.32}],
        "diagnosis_text": "### 1. Likely Fault\nBearing Inner Raceway Degradation\n",
        "likely_fault": "Bearing Inner Raceway Degradation",
        "why": "Vibration levels exceed ISO 10816 Zone D danger limit of 4.5 mm/s.",
        "recommended_checks": "1. Inspect bearing lubrication.\n2. Execute LOTO.",
        "confidence_limitations": "Confidence: High.",
        "sections": {
            "likely_fault": "Bearing Inner Raceway Degradation",
            "why": "Vibration levels exceed ISO 10816 Zone D danger limit of 4.5 mm/s.",
            "recommended_checks": "1. Inspect bearing lubrication.\n2. Execute LOTO.",
            "confidence_limitations": "Confidence: High.",
        },
        "runtime": "grounded_synthesis_fallback",
        "latency_seconds": 0.45,
    }
    inserted_diag = insert_diagnosis(test_diag)
    if not inserted_diag:
        logger.error("Failed to insert diagnosis record!")
        return False

    recent = get_recent_diagnoses(limit=5)
    matching = [d for d in recent if d["device_id"] == "test_pump_verify"]
    if not matching:
        logger.error("Could not read back test diagnosis record!")
        return False
    rec = matching[-1]
    logger.info(f"Read back diagnosis: {rec['device_id']}, {rec['fault_category']}, likely_fault='{rec.get('likely_fault')}'")
    assert rec["fault_category"] == "bearing_wear"
    assert rec["likely_fault"] == "Bearing Inner Raceway Degradation"
    assert isinstance(rec["timestamp"], str)
    logger.info("PASS: Diagnosis record inserted and read back successfully.")

    logger.info("--- Step 5: Test Retention Pruning ---")
    deleted = prune_old_telemetry(retention_days=7)
    logger.info(f"Pruning executed safely. Rows pruned: {deleted}")
    logger.info("PASS: Retention pruning function operational.")

    # Clean up test records
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM telemetry_readings WHERE device_id = 'test_pump_verify';")
            cur.execute("DELETE FROM fault_incidents WHERE device_id = 'test_pump_verify';")
    logger.info("Cleaned up test records.")

    logger.info("ALL VERIFICATION CHECKS PASSED SUCCESSFULLY!")
    return True


if __name__ == "__main__":
    if not run_checks():
        sys.exit(1)
