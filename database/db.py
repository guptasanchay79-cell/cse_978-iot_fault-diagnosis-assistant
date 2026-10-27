"""IoT Fault Diagnosis Assistant - Database Connection & Repository Module.

Handles PostgreSQL connection pooling, circuit breaking, transaction lifecycle,
parameterized queries, and persistence for sensor readings and fault diagnoses.
"""

from contextlib import contextmanager
from datetime import datetime, timezone
import json
import logging
from pathlib import Path
import sys
import time
from typing import Any, Dict, Generator, List, Optional

# Ensure project root is in sys.path
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from config import (
    DB_CONNECT_TIMEOUT_SECONDS,
    DEFAULT_DEVICE_ID,
    POSTGRES_DB,
    POSTGRES_HOST,
    POSTGRES_PASSWORD,
    POSTGRES_PORT,
    POSTGRES_USER,
    TELEMETRY_RETENTION_DAYS,
)

logger = logging.getLogger("DatabaseManager")

# Select PostgreSQL driver: psycopg (v3) or psycopg2
_DRIVER_TYPE = None
try:
    import psycopg
    from psycopg.rows import dict_row
    _DRIVER_TYPE = "psycopg"
except ImportError:
    try:
        import psycopg2
        import psycopg2.extras
        _DRIVER_TYPE = "psycopg2"
    except ImportError:
        _DRIVER_TYPE = None
        logger.warning("No PostgreSQL driver found (neither psycopg nor psycopg2). Database functionality disabled.")

# Circuit breaker state
_DB_AVAILABLE: Optional[bool] = None
_LAST_CHECK_TIME: float = 0.0
_CHECK_COOLDOWN_SECONDS: float = 5.0


def get_connection_params() -> dict:
    """Return dictionary of connection parameters loaded from environment."""
    return {
        "host": POSTGRES_HOST,
        "port": POSTGRES_PORT,
        "dbname": POSTGRES_DB,
        "user": POSTGRES_USER,
        "password": POSTGRES_PASSWORD,
        "connect_timeout": DB_CONNECT_TIMEOUT_SECONDS,
    }


def is_database_available(force_check: bool = False) -> bool:
    """Check if PostgreSQL database is reachable.
    
    Caches the result for 5 seconds to avoid request blocking when offline.
    """
    global _DB_AVAILABLE, _LAST_CHECK_TIME
    if _DRIVER_TYPE is None:
        return False

    now = time.time()
    if not force_check and _DB_AVAILABLE is not None and (now - _LAST_CHECK_TIME) < _CHECK_COOLDOWN_SECONDS:
        return _DB_AVAILABLE

    params = get_connection_params()
    try:
        if _DRIVER_TYPE == "psycopg":
            with psycopg.connect(**params) as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1;")
                    cur.fetchone()
        else:
            conn = psycopg2.connect(**params)
            with conn.cursor() as cur:
                cur.execute("SELECT 1;")
                cur.fetchone()
            conn.close()

        _DB_AVAILABLE = True
        _LAST_CHECK_TIME = now
        return True
    except Exception as e:
        if _DB_AVAILABLE is not False:
            logger.warning(
                f"PostgreSQL database '{POSTGRES_DB}' is unreachable at {POSTGRES_HOST}:{POSTGRES_PORT} ({e}). "
                "Falling back to in-memory / JSONL mode."
            )
        _DB_AVAILABLE = False
        _LAST_CHECK_TIME = now
        return False


@contextmanager
def get_db_connection(timeout: int = DB_CONNECT_TIMEOUT_SECONDS) -> Generator[Any, None, None]:
    """Transactional context manager for PostgreSQL database connections.
    
    - Automatically commits on successful completion.
    - Automatically rolls back transaction on any exception.
    - Always closes connection upon exit.
    """
    if _DRIVER_TYPE is None:
        raise RuntimeError("No PostgreSQL driver available. Install psycopg or psycopg2-binary.")

    params = get_connection_params()
    params["connect_timeout"] = timeout
    conn = None

    try:
        if _DRIVER_TYPE == "psycopg":
            conn = psycopg.connect(**params, row_factory=dict_row)
            yield conn
            conn.commit()
        else:
            conn = psycopg2.connect(**params, cursor_factory=psycopg2.extras.RealDictCursor)
            yield conn
            conn.commit()
    except Exception:
        if conn is not None and not (getattr(conn, "closed", False)):
            try:
                conn.rollback()
            except Exception:
                pass
        raise
    finally:
        if conn is not None and not (getattr(conn, "closed", False)):
            try:
                conn.close()
            except Exception:
                pass


# ==============================================================================
# Sensor Readings Operations
# ==============================================================================

def insert_sensor_reading(reading: Dict[str, Any], fault_status: str = "normal") -> bool:
    """Insert a single sensor reading into sensor_readings table.
    
    Uses parameterized query and ON CONFLICT DO NOTHING to prevent duplicate inserts.
    """
    if not is_database_available():
        return False

    sql = """
        INSERT INTO sensor_readings (
            device_id, temperature, vibration, pressure, timestamp, fault_status, mode
        ) VALUES (
            %(device_id)s, %(temperature)s, %(vibration)s, %(pressure)s, %(timestamp)s, %(fault_status)s, %(mode)s
        )
        ON CONFLICT (device_id, timestamp) DO NOTHING;
    """

    params = {
        "device_id": reading.get("device_id", DEFAULT_DEVICE_ID),
        "temperature": float(reading.get("temperature", 0.0)),
        "vibration": float(reading.get("vibration", 0.0)),
        "pressure": float(reading.get("pressure", 0.0)),
        "timestamp": reading.get("timestamp") or datetime.now(timezone.utc).isoformat(),
        "fault_status": reading.get("fault_status") or fault_status or "normal",
        "mode": reading.get("mode", "normal"),
    }

    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, params)
        return True
    except Exception as e:
        logger.warning(f"Failed to insert sensor reading into PostgreSQL: {e}")
        return False


def insert_sensor_readings_batch(readings: List[Dict[str, Any]]) -> int:
    """Insert a batch of sensor readings into sensor_readings table.
    
    Returns the count of inserted records.
    """
    if not readings or not is_database_available():
        return 0

    sql = """
        INSERT INTO sensor_readings (
            device_id, temperature, vibration, pressure, timestamp, fault_status, mode
        ) VALUES (
            %(device_id)s, %(temperature)s, %(vibration)s, %(pressure)s, %(timestamp)s, %(fault_status)s, %(mode)s
        )
        ON CONFLICT (device_id, timestamp) DO NOTHING;
    """

    batch_params = []
    for r in readings:
        batch_params.append({
            "device_id": r.get("device_id", DEFAULT_DEVICE_ID),
            "temperature": float(r.get("temperature", 0.0)),
            "vibration": float(r.get("vibration", 0.0)),
            "pressure": float(r.get("pressure", 0.0)),
            "timestamp": r.get("timestamp") or datetime.now(timezone.utc).isoformat(),
            "fault_status": r.get("fault_status", "normal"),
            "mode": r.get("mode", "normal"),
        })

    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.executemany(sql, batch_params)
        return len(batch_params)
    except Exception as e:
        logger.warning(f"Failed to insert sensor readings batch ({len(readings)} rows): {e}")
        return 0


# Alias for backward compatibility
def insert_telemetry_batch(readings: List[Dict[str, Any]]) -> int:
    """Backward compatibility alias for insert_sensor_readings_batch."""
    return insert_sensor_readings_batch(readings)


def get_recent_sensor_readings(limit: int = 60, chronological: bool = True) -> List[Dict[str, Any]]:
    """Retrieve recent sensor readings from sensor_readings table.
    
    If chronological=True, results are returned sorted from oldest to newest.
    """
    if not is_database_available():
        return []

    sql = """
        SELECT
            id, device_id, temperature, vibration, pressure, timestamp, fault_status, mode, created_at
        FROM sensor_readings
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
            iso_ts = ts.isoformat() if isinstance(ts, datetime) else str(ts) if ts else None
            ca = r.get("created_at")
            iso_ca = ca.isoformat() if isinstance(ca, datetime) else str(ca) if ca else None

            results.append({
                "id": r.get("id"),
                "device_id": r.get("device_id"),
                "temperature": float(r.get("temperature")),
                "vibration": float(r.get("vibration")),
                "pressure": float(r.get("pressure")),
                "timestamp": iso_ts,
                "fault_status": r.get("fault_status", "normal"),
                "mode": r.get("mode", "normal"),
                "created_at": iso_ca,
            })

        if chronological:
            results.reverse()
        return results
    except Exception as e:
        logger.warning(f"Failed to query sensor readings from PostgreSQL: {e}")
        return []


# ==============================================================================
# Fault Incidents / Diagnosis Operations
# ==============================================================================

def insert_diagnosis(record: Dict[str, Any]) -> bool:
    """Insert a diagnostic synthesis record into fault_incidents table."""
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
        "timestamp": record.get("timestamp") or datetime.now(timezone.utc).isoformat(),
        "device_id": record.get("device_id", DEFAULT_DEVICE_ID),
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
        logger.info(f"Persisted diagnosis for {params['device_id']} ({params['fault_category']}) to PostgreSQL.")
        return True
    except Exception as e:
        logger.warning(f"Failed to persist diagnosis to PostgreSQL: {e}")
        return False


def get_recent_diagnoses(limit: int = 50, chronological: bool = True) -> List[Dict[str, Any]]:
    """Retrieve recent diagnoses from fault_incidents table."""
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
            iso_ts = ts.isoformat() if isinstance(ts, datetime) else str(ts) if ts else None

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
                    "temperature": float(r["temperature"]) if r.get("temperature") is not None else None,
                    "vibration": float(r["vibration"]) if r.get("vibration") is not None else None,
                    "pressure": float(r["pressure"]) if r.get("pressure") is not None else None,
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


# ==============================================================================
# Maintenance & Statistics
# ==============================================================================

def prune_old_sensor_readings(retention_days: int = TELEMETRY_RETENTION_DAYS) -> int:
    """Delete sensor readings older than retention_days."""
    if not is_database_available():
        return 0

    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT prune_old_sensor_readings(%(days)s) AS deleted_count;", {"days": retention_days})
                row = cur.fetchone()
                count = row.get("deleted_count", 0) if row else 0
        if count > 0:
            logger.info(f"Pruned {count} sensor readings older than {retention_days} days.")
        return count
    except Exception:
        try:
            fallback_sql = """
                DELETE FROM sensor_readings
                WHERE timestamp < (CURRENT_TIMESTAMP - (%(days)s || ' days')::INTERVAL);
            """
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(fallback_sql, {"days": retention_days})
                    count = cur.rowcount
            if count > 0:
                logger.info(f"Pruned {count} sensor readings (fallback query).")
            return count
        except Exception as e2:
            logger.warning(f"Failed to prune old sensor readings: {e2}")
            return 0


def prune_old_telemetry(retention_days: int = TELEMETRY_RETENTION_DAYS) -> int:
    """Backward compatibility alias for prune_old_sensor_readings."""
    return prune_old_sensor_readings(retention_days)


def get_database_stats() -> Dict[str, Any]:
    """Return live counts of sensor_readings and fault_incidents from PostgreSQL."""
    if not is_database_available():
        return {
            "connected": False,
            "database": POSTGRES_DB,
            "telemetry_count": 0,
            "sensor_readings_count": 0,
            "incidents_count": 0,
            "retention_days": TELEMETRY_RETENTION_DAYS,
        }
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) AS c FROM sensor_readings;")
                s_count = cur.fetchone()["c"]
                cur.execute("SELECT COUNT(*) AS c FROM fault_incidents;")
                f_count = cur.fetchone()["c"]
                return {
                    "connected": True,
                    "database": POSTGRES_DB,
                    "telemetry_count": s_count,
                    "sensor_readings_count": s_count,
                    "incidents_count": f_count,
                    "retention_days": TELEMETRY_RETENTION_DAYS,
                    "pruning_interval": "1 hour",
                }
    except Exception as e:
        logger.warning(f"Error fetching DB stats: {e}")
        return {
            "connected": False,
            "database": POSTGRES_DB,
            "telemetry_count": 0,
            "sensor_readings_count": 0,
            "incidents_count": 0,
            "retention_days": TELEMETRY_RETENTION_DAYS,
            "error": str(e),
        }


def get_db_stats() -> Dict[str, Any]:
    """Alias for get_database_stats."""
    return get_database_stats()


def init_database_schema(schema_file: Optional[Path] = None) -> bool:
    """Apply db/init.sql to the configured PostgreSQL database."""
    if schema_file is None:
        schema_file = _PROJECT_ROOT / "db" / "init.sql"
    if not schema_file.exists():
        logger.error(f"Schema file not found at: {schema_file}")
        return False

    sql_text = schema_file.read_text(encoding="utf-8")
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql_text)
        logger.info(f"Schema applied successfully to '{POSTGRES_DB}'.")
        return True
    except Exception as e:
        logger.error(f"Failed to apply schema: {e}")
        return False
