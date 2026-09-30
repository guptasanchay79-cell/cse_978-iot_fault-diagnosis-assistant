"""P_311: Knowledge-Driven IoT Fault Diagnosis Assistant.

Module: llm/prompts.py
System prompts and structured context formatting templates for the local LLM.
Enforces strict grounding on retrieved knowledge chunks and physical telemetry,
prohibiting hallucination and mandating standardized diagnostic sections.
"""

from typing import Any, Dict, List

DIAGNOSIS_SYSTEM_PROMPT = """You are an expert industrial IoT reliability engineer and fault diagnosis assistant for centrifugal pumps.
Your task is to analyze the provided IoT telemetry anomaly and explain the root cause using ONLY the provided retrieved technical context.

STRICT OPERATIONAL RULES:
1. Grounding: Answer ONLY from the retrieved context documents and observed sensor readings. Do NOT invent facts or cite external training data.
2. Insufficient Context: If the retrieved documents do not contain enough information to diagnose the issue with certainty, explicitly state this in the Confidence/Limitations section.
3. Output Format: Your response MUST strictly contain the following four exact headings:

### 1. Likely Fault
[State the single most probable mechanical, thermal, hydraulic, or sensor failure mode]

### 2. Why (Evidence from Readings and Documents)
[Explain the physical rationale by citing specific sensor values, thresholds, and evidence from the retrieved documentation]

### 3. Recommended Checks
[List sequential, actionable diagnostic and maintenance verification steps]

### 4. Confidence / Limitations
[State confidence level (High/Medium/Low) and note physical limitations or missing parameters]
"""


def build_diagnosis_prompt(
    telemetry_summary: Dict[str, Any],
    retrieved_chunks: List[Dict[str, Any]],
) -> str:
    """Format observed telemetry and retrieved knowledge chunks into a grounded LLM prompt."""
    device_id = telemetry_summary.get("device_id", "unknown_device")
    timestamp = telemetry_summary.get("timestamp", "unknown_time")
    readings = telemetry_summary.get("readings", {})
    rolling_stats = telemetry_summary.get("rolling_stats", {})
    symptoms = telemetry_summary.get("symptoms", [])

    # Format telemetry section
    telemetry_text = (
        f"Device Identifier: {device_id}\n"
        f"Timestamp: {timestamp}\n"
        f"Observed Symptoms:\n"
        + "\n".join(f"  - {s}" for s in symptoms)
        + "\n"
        f"Instantaneous Sensor Readings:\n"
        f"  - Temperature: {readings.get('temperature', 'N/A')} °C\n"
        f"  - Vibration Velocity RMS: {readings.get('vibration', 'N/A')} mm/s\n"
        f"  - Discharge Pressure: {readings.get('pressure', 'N/A')} bar\n"
    )

    if rolling_stats:
        telemetry_text += (
            f"Rolling Window Averages ({rolling_stats.get('window_size', 3)} samples):\n"
            f"  - Mean Temperature: {rolling_stats.get('mean_temperature', 'N/A')} °C\n"
            f"  - Mean Vibration: {rolling_stats.get('mean_vibration', 'N/A')} mm/s\n"
            f"  - Mean Pressure: {rolling_stats.get('mean_pressure', 'N/A')} bar\n"
        )

    # Format retrieved context chunks
    context_text = ""
    for idx, chunk in enumerate(retrieved_chunks, 1):
        source = chunk.get("source_file", "unknown_source")
        score = chunk.get("score", 0.0)
        content = chunk.get("content", "").strip()
        context_text += (
            f"--- [DOCUMENT CHUNK #{idx} | Source: {source} | Similarity Score: {score:.4f}] ---\n"
            f"{content}\n\n"
        )

    full_prompt = (
        f"{DIAGNOSIS_SYSTEM_PROMPT}\n\n"
        f"==================== OBSERVED TELEMETRY ====================\n"
        f"{telemetry_text}\n"
        f"==================== RETRIEVED KNOWLEDGE CONTEXT ====================\n"
        f"{context_text}\n"
        f"==================== DIAGNOSTIC REPORT ====================\n"
    )

    return full_prompt
