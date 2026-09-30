"""P_311: Knowledge-Driven IoT Fault Diagnosis Assistant.

Unit tests for Stage 3 realistic telemetry simulator and fault modes.
Verifies that each mode generates distinct, physically grounded telemetry signatures
and enforces ground-truth label isolation.
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
    PRESSURE_LOW_THRESHOLD,
    PRESSURE_NORMAL_MAX,
    PRESSURE_NORMAL_MIN,
    TEMP_NORMAL_MAX,
    TEMP_NORMAL_MIN,
    TEMP_WARNING_THRESHOLD,
    VIB_NORMAL_MAX,
    VIB_NORMAL_MIN,
    VIB_WARNING_THRESHOLD,
)
from mqtt.sensor_simulator import PumpTelemetrySimulator


class TestFaultSimulatorModes(unittest.TestCase):
    """Test telemetry signatures across all operational modes."""

    def test_normal_mode_within_healthy_envelope(self):
        """Verify normal mode remains within healthy operating bounds."""
        sim = PumpTelemetrySimulator(mode=FAULT_MODE_NORMAL, test_mode=False)
        for _ in range(20):
            reading = sim.step()
            self.assertGreaterEqual(reading["temperature"], TEMP_NORMAL_MIN - 2.0)
            self.assertLessEqual(reading["temperature"], TEMP_NORMAL_MAX + 2.0)
            self.assertGreaterEqual(reading["vibration"], VIB_NORMAL_MIN - 0.5)
            self.assertLessEqual(reading["vibration"], VIB_NORMAL_MAX + 0.5)
            self.assertGreaterEqual(reading["pressure"], PRESSURE_NORMAL_MIN - 0.5)
            self.assertLessEqual(reading["pressure"], PRESSURE_NORMAL_MAX + 0.5)
            self.assertNotIn("ground_truth_fault", reading)

    def test_overheating_mode_signature(self):
        """Verify overheating mode causes temperature to exceed warning threshold while others stay normal."""
        sim = PumpTelemetrySimulator(mode=FAULT_MODE_OVERHEATING, test_mode=False)
        # Advance 20 steps to allow progressive climb
        for _ in range(20):
            reading = sim.step()

        self.assertGreater(reading["temperature"], TEMP_WARNING_THRESHOLD)
        self.assertLessEqual(reading["vibration"], VIB_NORMAL_MAX + 1.0)
        self.assertGreaterEqual(reading["pressure"], PRESSURE_NORMAL_MIN - 0.5)
        self.assertNotIn("ground_truth_fault", reading)

    def test_bearing_wear_mode_signature(self):
        """Verify bearing wear causes vibration to exceed ISO threshold with secondary temp rise."""
        sim = PumpTelemetrySimulator(mode=FAULT_MODE_BEARING_WEAR, test_mode=False)
        for _ in range(20):
            reading = sim.step()

        self.assertGreater(reading["vibration"], VIB_WARNING_THRESHOLD)
        # Pressure remains normal
        self.assertGreaterEqual(reading["pressure"], PRESSURE_NORMAL_MIN - 0.5)
        self.assertNotIn("ground_truth_fault", reading)

    def test_pressure_drop_mode_signature(self):
        """Verify pressure drop causes pressure to fall below low threshold."""
        sim = PumpTelemetrySimulator(mode=FAULT_MODE_PRESSURE_DROP, test_mode=False)
        for _ in range(15):
            reading = sim.step()

        self.assertLess(reading["pressure"], PRESSURE_LOW_THRESHOLD)
        self.assertLess(reading["temperature"], TEMP_WARNING_THRESHOLD)
        self.assertNotIn("ground_truth_fault", reading)

    def test_sensor_failure_flatline(self):
        """Verify flatline sensor mode produces identical readings across steps."""
        sim = PumpTelemetrySimulator(
            mode=FAULT_MODE_SENSOR_FAILURE, sensor_failure_type="flatline", test_mode=False
        )
        readings = [sim.step()["temperature"] for _ in range(10)]
        # All temperature readings must be mathematically identical (zero variance)
        self.assertEqual(len(set(readings)), 1)
        self.assertNotIn("ground_truth_fault", sim.step())

    def test_sensor_failure_disconnect(self):
        """Verify disconnect sensor mode produces -999.0 out-of-range flag."""
        sim = PumpTelemetrySimulator(
            mode=FAULT_MODE_SENSOR_FAILURE, sensor_failure_type="disconnect", test_mode=False
        )
        reading = sim.step()
        self.assertEqual(reading["temperature"], -999.0)

    def test_ground_truth_isolation(self):
        """Verify ground_truth_fault is strictly absent in standard mode and present in test_mode."""
        sim_standard = PumpTelemetrySimulator(mode=FAULT_MODE_OVERHEATING, test_mode=False)
        reading_standard = sim_standard.step()
        self.assertNotIn("ground_truth_fault", reading_standard)

        sim_test = PumpTelemetrySimulator(mode=FAULT_MODE_OVERHEATING, test_mode=True)
        reading_test = sim_test.step()
        self.assertIn("ground_truth_fault", reading_test)
        self.assertEqual(reading_test["ground_truth_fault"], FAULT_MODE_OVERHEATING)


if __name__ == "__main__":
    unittest.main()
