"""P_311: Knowledge-Driven IoT Fault Diagnosis Assistant.

Unit tests for Stage 7 local LLM prompts, client integration,
section formatting, and offline resilience.
"""

from pathlib import Path
import sys
import unittest

# Ensure project root is in sys.path
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from llm.client import LocalLLMClient
from llm.prompts import build_diagnosis_prompt
from rag.retriever import TFIDFRetriever


class TestLocalLLM(unittest.TestCase):
    """Test suite for Local LLM prompting, section validation, and client fallback."""

    def setUp(self):
        self.client = LocalLLMClient()
        self.retriever = TFIDFRetriever()

    def test_prompt_builder_includes_telemetry_and_chunks(self):
        """Verify prompt template contains telemetry readings and retrieved chunks."""
        telemetry = {
            "device_id": "pump_centrifugal_01",
            "timestamp": "2026-10-01T00:00:00Z",
            "symptoms": ["severe motor stator overheating at 82.5 C"],
            "readings": {"temperature": 82.5, "vibration": 1.4, "pressure": 5.0},
        }
        chunks = [
            {
                "source_file": "KB03_motor_winding_overheating.md",
                "score": 0.28,
                "content": "Stator winding thermal breakdown and fan shroud blockage.",
            }
        ]
        prompt = build_diagnosis_prompt(telemetry, chunks)
        self.assertIn("pump_centrifugal_01", prompt)
        self.assertIn("severe motor stator overheating", prompt)
        self.assertIn("82.5", prompt)
        self.assertIn("KB03_motor_winding_overheating.md", prompt)
        self.assertIn("Likely Fault", prompt)
        self.assertIn("Recommended Checks", prompt)

    def test_generate_returns_all_four_mandatory_sections(self):
        """Verify generated diagnosis contains all 4 mandatory report sections."""
        telemetry = {
            "device_id": "pump_centrifugal_01",
            "timestamp": "2026-10-01T00:00:00Z",
            "fault_category": "bearing_wear",
            "symptoms": ["critical bearing vibration of 6.2 mm/s"],
            "readings": {"temperature": 67.5, "vibration": 6.2, "pressure": 5.0},
            "rolling_stats": {"mean_temperature": 67.0, "mean_vibration": 6.1, "mean_pressure": 5.0, "window_size": 3},
        }
        chunks = self.retriever.retrieve("bearing vibration 6.2 mm/s", top_k=2)
        result = self.client.generate(telemetry, chunks)

        self.assertEqual(result["status"], "success")
        sections = result["sections"]
        self.assertTrue(sections["likely_fault"], "Section 1 'Likely Fault' missing or empty!")
        self.assertTrue(sections["why"], "Section 2 'Why' missing or empty!")
        self.assertTrue(sections["recommended_checks"], "Section 3 'Recommended Checks' missing or empty!")
        self.assertTrue(sections["confidence_limitations"], "Section 4 'Confidence/Limitations' missing or empty!")
        self.assertTrue("KB01" in sections["why"] or "KB02" in sections["why"])

    def test_generate_handles_insufficient_context(self):
        """Verify client explicitly states insufficient context when no chunks are provided."""
        telemetry = {
            "device_id": "pump_centrifugal_01",
            "timestamp": "2026-10-01T00:00:00Z",
            "fault_category": "unknown",
            "symptoms": ["unfamiliar sensor anomaly"],
            "readings": {"temperature": 50.0, "vibration": 1.0, "pressure": 5.0},
        }
        result = self.client.generate(telemetry, retrieved_chunks=[])
        sections = result["sections"]
        self.assertIn("Low", sections["confidence_limitations"])
        self.assertIn("Insufficient", sections["confidence_limitations"])

    def test_availability_check_non_blocking(self):
        """Verify availability check runs quickly and reports status string without error."""
        available, msg = self.client.is_available()
        self.assertIsInstance(available, bool)
        self.assertIsInstance(msg, str)


if __name__ == "__main__":
    unittest.main()
