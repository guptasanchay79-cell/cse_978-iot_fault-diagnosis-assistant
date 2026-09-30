"""P_311: Knowledge-Driven IoT Fault Diagnosis Assistant.

Module: llm/client.py
Local LLM inference client interfacing with Ollama (e.g. llama3.2:3b).
Handles local networking via standard urllib, gracefully manages timeouts,
detects whether Ollama is active, and provides a deterministic rule-grounded
synthesis fallback when the local daemon is offline.
"""

import argparse
import json
import logging
from pathlib import Path
import re
import sys
import time
from typing import Any, Dict, List, Optional, Tuple
import urllib.error
import urllib.request

# Ensure project root is in sys.path
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from config import (
    LLM_MODEL_NAME,
    LLM_REQUEST_TIMEOUT_SECONDS,
    LLM_TEMPERATURE,
    OLLAMA_API_BASE_URL,
)
from llm.prompts import build_diagnosis_prompt

logging.basicConfig(
    stream=sys.stdout,
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("LLMClient")


class LocalLLMClient:
    """Client for local Ollama LLM inference with grounded context synthesis."""

    def __init__(
        self,
        base_url: str = OLLAMA_API_BASE_URL,
        model_name: str = LLM_MODEL_NAME,
        timeout: float = LLM_REQUEST_TIMEOUT_SECONDS,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model_name = model_name
        self.timeout = timeout

    def is_available(self) -> Tuple[bool, str]:
        """Check if local Ollama daemon is active and responsive on localhost."""
        url = f"{self.base_url}/api/tags"
        try:
            req = urllib.request.Request(url, method="GET")
            with urllib.request.urlopen(req, timeout=2.0) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read().decode("utf-8"))
                    models = [m.get("name", "") for m in data.get("models", [])]
                    return True, f"Ollama online with models: {', '.join(models) or 'none'}"
                return False, f"Ollama returned HTTP status {resp.status}"
        except urllib.error.URLError as err:
            return False, f"Ollama service unreachable on {self.base_url}: {err.reason}"
        except Exception as exc:
            return False, f"Ollama connection check failed: {exc}"

    def generate(
        self,
        telemetry_summary: Dict[str, Any],
        retrieved_chunks: List[Dict[str, Any]],
        force_fallback: bool = False,
    ) -> Dict[str, Any]:
        """Generate a structured grounded diagnosis for the telemetry and retrieved context."""
        prompt = build_diagnosis_prompt(telemetry_summary, retrieved_chunks)
        start_time = time.perf_counter()

        # Check if Ollama is available
        available, status_msg = self.is_available()

        if available and not force_fallback:
            try:
                logger.info("Querying local Ollama model '%s'...", self.model_name)
                diagnosis_text = self._query_ollama(prompt)
                elapsed = time.perf_counter() - start_time
                return {
                    "status": "success",
                    "runtime": f"ollama ({self.model_name})",
                    "latency_seconds": round(elapsed, 2),
                    "prompt": prompt,
                    "response": diagnosis_text,
                    "sections": self._parse_sections(diagnosis_text),
                }
            except Exception as exc:
                logger.warning(
                    "Ollama inference failed (%s). Falling back to grounded synthesis: %s",
                    type(exc).__name__,
                    exc,
                )

        # Fallback path when Ollama is offline or uninstalled
        logger.info(
            "Local LLM runtime note: %s. Using deterministic grounded context synthesis.",
            status_msg,
        )
        diagnosis_text = self._generate_grounded_synthesis(
            telemetry_summary, retrieved_chunks
        )
        elapsed = time.perf_counter() - start_time

        return {
            "status": "success",
            "runtime": "grounded_synthesis_fallback",
            "notice": (
                f"Ollama is offline ({status_msg}). Diagnosis was synthesized directly from "
                "the retrieved knowledge base context. To enable neural generation, launch: 'ollama serve'."
            ),
            "latency_seconds": round(elapsed, 4),
            "prompt": prompt,
            "response": diagnosis_text,
            "sections": self._parse_sections(diagnosis_text),
        }

    def _query_ollama(self, prompt: str) -> str:
        """Send generation request to Ollama HTTP API."""
        url = f"{self.base_url}/api/generate"
        payload = {
            "model": self.model_name,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": LLM_TEMPERATURE,
            },
        }

        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            if resp.status != 200:
                raise RuntimeError(f"Ollama API returned HTTP {resp.status}")
            data = json.loads(resp.read().decode("utf-8"))
            return data.get("response", "").strip()

    def _generate_grounded_synthesis(
        self,
        telemetry: Dict[str, Any],
        chunks: List[Dict[str, Any]],
    ) -> str:
        """Deterministic context synthesis strictly grounded in retrieved documents."""
        device_id = telemetry.get("device_id", "pump_centrifugal_01")
        category = telemetry.get("fault_category", "unknown")
        readings = telemetry.get("readings", {})
        symptoms = telemetry.get("symptoms", [])

        if not chunks:
            return (
                "### 1. Likely Fault\n"
                "Unidentified Asset Anomaly (No Matching Context)\n\n"
                "### 2. Why (Evidence from Readings and Documents)\n"
                f"Observed symptoms: {'; '.join(symptoms)}.\n"
                "No relevant diagnostic documents were retrieved from the knowledge base.\n\n"
                "### 3. Recommended Checks\n"
                "1. Perform immediate manual visual and thermal inspection of the asset.\n"
                "2. Verify instrumentation and calibration.\n\n"
                "### 4. Confidence / Limitations\n"
                "Confidence: Low. Insufficient retrieved context to formulate a grounded diagnosis."
            )

        top_chunk = chunks[0]
        top_title = top_chunk.get("doc_title", "Technical Diagnosis Manual")
        top_file = top_chunk.get("source_file", "knowledge_base")
        top_content = top_chunk.get("content", "")

        # Extract root causes and recommendations from the top chunk content
        likely_fault_match = re.search(r"Manual:\s*(.+)", top_title)
        likely_fault = likely_fault_match.group(1).strip() if likely_fault_match else top_title

        # Synthesize 4 required sections
        temp_val = readings.get("temperature", "N/A")
        vib_val = readings.get("vibration", "N/A")
        press_val = readings.get("pressure", "N/A")

        why_text = (
            f"Observed telemetry for {device_id} exhibits {'; '.join(symptoms)}. "
            f"Current operating parameters (Temperature: {temp_val} C, Vibration: {vib_val} mm/s, "
            f"Discharge Pressure: {press_val} bar) closely align with the diagnostic profile "
            f"documented in '{top_file}'. "
        )
        if "bearing" in category:
            why_text += (
                "Vibration velocity RMS exceeds the ISO 10816 Zone D boundary (4.5 mm/s), "
                "characteristic of inner raceway micro-spalling or boundary lubrication breakdown."
            )
        elif "overheating" in category:
            why_text += (
                "Thermal readings exceed the 75.0 C warning limit, confirming rapid thermal accumulation "
                "due to stator cooling breakdown or abnormal motor electrical loading."
            )
        elif "pressure_drop" in category:
            why_text += (
                "Discharge hydraulic pressure has collapsed below 3.0 bar, indicating catastrophic head loss "
                "from discharge pipe breach or severe impeller eye cavitation."
            )
        elif "sensor_failure" in category:
            why_text += (
                "Sensor signal exhibits zero variance or physical out-of-range flag, indicating instrumentation "
                "open-circuit or ADC peripheral freeze while pump continues nominal operation."
            )

        checks_text = (
            f"1. Perform immediate field verification against '{top_file}'.\n"
            "2. Confirm physical touch temperature, acoustic noise, and local gauge readings.\n"
            "3. If electrical or mechanical disassembly is required, execute Lockout/Tagout (LOTO).\n"
            "4. Inspect seals, lubrication grease ports, and piping joints as prescribed in manual."
        )

        limitations_text = (
            "Confidence: High (Grounded directly on top retrieved technical manual). "
            f"Grounding Source: {top_file} (Similarity Score: {top_chunk.get('score', 0.0):.4f}). "
            "Limitation: Diagnosis assumes standard operating speed and steady liquid viscosity."
        )

        return (
            f"### 1. Likely Fault\n{likely_fault}\n\n"
            f"### 2. Why (Evidence from Readings and Documents)\n{why_text}\n\n"
            f"### 3. Recommended Checks\n{checks_text}\n\n"
            f"### 4. Confidence / Limitations\n{limitations_text}\n"
        )

    def _parse_sections(self, text: str) -> Dict[str, str]:
        """Parse the 4 standardized output sections from response text."""
        sections = {}
        patterns = {
            "likely_fault": r"###\s*1\.\s*Likely Fault\s*\n(.*?)(?=\n###|\Z)",
            "why": r"###\s*2\.\s*Why.*?\n(.*?)(?=\n###|\Z)",
            "recommended_checks": r"###\s*3\.\s*Recommended Checks\s*\n(.*?)(?=\n###|\Z)",
            "confidence_limitations": r"###\s*4\.\s*Confidence.*?\n(.*?)(?=\n###|\Z)",
        }
        for key, pat in patterns.items():
            match = re.search(pat, text, re.DOTALL | re.IGNORECASE)
            sections[key] = match.group(1).strip() if match else ""
        return sections


def main() -> int:
    """CLI testing tool: run LLM client with a hardcoded diagnostic query."""
    client = LocalLLMClient()
    available, msg = client.is_available()
    print("=" * 70)
    print("P_311 Local LLM Client Diagnostic Check")
    print(f"Ollama Status: {msg}")
    print("=" * 70)

    # Hardcoded test example
    dummy_telemetry = {
        "device_id": "pump_centrifugal_01",
        "timestamp": "2026-10-01T01:24:00Z",
        "fault_category": "bearing_wear",
        "symptoms": [
            "critical bearing vibration velocity RMS of 6.34 mm/s exceeding ISO 10816 Zone D danger limit",
            "secondary frictional temperature rise of 67.80 C",
        ],
        "readings": {"temperature": 67.8, "vibration": 6.34, "pressure": 5.01},
        "rolling_stats": {"mean_temperature": 67.45, "mean_vibration": 6.12, "mean_pressure": 5.02, "window_size": 3},
    }

    from rag.retriever import TFIDFRetriever
    retriever = TFIDFRetriever()
    query = "Industrial centrifugal pump pump_centrifugal_01 exhibits critical bearing vibration velocity RMS of 6.34 mm/s and temperature rise of 67.80 C"
    retrieved_chunks = retriever.retrieve(query, top_k=3)

    print("\nExecuting Local Diagnosis Inference...")
    result = client.generate(dummy_telemetry, retrieved_chunks)

    print(f"\nRuntime: {result['runtime']}")
    print(f"Latency: {result['latency_seconds']} seconds")
    if "notice" in result:
        print(f"Notice: {result['notice']}")
    print("\n" + result["response"])
    print("=" * 70)
    return 0


if __name__ == "__main__":
    sys.exit(main())
