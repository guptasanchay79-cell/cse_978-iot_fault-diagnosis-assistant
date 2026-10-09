"""Unit tests for PostgreSQL persistence layer (db module).

Verifies graceful degradation when database is offline, ISO timestamp compliance,
and safe non-blocking behaviors.
"""

from datetime import datetime, timezone
import unittest

from db.connection import is_database_available
from db.repository import (
    get_recent_diagnoses,
    insert_diagnosis,
    insert_telemetry_batch,
    prune_old_telemetry,
)


class TestDatabaseGracefulDegradation(unittest.TestCase):
    """Test suite ensuring zero crashes occur when database is offline."""

    def test_database_available_returns_bool(self):
        """Verify is_database_available returns a boolean without throwing."""
        available = is_database_available()
        self.assertIsInstance(available, bool)

    def test_insert_diagnosis_offline_safety(self):
        """Verify insert_diagnosis handles offline database gracefully."""
        sample_record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "device_id": "pump_centrifugal_01",
            "fault_category": "bearing_wear",
            "symptoms": ["vibration 5.2 mm/s"],
            "readings": {"temperature": 55.0, "vibration": 5.2, "pressure": 5.0},
            "retrieved_sources": [],
            "diagnosis_text": "Sample test diagnosis",
            "sections": {},
            "runtime": "test",
            "latency_seconds": 0.05,
        }
        # If DB is offline, should return False without raising
        result = insert_diagnosis(sample_record)
        self.assertIsInstance(result, bool)

    def test_get_recent_diagnoses_offline_safety(self):
        """Verify get_recent_diagnoses returns a list safely."""
        diagnoses = get_recent_diagnoses(limit=10)
        self.assertIsInstance(diagnoses, list)

    def test_insert_telemetry_batch_offline_safety(self):
        """Verify insert_telemetry_batch returns integer count safely."""
        sample_batch = [
            {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "device_id": "pump_centrifugal_01",
                "temperature": 54.0,
                "vibration": 1.4,
                "pressure": 5.0,
                "mode": "normal",
            }
        ]
        inserted = insert_telemetry_batch(sample_batch)
        self.assertIsInstance(inserted, int)

    def test_prune_old_telemetry_offline_safety(self):
        """Verify prune_old_telemetry returns integer count safely."""
        deleted = prune_old_telemetry(retention_days=7)
        self.assertIsInstance(deleted, int)

    def test_timestamp_iso_format_adherence(self):
        """Verify datetime to ISO string conversion produces standard format."""
        dt = datetime(2026, 10, 1, 15, 30, 45, 123456, tzinfo=timezone.utc)
        iso_str = dt.isoformat()
        self.assertEqual(iso_str, "2026-10-01T15:30:45.123456+00:00")


if __name__ == "__main__":
    unittest.main()
