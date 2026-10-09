"""P_311: Knowledge-Driven IoT Fault Diagnosis Assistant.

Data repository layer providing access to PostgreSQL persistence.
All functions fail gracefully if the database is unavailable, returning fallback defaults.
"""

from datetime import datetime
import json
import logging
from typing import Any, Dict, List, Optional

from config import TELEMETRY_RETENTION_DAYS
from db.connection import get_db_connection, is_database_available

logger = logging.getLogger("DatabaseRepository")


def insert_diagnosis(record: Dict[str, Any]) -> bool:
    """Insert a single diagnostic record into fault_incidents table.
    
    Returns True if successfully inserted, False otherwise.
    """
    if not is_database_available():
        return False

    sql = """
        INSERT INTO fault_incidents (
            timestamp, device_id, fault_category, symptoms,
            temperature, vibration, pressure, retrieved_sources,
            diagnosis_text, likely_fault, why, recommended_checks,
            confidence_limitations, sections, runtime, latency_seconds
        ) VALUES (
            %(timestamp)s, %(device_id)s, %(fault_category)s, %(symptoms)s,
            %(temperature)s, %(vibration)s, %(pressure)s, %(retrieved_sources)s,
            %(diagnosis_text)s, %(likely_fault)s, %(why)s, %(recommended_checks)s,
            %(confidence_limitations)s, %(sections)s, %(runtime)s, %(latency_seconds)s
        )
        ON CONFLICT (device_id, timestamp) DO NOTHING;
    """
    readings = record.get("readings") or {}
    symptoms = record.get("symptoms", [])
    retrieved_sources = record.get("retrieved_sources", [])
    sections = record.get("sections") or {}

    likely_fault = record.get("likely_fault") or sections.get("likely_fault") or sections.get("Likely Fault") or ""
    why = record.get("why") or sections.get("why") or sections.get("Why") or ""
    recommended_checks = record.get("recommended_checks") or sections.get("recommended_checks") or sections.get("Recommended Checks") or ""
    confidence_limitations = record.get("confidence_limitations") or sections.get("confidence_limitations") or sections.get("Confidence and Limitations") or ""

    # Ensure sections object has all keys populated
    if isinstance(sections, dict):
        sections_dict = dict(sections)
        sections_dict.setdefault("likely_fault", likely_fault)
        sections_dict.setdefault("why", why)
        sections_dict.setdefault("recommended_checks", recommended_checks)
        sections_dict.setdefault("confidence_limitations", confidence_limitations)
    else:
        sections_dict = {
            "likely_fault": likely_fault,
            "why": why,
            "recommended_checks": recommended_checks,
            "confidence_limitations": confidence_limitations,
        }

    params = {
        "timestamp": record.get("timestamp"),
        "device_id": record.get("device_id", "unknown_device"),
        "fault_category": record.get("fault_category", "unknown"),
        "symptoms": json.dumps(symptoms) if isinstance(symptoms, (list, dict)) else symptoms,
        "temperature": float(readings.get("temperature")) if readings.get("temperature") is not None else None,
        "vibration": float(readings.get("vibration")) if readings.get("vibration") is not None else None,
        "pressure": float(readings.get("pressure")) if readings.get("pressure") is not None else None,
        "retrieved_sources": json.dumps(retrieved_sources) if isinstance(retrieved_sources, (list, dict)) else retrieved_sources,
        "diagnosis_text": record.get("diagnosis_text", ""),
        "likely_fault": likely_fault,
        "why": why,
        "recommended_checks": recommended_checks,
        "confidence_limitations": confidence_limitations,
        "sections": json.dumps(sections_dict),
        "runtime": record.get("runtime", "unknown"),
        "latency_seconds": float(record.get("latency_seconds")) if record.get("latency_seconds") is not None else None,
    }

    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, params)
        logger.info(f"Persisted diagnosis for {params['device_id']} ({params['fault_category']}) to database.")
        return True
    except Exception as e:
        logger.warning(f"Failed to persist diagnosis to PostgreSQL: {e}")
        return False


def get_recent_diagnoses(limit: int = 50, chronological: bool = True) -> List[Dict[str, Any]]:
    """Retrieve recent diagnoses from fault_incidents table.
    
    Timestamps are converted to strict ISO-8601 strings matching existing JSONL logs.
    If chronological=True, results are sorted from oldest to newest.
    """
    if not is_database_available():
        return []

    sql = """
        SELECT
            timestamp, device_id, fault_category, symptoms,
            temperature, vibration, pressure, retrieved_sources,
            diagnosis_text, likely_fault, why, recommended_checks,
            confidence_limitations, sections, runtime, latency_seconds
        FROM fault_incidents
        ORDER BY timestamp DESC
        LIMIT %(limit)s;
    """

    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, {"limit": limit})
                rows = cur.fetchall()

        results = []
        for r in rows:
            ts = r.get("timestamp")
            if isinstance(ts, datetime):
                iso_ts = ts.isoformat()
            else:
                iso_ts = str(ts) if ts else None

            symptoms = r.get("symptoms")
            if isinstance(symptoms, str):
                try:
                    symptoms = json.loads(symptoms)
                except Exception:
                    symptoms = [symptoms]

            retrieved = r.get("retrieved_sources")
            if isinstance(retrieved, str):
                try:
                    retrieved = json.loads(retrieved)
                except Exception:
                    retrieved = []

            sections = r.get("sections")
            if isinstance(sections, str):
                try:
                    sections = json.loads(sections)
                except Exception:
                    sections = {}

            item = {
                "timestamp": iso_ts,
                "device_id": r.get("device_id"),
                "fault_category": r.get("fault_category"),
                "symptoms": symptoms if isinstance(symptoms, list) else [],
                "readings": {
                    "temperature": r.get("temperature"),
                    "vibration": r.get("vibration"),
                    "pressure": r.get("pressure"),
                },
                "retrieved_sources": retrieved if isinstance(retrieved, list) else [],
                "diagnosis_text": r.get("diagnosis_text"),
                "likely_fault": r.get("likely_fault") or (sections.get("likely_fault") if isinstance(sections, dict) else ""),
                "why": r.get("why") or (sections.get("why") if isinstance(sections, dict) else ""),
                "recommended_checks": r.get("recommended_checks") or (sections.get("recommended_checks") if isinstance(sections, dict) else ""),
                "confidence_limitations": r.get("confidence_limitations") or (sections.get("confidence_limitations") if isinstance(sections, dict) else ""),
                "sections": sections if isinstance(sections, dict) else {},
                "runtime": r.get("runtime"),
                "latency_seconds": r.get("latency_seconds"),
            }
            results.append(item)

        if chronological:
            results.reverse()
        return results
    except Exception as e:
        logger.warning(f"Failed to query diagnoses from PostgreSQL: {e}")
        return []


def insert_telemetry_batch(readings: List[Dict[str, Any]]) -> int:
    """Insert a batch of sensor readings into telemetry_readings table.
    
    Returns the count of successfully inserted records.
    """
    if not readings or not is_database_available():
        return 0

    sql = """
        INSERT INTO telemetry_readings (
            timestamp, device_id, temperature, vibration, pressure, mode
        ) VALUES (
            %(timestamp)s, %(device_id)s, %(temperature)s, %(vibration)s, %(pressure)s, %(mode)s
        );
    """

    batch_params = []
    for r in readings:
        batch_params.append({
            "timestamp": r.get("timestamp"),
            "device_id": r.get("device_id", "pump_centrifugal_01"),
            "temperature": float(r.get("temperature", 0.0)),
            "vibration": float(r.get("vibration", 0.0)),
            "pressure": float(r.get("pressure", 0.0)),
            "mode": r.get("mode", "normal"),
        })

    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.executemany(sql, batch_params)
        return len(batch_params)
    except Exception as e:
        logger.warning(f"Failed to insert telemetry batch ({len(readings)} rows) into PostgreSQL: {e}")
        return 0


def prune_old_telemetry(retention_days: int = TELEMETRY_RETENTION_DAYS) -> int:
    """Delete telemetry older than retention_days.
    
    Returns the number of rows deleted.
    """
    if not is_database_available():
        return 0

    sql = "SELECT prune_old_telemetry(%(days)s) AS deleted_count;"
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, {"days": retention_days})
                row = cur.fetchone()
                count = row.get("deleted_count", 0) if row else 0
        if count > 0:
            logger.info(f"Pruned {count} telemetry records older than {retention_days} days.")
        return count
    except Exception as e:
        try:
            fallback_sql = """
                DELETE FROM telemetry_readings
                WHERE timestamp < (CURRENT_TIMESTAMP - (%(days)s || ' days')::INTERVAL);
            """
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(fallback_sql, {"days": retention_days})
                    count = cur.rowcount
            if count > 0:
                logger.info(f"Pruned {count} telemetry records (fallback query).")
            return count
        except Exception as e2:
            logger.warning(f"Failed to prune old telemetry: {e2}")
            return 0


def get_db_stats() -> Dict[str, Any]:
    """Return counts of telemetry_readings and fault_incidents from PostgreSQL."""
    if not is_database_available():
        return {
            "connected": False,
            "database": "p311_iot_diagnostics",
            "telemetry_count": 0,
            "incidents_count": 0,
            "retention_days": TELEMETRY_RETENTION_DAYS,
        }
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) AS c FROM telemetry_readings;")
                t_count = cur.fetchone()["c"]
                cur.execute("SELECT COUNT(*) AS c FROM fault_incidents;")
                f_count = cur.fetchone()["c"]
                return {
                    "connected": True,
                    "database": "p311_iot_diagnostics",
                    "telemetry_count": t_count,
                    "incidents_count": f_count,
                    "retention_days": TELEMETRY_RETENTION_DAYS,
                    "pruning_interval": "1 hour",
                }
    except Exception as e:
        logger.warning(f"Error fetching DB stats: {e}")
        return {
            "connected": False,
            "database": "p311_iot_diagnostics",
            "telemetry_count": 0,
            "incidents_count": 0,
            "retention_days": TELEMETRY_RETENTION_DAYS,
            "error": str(e),
        }

