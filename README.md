# P_311: Knowledge-Driven IoT Fault Diagnosis Assistant

An AI-assisted industrial fault diagnosis system combining real-time IoT sensor telemetry, rule-based explainable anomaly detection, local semantic knowledge retrieval (RAG), and an offline local Large Language Model (LLM).

---

## 1. System Pipeline

```text
+-----------------------+       MQTT (Mosquitto)       +------------------------+
|   Sensor Simulator    | ---------------------------> |   Python Subscriber    |
| (Centrifugal Pump T/V/P) |      Port 1883 (JSON)      | (paho-mqtt 2.x API v2) |
+-----------------------+                              +------------------------+
                                                                   |
                                                                   v
                                                       +------------------------+
                                                       | Fault Detection Engine |
                                                       | (Thresholds & Windows) |
                                                       +------------------------+
                                                                   | (When Fault Detected)
                                                                   v
+-----------------------+                              +------------------------+
| Local LLM (Ollama)    | <--------------------------- | RAG Retrieval Engine   |
| (llama3.2:3b offline) |      Symptom Summary +       | (Indexed Maintenance   |
+-----------------------+      Context Passages        |  Knowledge Base)       |
            |                                          +------------------------+
            v
+-------------------------------------------------------+
| Structured Diagnostic Report                         |
| - Likely Fault Mode                                   |
| - Technical Root-Cause Explanation                     |
| - Prescribed Corrective Checks & Actions              |
| - Confidence & Physical Operating Limits              |
+-------------------------------------------------------+
```

---

## 2. Directory Architecture

```text
p311_iot_fault_diagnosis/
├── config.py             # Central single-source-of-truth configuration
├── main.py               # Main application entry point and pipeline orchestrator
├── requirements.txt      # Minimal pinned dependencies
├── README.md             # Project documentation and setup guide
├── .gitignore            # Git exclusion rules (cache, venv, models)
├── mqtt/                 # MQTT publisher and subscriber modules
│   ├── sensor_simulator.py
│   └── mqtt_subscriber.py
├── diagnosis/            # Symptom extraction and rule-based fault detection
├── knowledge_base/       # Markdown diagnostic manuals and procedures
├── rag/                  # Chunking, local embedding, and similarity retrieval
├── llm/                  # Offline Ollama client and prompt templates
├── data/                 # Diagnostic run logs and telemetry traces
├── tests/                # Unit and integration test suites
└── docs/                 # Architectural decisions, evaluation reports, viva prep
    └── decisions.md      # Binding design and scoping decisions
```

---

## 3. Prerequisites (Windows)

1. **Operating System:** Windows 10 / 11 with PowerShell 5.1+.
2. **Python:** Python 3.13+ installed and accessible via `python`.
3. **MQTT Broker:** Eclipse Mosquitto installed as a Windows service on port 1883 (`C:\Program Files\mosquitto`).
4. **Git:** Git for Windows installed.

---

## 4. Setup Instructions (PowerShell)

### Step 1: Open PowerShell in the Project Directory
```powershell
cd 'C:\Users\SANCHAY\OneDrive\Desktop\files'
```

### Step 2: Create and Activate the Virtual Environment
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```
*(Verify that `(.venv)` appears at the start of your PowerShell prompt).*

### Step 3: Install Required Dependencies
```powershell
pip install --upgrade pip
pip install -r requirements.txt
```

### Step 4: Verify Installation
```powershell
python -c "import paho.mqtt.client as mqtt; print('paho-mqtt successfully loaded, version:', mqtt.__version__)"
```

### Step 5: Verify Mosquitto Service Status
```powershell
Get-Service -Name mosquitto
```
Ensure the status shows `Running`. If not running, start it:
```powershell
Start-Service -Name mosquitto
```

---

## 5. Execution

- Run baseline system test:
  ```powershell
  python main.py
  ```

---

## 6. Monitored Machine Specifications

- **Machine Type:** Industrial Centrifugal Pump with 3-phase AC induction drive motor.
- **Sensors:**
  - **Motor/Bearing Temperature:** °C (Nominal: 45–65°C, Warning: > 75°C)
  - **Vibration Velocity RMS:** mm/s (Nominal: 0.8–2.5 mm/s, Warning: > 4.5 mm/s per ISO 10816)
  - **Discharge Pressure:** bar (Nominal: 4.0–6.0 bar, Warning: < 3.0 bar)
