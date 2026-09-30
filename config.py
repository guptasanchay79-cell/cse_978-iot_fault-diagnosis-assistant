"""P_311: Knowledge-Driven IoT Fault Diagnosis Assistant.

Central configuration module.
All system parameters, MQTT settings, physical sensor thresholds,
and RAG/LLM configurations are maintained in this single source of truth.
"""

from pathlib import Path

# ==============================================================================
# 1. Project Directory Paths
# ==============================================================================
BASE_DIR: Path = Path(__file__).resolve().parent
KNOWLEDGE_BASE_DIR: Path = BASE_DIR / "knowledge_base"
DATA_DIR: Path = BASE_DIR / "data"
DOCS_DIR: Path = BASE_DIR / "docs"

# ==============================================================================
# 2. MQTT Broker & Networking Configuration
# ==============================================================================
# Mosquitto runs locally as a Windows service on the standard MQTT port 1883.
MQTT_BROKER_HOST: str = "localhost"
MQTT_BROKER_PORT: int = 1883
MQTT_KEEPALIVE_SECONDS: int = 60

# Topic for publishing and consuming centrifugal pump telemetry
MQTT_TELEMETRY_TOPIC: str = "industrial/pump/centrifugal_01/telemetry"
MQTT_DIAGNOSIS_TOPIC: str = "industrial/pump/centrifugal_01/diagnosis"

# Default Device Identifier
DEFAULT_DEVICE_ID: str = "pump_centrifugal_01"

# Telemetry streaming interval in seconds (1 message per second)
TELEMETRY_PUBLISH_INTERVAL: float = 1.0

# Supported operational and fault simulation modes
FAULT_MODE_NORMAL: str = "normal"
FAULT_MODE_OVERHEATING: str = "overheating"
FAULT_MODE_BEARING_WEAR: str = "bearing_wear"
FAULT_MODE_PRESSURE_DROP: str = "pressure_drop"
FAULT_MODE_SENSOR_FAILURE: str = "sensor_failure"

ALL_FAULT_MODES: list[str] = [
    FAULT_MODE_NORMAL,
    FAULT_MODE_OVERHEATING,
    FAULT_MODE_BEARING_WEAR,
    FAULT_MODE_PRESSURE_DROP,
    FAULT_MODE_SENSOR_FAILURE,
]

# Physical simulation parameters for smooth random-walk telemetry
SIM_NOISE_STD_TEMP: float = 0.35      # Small thermal noise (°C)
SIM_NOISE_STD_VIB: float = 0.08       # Mechanical vibration noise (mm/s)
SIM_NOISE_STD_PRESSURE: float = 0.06  # Hydraulic pressure noise (bar)
SIM_MEAN_REVERSION_RATE: float = 0.15 # Restoring force towards setpoint

# ==============================================================================
# 3. Machine Physical Parameters & Thresholds (Centrifugal Pump)
# ==============================================================================
# Baseline ranges represent nominal steady-state operation of an industrial pump.
# Thresholds are derived from standard industrial machinery guidelines (ISO 10816).

# Temperature (°C) — Measured at pump motor and drive-end bearings
# Nominal operating range: 45.0°C to 65.0°C
TEMP_NORMAL_MIN: float = 45.0
TEMP_NORMAL_MAX: float = 65.0
# Warning threshold: Temperatures exceeding 75.0°C indicate insufficient cooling,
# excessive friction, or electrical overload.
TEMP_WARNING_THRESHOLD: float = 75.0

# Vibration Velocity RMS (mm/s) — Measured radially at bearing housing
# ISO 10816-3 Class II (medium industrial machines):
#   < 2.8 mm/s: Good (Zone A/B)
#   2.8 - 4.5 mm/s: Acceptable (Zone C)
#   > 4.5 mm/s: Unsatisfactory / Danger (Zone D)
VIB_NORMAL_MIN: float = 0.8
VIB_NORMAL_MAX: float = 2.5
# Warning threshold: Vibration > 4.5 mm/s signifies mechanical looseness,
# severe bearing degradation, or severe dynamic unbalance.
VIB_WARNING_THRESHOLD: float = 4.5

# Discharge Pressure (bar) — Measured at the pump discharge nozzle
# Nominal operating range under standard head: 4.0 bar to 6.0 bar
PRESSURE_NORMAL_MIN: float = 4.0
PRESSURE_NORMAL_MAX: float = 6.0
# Warning threshold: Pressure falling below 3.0 bar indicates discharge leakage,
# line rupture, severe pump cavitation, or suction blockage.
PRESSURE_LOW_THRESHOLD: float = 3.0

# Sensor validity limits (used to detect flat-line, disconnected, or erratic sensors)
TEMP_VALID_RANGE: tuple[float, float] = (-20.0, 150.0)
VIB_VALID_RANGE: tuple[float, float] = (0.0, 50.0)
PRESSURE_VALID_RANGE: tuple[float, float] = (0.0, 25.0)

# ==============================================================================
# 4. Fault Detection & Pipeline Cooldown
# ==============================================================================
# Number of consecutive anomalous readings required before triggering diagnosis.
# Prevents single-sample sensor spikes/noise from calling the LLM unnecessarily.
DETECTION_WINDOW_SIZE: int = 3

# Minimum seconds to wait between LLM diagnostic calls for the same fault condition.
# Prevents flooding the local model with duplicate inference requests.
LLM_DIAGNOSIS_COOLDOWN_SECONDS: float = 30.0

# ==============================================================================
# 5. Local RAG & Embedding Settings
# ==============================================================================
# Number of top knowledge chunks to retrieve for LLM context grounding
RAG_TOP_K: int = 3

# Minimum cosine similarity threshold to consider a retrieved chunk relevant
RAG_SIMILARITY_THRESHOLD: float = 0.35

# ==============================================================================
# 6. Local LLM Configuration (Ollama)
# ==============================================================================
# Ollama service endpoint (default localhost port 11434)
OLLAMA_API_BASE_URL: str = "http://localhost:11434"

# Primary local model (quantized 4-bit, fits within 4GB VRAM / 16GB RAM)
LLM_MODEL_NAME: str = "llama3.2:3b"

# Inference generation parameters
LLM_TEMPERATURE: float = 0.1  # Low temperature for strict factual grounding
LLM_REQUEST_TIMEOUT_SECONDS: float = 45.0
