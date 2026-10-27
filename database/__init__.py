"""Database access module for IoT Fault Diagnosis Assistant.

Re-exports core database connection and repository functions from database.db.
"""

from database.db import (
    get_connection_params,
    get_database_stats,
    get_db_connection,
    get_db_stats,
    get_recent_diagnoses,
    get_recent_sensor_readings,
    init_database_schema,
    insert_diagnosis,
    insert_sensor_reading,
    insert_sensor_readings_batch,
    insert_telemetry_batch,
    is_database_available,
    prune_old_sensor_readings,
    prune_old_telemetry,
)

__all__ = [
    "get_connection_params",
    "get_db_connection",
    "is_database_available",
    "insert_sensor_reading",
    "insert_sensor_readings_batch",
    "insert_telemetry_batch",
    "get_recent_sensor_readings",
    "insert_diagnosis",
    "get_recent_diagnoses",
    "prune_old_sensor_readings",
    "prune_old_telemetry",
    "get_database_stats",
    "get_db_stats",
    "init_database_schema",
]
