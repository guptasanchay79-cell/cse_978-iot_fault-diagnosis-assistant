"""P_311: Knowledge-Driven IoT Fault Diagnosis Assistant.

Unit tests for Stage 4 fault detection and symptom extraction engine.
Tests threshold evaluation, rolling window smoothing, noise spike immunity,
and RAG query generation.
"""

from pathlib import Path
import sys
import unittest

# Ensure project root is in sys.path
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from config import (
    FAULT_MODE_BEARING_WEAR,
    FAULT_MODE_NORMAL,
    FAULT_MODE_OVERHEATING,
    FAULT_MODE_PRESSURE_DROP,
    FAULT_MODE_SENSOR_FAILURE,
)
from diagnosis.fault_detector import FaultDetector
from mqtt.sensor_simulator import PumpTelemetrySimulator


class TestFaultDetector(unittest.TestCase):
    """Test suite for FaultDetector rule-based logic."""

    def setUp(self):
        self.detector = FaultDetector(window_size=3)

    def test_normal_telemetry_triggers_zero_faults(self):
        """Verify that normal telemetry never generates false positive fault reports."""
        sim = PumpTelemetrySimulator(mode=FAULT_MODE_NORMAL)
        for _ in range(25):
            reading = sim.step()
            fault_report = self.detector.process_reading(reading)
            self.assertIsNone(fault_report, "Normal reading erroneously triggered a fault!")
        self.assertEqual(self.detector.faults_detected_count, 0)

    def test_overheating_detection(self):
        """Verify that overheating telemetry triggers the overheating category and structured report."""
        sim = PumpTelemetrySimulator(mode=FAULT_MODE_OVERHEATING)
        reports = []
        for _ in range(20):
            reading = sim.step()
            report = self.detector.process_reading(reading)
            if report is not None:
                reports.append(report)

        self.assertGreater(len(reports), 0, "Overheating condition was not detected!")
        last_report = reports[-1]
        self.assertEqual(last_report["fault_category"], "overheating")
        self.assertTrue(any("overheating" in s for s in last_report["symptoms"]))
        self.assertIn("centrifugal pump", last_report["query"].lower())
        self.assertGreater(last_report["rolling_stats"]["mean_temperature"], 75.0)

    def test_bearing_wear_detection(self):
        """Verify that bearing wear telemetry triggers the bearing_wear category."""
        sim = PumpTelemetrySimulator(mode=FAULT_MODE_BEARING_WEAR)
        reports = []
        for _ in range(20):
            reading = sim.step()
            report = self.detector.process_reading(reading)
            if report is not None:
                reports.append(report)

        self.assertGreater(len(reports), 0, "Bearing wear condition was not detected!")
        last_report = reports[-1]
        self.assertEqual(last_report["fault_category"], "bearing_wear")
        self.assertTrue(any("bearing vibration" in s for s in last_report["symptoms"]))
        self.assertGreater(last_report["rolling_stats"]["mean_vibration"], 4.5)

    def test_pressure_drop_detection(self):
        """Verify that pressure drop telemetry triggers the pressure_drop category."""
        sim = PumpTelemetrySimulator(mode=FAULT_MODE_PRESSURE_DROP)
        reports = []
        for _ in range(15):
            reading = sim.step()
            report = self.detector.process_reading(reading)
            if report is not None:
                reports.append(report)

        self.assertGreater(len(reports), 0, "Pressure drop condition was not detected!")
        last_report = reports[-1]
        self.assertEqual(last_report["fault_category"], "pressure_drop")
        self.assertTrue(any("discharge pressure drop" in s for s in last_report["symptoms"]))
        self.assertLess(last_report["rolling_stats"]["mean_pressure"], 3.0)

    def test_sensor_flatline_detection(self):
        """Verify that frozen sensor readings trigger sensor_failure category."""
        sim = PumpTelemetrySimulator(
            mode=FAULT_MODE_SENSOR_FAILURE, sensor_failure_type="flatline"
        )
        reports = []
        for _ in range(10):
            reading = sim.step()
            report = self.detector.process_reading(reading)
            if report is not None:
                reports.append(report)

        self.assertGreater(len(reports), 0, "Sensor flatline was not detected!")
        last_report = reports[-1]
        self.assertEqual(last_report["fault_category"], "sensor_failure")
        self.assertTrue(any("flat-line" in s for s in last_report["symptoms"]))

    def test_sensor_disconnect_immediate_detection(self):
        """Verify that out-of-range sensor disconnect (-999.0) triggers immediately."""
        reading = {
            "device_id": "pump_centrifugal_01",
            "timestamp": "2026-10-01T00:00:00Z",
            "temperature": -999.0,
            "vibration": 1.4,
            "pressure": 5.0,
        }
        report = self.detector.process_reading(reading)
        self.assertIsNotNone(report)
        self.assertEqual(report["fault_category"], "sensor_failure")
        self.assertTrue(any("outside physical valid range" in s for s in report["symptoms"]))

    def test_noise_spike_immunity(self):
        """Verify that a single transient spike does not trigger a false alarm due to rolling average."""
        # 1. Provide two normal readings
        r1 = {"device_id": "pump_01", "timestamp": "t1", "temperature": 52.0, "vibration": 1.4, "pressure": 5.0}
        r2 = {"device_id": "pump_01", "timestamp": "t2", "temperature": 53.0, "vibration": 1.5, "pressure": 4.9}
        self.assertIsNone(self.detector.process_reading(r1))
        self.assertIsNone(self.detector.process_reading(r2))

        # 2. Inject a single high-temperature spike (78.0 C)
        # Window contents: [52.0, 53.0, 78.0] -> Mean = 61.0 C (below 75.0 C threshold!)
        r3 = {"device_id": "pump_01", "timestamp": "t3", "temperature": 78.0, "vibration": 1.4, "pressure": 5.0}
        report = self.detector.process_reading(r3)
        self.assertIsNone(report, "Single transient spike falsely triggered an alarm!")


if __name__ == "__main__":
    unittest.main()
