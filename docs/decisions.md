# Project Decisions Record — P_311

This document records all foundational architectural and scoping decisions confirmed for project **P_311: Knowledge-Driven IoT Fault Diagnosis Assistant**. Every decision here is binding for subsequent implementation stages unless explicitly renegotiated.

---

## Decision 0: Project Workspace & File System Path

- **Decision:** Maintain the active workspace at `C:\Users\SANCHAY\OneDrive\Desktop\files`, while directing local LLM model weights to Drive `D:` (`D:\ollama\models`).
- **Reason:** The current workspace path contains no spaces and is directly opened in the IDE/editor. Setting `OLLAMA_MODELS=D:\ollama\models` preserves the 337 GB free space on Drive `D:` for model checkpoints without requiring the user to switch workspace directories.
- **Reference in Roadmap:** Stage 0 & Stage 1 Decision point.

---

## Decision 1: User Interface vs. CLI

- **Decision:** Polished Command Line Interface (CLI) / terminal application only. No graphical or web UI will be built.
- **Reason:** The official HCL problem statement requires only an IoT telemetry pipeline, knowledge base, and local RAG/LLM. A web UI would introduce unnecessary frontend complexity, external frameworks, and potential points of failure during the viva. A clean terminal interface with structured logging and formatted tables directly demonstrates system engineering.
- **Reference in Roadmap:** Stage 0, Question 1; Stage 9.

---

## Decision 2: UI Tooling & Impeccable Skill

- **Decision:** Not applicable.
- **Reason:** CLI interface confirmed in Decision 1. System check also verified that the *Impeccable* design skill is not installed in the Antigravity IDE environment.
- **Reference in Roadmap:** Stage 0, Question 7.

---

## Decision 3: Local LLM Runtime, Model Selection & Storage

- **Decision:** Use **Ollama** as the local LLM runtime, configured to store model weights on Drive `D:` via `OLLAMA_MODELS=D:\ollama\models`. The primary model will be `llama3.2:3b` (or `phi3:mini` as fallback).
- **Reason:**
  - Hardware specs: Intel Core CPU, 16 GB System RAM, NVIDIA GeForce RTX 3050 Laptop GPU (4 GB VRAM).
  - Storage specs: Drive `C:` has ~3.96 GB free (insufficient for model cache), Drive `D:` has 337 GB free.
  - A 3B parameter model quantized to 4-bit requires ~2.0 GB VRAM/RAM, executing in sub-second to low-second latency locally on the RTX 3050 without out-of-memory errors.
- **Reference in Roadmap:** Stage 0, Question 2; Stage 7.

---

## Decision 4: Academic Deliverables & Format

- **Decision:** Standard comprehensive university engineering format:
  1. Complete project report outline (Abstract, Problem Statement, System Architecture, Telemetry Pipeline, RAG Retrieval, LLM Grounding, Evaluation Results, Viva Prep).
  2. Slide-by-slide PPT presentation outline.
  3. Viva questions and defense answers document (`docs/viva_prep.md`).
- **Reason:** Ensures thorough academic rigor and complete alignment with college evaluation criteria.
- **Reference in Roadmap:** Stage 0, Question 3; Stage 11.

---

## Decision 5: Machine Domain Selection

- **Decision:** **Industrial Centrifugal Pump with Electric Drive Motor**.
- **Reason:** Centrifugal pumps are ubiquitous in industrial plants (water treatment, chemical, power generation), intuitive for viva examiners to understand, and exhibit well-documented physical fault signatures across temperature, vibration, and hydraulic pressure.
- **Reference in Roadmap:** Stage 0, Question 4.

---

## Decision 6: Telemetry Sensors & Baseline Parameters

- **Decision:** Three core continuous sensor streams:
  1. **Motor & Bearing Temperature (`temperature`):** Unit °C. Normal range: 45.0°C – 65.0°C.
  2. **Vibration Velocity RMS (`vibration`):** Unit mm/s. Normal range: 0.5 mm/s – 2.5 mm/s (ISO 10816 industrial vibration standards).
  3. **Discharge Pressure (`pressure`):** Unit bar. Normal range: 4.0 bar – 6.0 bar.
- **Reason:** These three physical quantities cleanly isolate mechanical, thermal, and hydraulic failure modes.
- **Reference in Roadmap:** Stage 0, Question 5; Stage 3.

---

## Decision 7: Diagnosable Fault Modes & Signatures

- **Decision:** Four distinct fault modes plus normal baseline:
  1. **Normal Operation:** Readings drift smoothly within healthy ranges with low Gaussian noise.
  2. **Overheating:** Temperature climbs above 75.0°C; vibration and pressure remain normal.
  3. **Bearing Wear:** Vibration spikes above 4.5 mm/s; temperature gradually increases due to friction.
  4. **Pressure Drop (Discharge Leak / Cavitation):** Pressure drops below 3.0 bar; vibration exhibits high-frequency instability.
  5. **Sensor Failure / Flat-line:** Sensor value abruptly locks to a constant or drops to null/out-of-range (-999).
- **Reason:** Each mode has a deterministic, explainable rule-based symptom profile that the detector can extract and the RAG/LLM can diagnose.
- **Reference in Roadmap:** Stage 0, Question 5; Stage 3; Stage 4.

---

## Decision 8: Knowledge Base Strategy & Attribution

- **Decision:** Diagnostic knowledge base documents (~12–15 Markdown files) will be drafted systematically based on standard industrial pump maintenance procedures and ISO 10816 standards, then reviewed and approved by the user. Every document's provenance will be logged in `docs/knowledge_sources.md`.
- **Reason:** Adheres to Constraint 5 (honesty regarding sources). Never misrepresent synthetic technical summaries as proprietary OEM manuals.
- **Reference in Roadmap:** Stage 0, Question 6; Stage 5.

---

## Decision 9: MQTT & Software Environment Standards

- **Decision:**
  - Python 3.13.x with a dedicated virtual environment (`.venv`).
  - `paho-mqtt` 2.x API using `CallbackAPIVersion.VERSION2`.
  - Mosquitto Windows service on `localhost:1883` (verified running).
  - Telemetry payloads strictly formatted as JSON containing `device_id`, `timestamp`, and sensor values.
  - No cloud services, databases, or unnecessary heavy frameworks.
- **Reason:** Strict adherence to project constraints and Viva explainability.
- **Reference in Roadmap:** Section 2 & 3 of `prompt.md`.
