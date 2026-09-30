"""P_311: Knowledge-Driven IoT Fault Diagnosis Assistant.

Module: diagnosis/fault_detector.py
Rule-based, explainable symptom extraction engine.
Processes incoming IoT telemetry through a short rolling window,
detects physical and sensor anomalies against industrial thresholds,
and synthesizes a structured symptom summary and RAG retrieval query.
"""

from collections import deque
import logging
from pathlib import Path
import sys
from typing import Any, Deque, Dict, List, Optional

# Ensure project root is in sys.path
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from config import (
    DETECTION_WINDOW_SIZE,
    PRESSURE_LOW_THRESHOLD,
    PRESSURE_VALID_RANGE,
    SENSOR_FLATLINE_EPSILON,
    TEMP_NORMAL_MAX,
    TEMP_RATE_OF_CLIMB_THRESHOLD,
    TEMP_VALID_RANGE,
    TEMP_WARNING_THRESHOLD,
    VIB_VALID_RANGE,
    VIB_WARNING_THRESHOLD,
)

logging.basicConfig(
    stream=sys.stdout,
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("FaultDetector")


class FaultDetector:
    """Stateful, rule-based anomaly detector using rolling windows.

    Applies deterministic, explainable thresholds and statistical rules
    to isolate mechanical, thermal, hydraulic, and sensor failures.
    """

    def __init__(self, window_size: int = DETECTION_WINDOW_SIZE) -> None:
        self.window_size = window_size
        self._history: Deque[Dict[str, Any]] = deque(maxlen=window_size)
        self.faults_detected_count = 0

    def reset(self) -> None:
        """Clear rolling history."""
        self._history.clear()

    def process_reading(self, reading: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Ingest a telemetry reading and evaluate anomaly rules.

        Returns:
            Structured anomaly dictionary if a fault condition is confirmed,
            or None if the machine is operating within healthy boundaries.
        """
        # Append latest reading to rolling window
        self._history.append(reading)

        device_id = reading.get("device_id", "unknown_device")
        timestamp = reading.get("timestamp", "")
        temp = float(reading.get("temperature", 0.0))
        vib = float(reading.get("vibration", 0.0))
        pressure = float(reading.get("pressure", 0.0))

        # Check for immediate physical out-of-range / disconnect (does not require full window)
        out_of_range_symptoms: List[str] = []
        if not (TEMP_VALID_RANGE[0] <= temp <= TEMP_VALID_RANGE[1]):
            out_of_range_symptoms.append(
                f"temperature sensor reading ({temp:.1f} C) is outside physical valid range "
                f"[{TEMP_VALID_RANGE[0]}, {TEMP_VALID_RANGE[1]}] C (sensor disconnect / open-circuit)"
            )
        if not (VIB_VALID_RANGE[0] <= vib <= VIB_VALID_RANGE[1]):
            out_of_range_symptoms.append(
                f"vibration sensor reading ({vib:.1f} mm/s) is outside physical valid range"
            )
        if not (PRESSURE_VALID_RANGE[0] <= pressure <= PRESSURE_VALID_RANGE[1]):
            out_of_range_symptoms.append(
                f"pressure sensor reading ({pressure:.1f} bar) is outside physical valid range"
            )

        if out_of_range_symptoms:
            self.faults_detected_count += 1
            query = (
                f"Industrial centrifugal pump {device_id} telemetry sensor failure: "
                f"{'; '.join(out_of_range_symptoms)}."
            )
            return {
                "device_id": device_id,
                "timestamp": timestamp,
                "has_fault": True,
                "fault_category": "sensor_failure",
                "symptoms": out_of_range_symptoms,
                "readings": {"temperature": temp, "vibration": vib, "pressure": pressure},
                "rolling_stats": {"window_size": len(self._history)},
                "query": query,
            }

        # For physical anomalies and flatline, require at least window_size readings
        # to filter out single-sample noise spikes
        if len(self._history) < self.window_size:
            return None

        # Calculate rolling statistics across the active window
        temps = [float(r["temperature"]) for r in self._history]
        vibs = [float(r["vibration"]) for r in self._history]
        pressures = [float(r["pressure"]) for r in self._history]

        mean_temp = sum(temps) / len(temps)
        mean_vib = sum(vibs) / len(vibs)
        mean_pressure = sum(pressures) / len(pressures)

        temp_range = max(temps) - min(temps)
        vib_range = max(vibs) - min(vibs)

        symptoms: List[str] = []
        fault_category = "none"

        # ----------------------------------------------------------------------
        # Rule 1: Frozen / Flatline Sensor Malfunction
        # If the sensor reading has virtually zero variance across the window
        # ----------------------------------------------------------------------
        if temp_range < SENSOR_FLATLINE_EPSILON:
            symptoms.append(
                f"temperature sensor flat-line detected: value frozen at {mean_temp:.2f} C "
                f"with 0.00 variance across {self.window_size} consecutive readings"
            )
            fault_category = "sensor_failure"

        # ----------------------------------------------------------------------
        # Rule 2: Critical Bearing Degradation (ISO 10816 Zone D)
        # ----------------------------------------------------------------------
        elif mean_vib >= VIB_WARNING_THRESHOLD:
            fault_category = "bearing_wear"
            symptoms.append(
                f"critical bearing vibration velocity RMS of {mean_vib:.2f} mm/s "
                f"exceeding ISO 10816 Zone D danger limit of {VIB_WARNING_THRESHOLD:.1f} mm/s"
            )
            # Check for secondary frictional heating
            if mean_temp > TEMP_NORMAL_MAX:
                symptoms.append(
                    f"secondary frictional temperature rise of {mean_temp:.2f} C "
                    f"above normal running threshold ({TEMP_NORMAL_MAX:.1f} C)"
                )

        # ----------------------------------------------------------------------
        # Rule 3: Severe Overheating / Cooling Failure
        # ----------------------------------------------------------------------
        elif mean_temp >= TEMP_WARNING_THRESHOLD:
            fault_category = "overheating"
            symptoms.append(
                f"severe motor stator / bearing overheating at {mean_temp:.2f} C "
                f"exceeding thermal safety threshold of {TEMP_WARNING_THRESHOLD:.1f} C"
            )
            # Check rate of climb across window
            rate_of_climb = (temps[-1] - temps[0]) / (len(temps) - 1)
            if rate_of_climb >= TEMP_RATE_OF_CLIMB_THRESHOLD:
                symptoms.append(
                    f"rapid thermal climb rate of +{rate_of_climb:.2f} C per sample step"
                )

        # ----------------------------------------------------------------------
        # Rule 4: Discharge Pressure Loss / Leak / Cavitation
        # ----------------------------------------------------------------------
        elif mean_pressure <= PRESSURE_LOW_THRESHOLD:
            fault_category = "pressure_drop"
            symptoms.append(
                f"critical hydraulic discharge pressure drop to {mean_pressure:.2f} bar "
                f"falling below low operational limit of {PRESSURE_LOW_THRESHOLD:.1f} bar"
            )
            # Check for cavitation-induced vibration jitter
            if mean_vib >= 1.8:
                symptoms.append(
                    f"hydraulic cavitation turbulence with vibration fluctuations of {mean_vib:.2f} mm/s"
                )

        # If any symptoms were triggered, construct the structured diagnosis payload
        if symptoms:
            self.faults_detected_count += 1
            query = self._build_rag_query(
                device_id=device_id,
                fault_category=fault_category,
                symptoms=symptoms,
                temp=mean_temp,
                vib=mean_vib,
                pressure=mean_pressure,
            )

            result = {
                "device_id": device_id,
                "timestamp": timestamp,
                "has_fault": True,
                "fault_category": fault_category,
                "symptoms": symptoms,
                "readings": {
                    "temperature": round(temp, 2),
                    "vibration": round(vib, 2),
                    "pressure": round(pressure, 2),
                },
                "rolling_stats": {
                    "mean_temperature": round(mean_temp, 2),
                    "mean_vibration": round(mean_vib, 2),
                    "mean_pressure": round(mean_pressure, 2),
                    "window_size": self.window_size,
                },
                "query": query,
            }
            logger.warning(
                "[FAULT DETECTED] Device=%s | Category=%s | Symptoms=%s",
                device_id,
                fault_category,
                "; ".join(symptoms),
            )
            return result

        # Normal steady-state operation: no fault triggered
        return None

    @staticmethod
    def _build_rag_query(
        device_id: str,
        fault_category: str,
        symptoms: List[str],
        temp: float,
        vib: float,
        pressure: float,
    ) -> str:
        """Synthesize a rich plain-English symptom query sentence for RAG retrieval."""
        symptom_str = ", and ".join(symptoms)
        return (
            f"Industrial centrifugal pump {device_id} exhibits {symptom_str}. "
            f"Current telemetry shows temperature {temp:.2f} C, vibration {vib:.2f} mm/s, "
            f"and discharge pressure {pressure:.2f} bar."
        )
