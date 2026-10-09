"""P_311: Knowledge-Driven IoT Fault Diagnosis Assistant.

Database persistence package for fault incidents and sensor telemetry.
"""

from db.repository import (
    get_db_stats,
    get_recent_diagnoses,
    insert_diagnosis,
    insert_telemetry_batch,
    is_database_available,
    prune_old_telemetry,
)

__all__ = [
    "is_database_available",
    "insert_diagnosis",
    "get_recent_diagnoses",
    "insert_telemetry_batch",
    "prune_old_telemetry",
    "get_db_stats",
]

