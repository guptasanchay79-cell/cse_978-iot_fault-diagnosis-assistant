"""P_311: Knowledge-Driven IoT Fault Diagnosis Assistant.

Unit and benchmark tests for Stage 6 RAG knowledge retriever.
Verifies chunking, index caching, and ensures that for every simulated
fault mode query, the correct diagnostic manual ranks in the top 3 results.
"""

from pathlib import Path
import sys
import unittest

# Ensure project root is in sys.path
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from rag.chunker import load_and_chunk_knowledge_base
from rag.retriever import TFIDFRetriever


class TestRAGRetriever(unittest.TestCase):
    """Test suite for semantic RAG chunking and TF-IDF retrieval."""

    @classmethod
    def setUpClass(cls):
        cls.retriever = TFIDFRetriever()

    def test_chunking_loads_all_documents(self):
        """Verify that all 14 markdown manuals are chunked into semantic sections."""
        chunks = load_and_chunk_knowledge_base()
        self.assertGreaterEqual(len(chunks), 70)
        doc_ids = {c.doc_id for c in chunks}
        self.assertEqual(len(doc_ids), 14)

    def test_retrieval_bearing_wear_ranks_top3(self):
        """Verify bearing wear symptom query returns KB01 or KB02 in top 3."""
        query = (
            "Industrial centrifugal pump pump_centrifugal_01 exhibits critical bearing vibration "
            "velocity RMS of 6.24 mm/s exceeding ISO 10816 Zone D danger limit of 4.5 mm/s, and "
            "secondary frictional temperature rise of 67.80 C. Current telemetry shows vibration 6.24 mm/s."
        )
        results = self.retriever.retrieve(query, top_k=3)
        self.assertGreaterEqual(len(results), 1)
        top_files = [r["source_file"] for r in results]
        self.assertTrue(
            "KB01_bearing_inner_raceway_fatigue.md" in top_files
            or "KB02_bearing_lubrication_starvation.md" in top_files,
            f"Expected bearing wear manual in top 3, got: {top_files}",
        )

    def test_retrieval_overheating_ranks_top3(self):
        """Verify overheating symptom query returns KB03 or KB04 in top 3."""
        query = (
            "Industrial centrifugal pump pump_centrifugal_01 exhibits severe motor stator / bearing "
            "overheating at 82.50 C exceeding thermal safety threshold of 75.0 C, and rapid thermal climb rate. "
            "Current telemetry shows temperature 82.50 C."
        )
        results = self.retriever.retrieve(query, top_k=3)
        self.assertGreaterEqual(len(results), 1)
        top_files = [r["source_file"] for r in results]
        self.assertTrue(
            "KB03_motor_winding_overheating.md" in top_files
            or "KB04_bearing_housing_thermal_runaway.md" in top_files,
            f"Expected overheating manual in top 3, got: {top_files}",
        )

    def test_retrieval_pressure_drop_ranks_top3(self):
        """Verify pressure drop symptom query returns KB05 or KB06 in top 3."""
        query = (
            "Industrial centrifugal pump pump_centrifugal_01 exhibits critical hydraulic discharge "
            "pressure drop to 2.10 bar falling below low operational limit of 3.0 bar, and hydraulic "
            "cavitation turbulence with vibration fluctuations. Discharge pressure is 2.10 bar."
        )
        results = self.retriever.retrieve(query, top_k=3)
        self.assertGreaterEqual(len(results), 1)
        top_files = [r["source_file"] for r in results]
        self.assertTrue(
            "KB05_discharge_pipe_rupture_leakage.md" in top_files
            or "KB06_impeller_cavitation_hydraulic_loss.md" in top_files,
            f"Expected pressure drop / cavitation manual in top 3, got: {top_files}",
        )

    def test_retrieval_sensor_flatline_ranks_top3(self):
        """Verify sensor flatline query returns KB08 in top 3."""
        query = (
            "Industrial centrifugal pump pump_centrifugal_01 exhibits temperature sensor flat-line detected: "
            "value frozen at 54.00 C with 0.00 variance across consecutive readings."
        )
        results = self.retriever.retrieve(query, top_k=3)
        self.assertGreaterEqual(len(results), 1)
        top_files = [r["source_file"] for r in results]
        self.assertIn("KB08_adc_telemetry_sensor_flatline.md", top_files)

    def test_retrieval_sensor_disconnect_ranks_top3(self):
        """Verify sensor disconnect query returns KB07 in top 3."""
        query = (
            "Industrial centrifugal pump pump_centrifugal_01 telemetry sensor failure: temperature sensor "
            "reading (-999.0 C) is outside physical valid range (sensor disconnect / open-circuit)."
        )
        results = self.retriever.retrieve(query, top_k=3)
        self.assertGreaterEqual(len(results), 1)
        top_files = [r["source_file"] for r in results]
        self.assertIn("KB07_rtd_temperature_sensor_disconnect.md", top_files)


if __name__ == "__main__":
    unittest.main()
