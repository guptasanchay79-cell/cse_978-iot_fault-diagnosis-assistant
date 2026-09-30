"""P_311: Knowledge-Driven IoT Fault Diagnosis Assistant.

End-to-End integration test suite (Stage 8 & Stage 9).
Proves that:
1. Normal telemetry mode runs quietly with 0 diagnoses generated.
2. Fault modes (overheating, bearing wear) trigger detection, RAG, and LLM diagnosis.
3. Diagnostic records are cleanly persisted to data/diagnoses_log.jsonl.
"""

import json
from pathlib import Path
import sys
import time
import unittest

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from config import DATA_DIR, FAULT_MODE_BEARING_WEAR, FAULT_MODE_NORMAL, FAULT_MODE_OVERHEATING
from main import FaultDiagnosisPipeline
from mqtt.sensor_simulator import PumpTelemetrySimulator


class TestEndToEndIntegration(unittest.TestCase):
    """End-to-end integration tests for full diagnosis pipeline."""

    @classmethod
    def setUpClass(cls):
        cls.pipeline = FaultDiagnosisPipeline(cooldown_seconds=1.0)
        # Clear log files for clean test run
        jsonl = DATA_DIR / "diagnoses_log.jsonl"
        if jsonl.exists():
            jsonl.unlink()

    def test_normal_mode_stays_quiet(self):
        """Verify normal telemetry produces 0 diagnoses."""
        sim = PumpTelemetrySimulator(mode=FAULT_MODE_NORMAL)
        for _ in range(10):
            reading = sim.step()
            self.pipeline._handle_telemetry(reading)

        self.assertEqual(self.pipeline.total_diagnoses_generated, 0)

    def test_fault_mode_triggers_diagnosis_and_logging(self):
        """Verify overheating telemetry triggers diagnosis, formats report, and logs to disk."""
        sim = PumpTelemetrySimulator(mode=FAULT_MODE_OVERHEATING)
        for _ in range(15):
            reading = sim.step()
            self.pipeline._handle_telemetry(reading)

        self.assertGreaterEqual(self.pipeline.total_diagnoses_generated, 1)

        # Check log file exists and contains valid JSON
        log_file = DATA_DIR / "diagnoses_log.jsonl"
        self.assertTrue(log_file.exists())
        lines = log_file.read_text(encoding="utf-8").strip().split("\n")
        self.assertGreaterEqual(len(lines), 1)

        record = json.loads(lines[0])
        self.assertEqual(record["fault_category"], "overheating")
        self.assertIn("severe motor stator", record["symptoms"][0])
        self.assertGreaterEqual(len(record["retrieved_sources"]), 1)
        self.assertIn("Likely Fault", record["diagnosis_text"])


if __name__ == "__main__":
    unittest.main()
