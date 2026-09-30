# P_311 Roadmap — Knowledge-Driven IoT Fault Diagnosis Assistant

**Source of truth for scope (from the HCL project list):**

| Field | Value |
|---|---|
| Domain | Embedded IoT |
| Sub-domain | Industrial Support |
| Tech stack | **MQTT + Python + Local LLM + RAG** |
| Objective | Provide AI-assisted IoT fault diagnosis |
| Description | Combine IoT telemetry, a searchable knowledge base, and a local RAG/LLM system to explain likely faults and recommended checks. |

**Core pipeline:**

```text
Sensor Simulator → MQTT (Mosquitto) → Python subscriber → Fault detection
      → RAG retrieval over knowledge base → Local LLM → Likely fault + explanation + recommended checks
```

**Rules for this roadmap**

- Stay inside the stack above. Anything extra (web UI, database, Docker, cloud) is added only if explicitly approved in Stage 0.
- Build one stage at a time. Each stage ends with a working, demonstrable result and a commit.
- Do not start a stage until the previous one's "Done when" checks pass.
- Nothing is assumed. If a stage has an open choice, ask (see Stage 0 and the "Decision points" inside stages).

---

## Current status (as of 2026-09-30)

Already done:

- Python installed, `.venv` created in the project folder.
- Mosquitto installed and **already running as a Windows service on port 1883** (do not start a second broker with `mosquitto -v`).
- `paho-mqtt` 2.1.0 installed in the project `.venv`.
- First drafts exist: `mqtt/sensor_simulator.py` (random values, `key=value` string payload) and `mqtt/mqtt_subscriber.py`. End-to-end run (both at once showing `Published` and `Received`) **has not been confirmed yet**.

Not started: fault logic, knowledge base, RAG, local LLM, integration, testing, documentation.

---

## Stage 0 — Clarify before building

**Goal:** remove every open question so later stages need no guessing.

Questions to ask the user and record answers in `docs/decisions.md`:

1. Does the college require a UI/dashboard, or is a CLI/terminal demo acceptable? (The project spec lists no UI.)
2. Which local LLM runtime does the user want or already have installed (for example Ollama or llama.cpp)? Which model? What are the PC's RAM, GPU/VRAM, and free disk space?
3. Does the college give specific deliverables or a format (report template, PPT, viva topics, submission date)?
4. Is there a named machine or domain to simulate (motor, pump, compressor, HVAC, generic)? If none, ask the user to choose.
5. Which sensors and fault types does the user want? (Proposed default to confirm, not assume: temperature, vibration, pressure; faults such as overheating, bearing wear, pressure drop, sensor failure.)
6. Should the knowledge base be written by the user, generated with help, or taken from real manuals? (Needs to be accurate and honest about its source.)
7. Is the Impeccable design skill installed in Antigravity? If a UI is approved, confirm the exact tool/skill and how to use it.

**Done when:** `docs/decisions.md` exists with every answer, and the user has confirmed it.

---

## Stage 1 — Project baseline

**Goal:** a clean, reproducible project.

- Confirm folder structure:
  ```text
  mqtt/  diagnosis/  knowledge_base/  rag/  llm/  data/  tests/  docs/
  main.py  requirements.txt  README.md  .gitignore
  ```
- Add `.gitignore` (`.venv/`, `__pycache__/`, vector index/cache folders, model files).
- Initialise Git, first commit.
- Put config (broker host, port, topic names) in one `config.py`, not scattered across files.
- Generate `requirements.txt` from the `.venv` (only what is installed and needed).
- README skeleton: what the project is, how to set up on Windows/PowerShell.

**Decision point:** folder names with spaces in the path (`cse_978 Fault diagnosis iot`) can break commands. Ask the user whether to keep the folder name or move it.

**Done when:** fresh clone + `pip install -r requirements.txt` works, and `python -c "import paho.mqtt.client"` succeeds inside `.venv`.

---

## Stage 2 — MQTT pipeline (confirm end to end)

**Goal:** prove telemetry flows simulator → broker → subscriber.

- Verify broker is reachable on `localhost:1883`.
- Switch payloads to **JSON** with fields: `device_id`, `timestamp`, and each sensor reading.
- Use `paho-mqtt` 2.x callback API (`CallbackAPIVersion.VERSION2`).
- Subscriber parses JSON, validates fields, handles bad messages without crashing.
- Clean shutdown on Ctrl+C for both scripts.

**Done when:** running both scripts together shows matching `Published` and `Received` lines, and a deliberately malformed message is logged and skipped.

---

## Stage 3 — Realistic simulator with fault modes

**Goal:** generate data that actually contains diagnosable faults.

- Normal operation: values drift smoothly around a healthy baseline with small noise (not pure `random.uniform`).
- Fault modes selectable by command-line argument or config (confirmed list from Stage 0), each with a clear signature. Example shape only, final values agreed with the user:
  - overheating: temperature climbs, vibration normal
  - bearing wear: vibration rises, temperature rises slowly
  - pressure drop: pressure falls, other values normal
  - sensor failure: flat-line or out-of-range readings
- Each message carries a hidden `ground_truth_fault` label **only in a separate test mode**, so diagnosis can be scored later without leaking the answer to the detector.

**Done when:** running each mode produces visibly different telemetry, documented in `docs/fault_signatures.md`.

---

## Stage 4 — Fault detection (symptom extraction)

**Goal:** turn raw telemetry into a structured symptom summary for the RAG step.

- Start with simple, explainable logic: thresholds and short rolling windows (for example average of the last N readings, rate of change).
- Output a structured object, e.g. `{"device_id": ..., "symptoms": ["high vibration", "rising temperature"], "readings": {...}}`.
- Also produce a short plain-English symptom sentence used as the retrieval query in Stage 6.
- Thresholds live in `config.py` with comments explaining each number.
- No machine learning here unless the user asks. The spec's ML is the LLM/RAG layer.

**Done when:** each simulator fault mode triggers the expected symptoms, and normal mode triggers none (unit tests in `tests/`).

---

## Stage 5 — Knowledge base

**Goal:** a searchable set of technical documents the RAG system will use.

- Plain `.md` or `.txt` files in `knowledge_base/`, one fault/topic per file (about 10 to 15 to start).
- Consistent structure per file: fault name, symptoms, likely causes, diagnostic checks, recommended actions, safety notes.
- Content must match the fault modes from Stage 3, plus a few distractor topics so retrieval has something to get wrong.
- Record the source of each document in `docs/knowledge_sources.md` (written by user, written by assistant and reviewed, or from a real manual). Never present invented content as a real manufacturer manual.

**Done when:** user has reviewed the files and confirmed the facts look reasonable.

---

## Stage 6 — RAG retrieval

**Goal:** given a symptom query, return the most relevant knowledge chunks.

- Chunk documents (simple, section-based chunking is enough).
- Embed locally. **Decision point:** ask the user before choosing an embedding model and whether a vector store (Chroma/FAISS) is needed or plain cosine similarity over a small in-memory index is enough. Prefer the simplest thing that works for about 15 documents.
- Build/load the index from `knowledge_base/`; rebuild only when files change.
- Return top-k chunks with source file names and scores.
- Script to test retrieval alone: type a symptom sentence, see ranked chunks.

**Done when:** for every fault mode's symptom sentence, the correct document ranks in the top 3. Record results in `docs/retrieval_results.md`.

---

## Stage 7 — Local LLM integration

**Goal:** generate a grounded diagnosis using only retrieved context.

- Use the runtime and model confirmed in Stage 0. Run fully local, no cloud API.
- Prompt template in `llm/prompts.py`: inputs are telemetry summary + retrieved chunks; output sections are **Likely fault**, **Why (evidence from readings and documents)**, **Recommended checks**, **Confidence/limitations**.
- Instruct the model to use only the provided context and to say when context is insufficient.
- Handle timeouts and "LLM not running" with a clear error message.
- Test the LLM alone first with a hardcoded example, then with real retrieval output.

**Done when:** a hardcoded symptom + retrieved context returns a correctly structured answer in an acceptable time on the user's machine.

---

## Stage 8 — End-to-end integration

**Goal:** one command runs the whole system.

- `main.py` subscribes to MQTT, runs detection, and only when a fault is detected calls retrieval + LLM (not on every message).
- Avoid spamming the LLM: cooldown or require symptoms to persist for N readings.
- Log each diagnosis (time, device, symptoms, retrieved sources, answer) to a file in `data/` so results can be shown later.
- Graceful handling when broker, LLM, or index is unavailable.

**Done when:** starting the simulator in any fault mode causes a diagnosis to print within a reasonable time, and normal mode stays quiet.

---

## Stage 9 — Interface (only if approved in Stage 0)

**Goal:** a minimal way to show the system working.

If answer was **CLI only:** polish terminal output (clear sections, readable formatting), and skip the rest of this stage.

If a **UI is approved**, agree on the smallest useful scope first (for example: live readings, current status, latest diagnosis with its sources). Ask the user before choosing the UI framework or how Python talks to it.

Design rules (non-negotiable):

- Minimalistic. Plenty of whitespace, restrained palette, one accent color at most.
- No glassmorphism, no gradients-everywhere, no generic "AI dashboard" look, no decorative emoji.
- Use the Impeccable design guidance for typography and buttons.
- Animation: Framer Motion for small transitions. Use three.js only if the user confirms the UI is meant to be visually heavy; do not add it by default.
- Keep dependencies minimal. No UI library unless approved.

**Done when:** user approves a screenshot or demo of the interface.

---

## Stage 10 — Testing and evaluation

**Goal:** show the system works, with numbers.

- Unit tests for parsing, detection, and retrieval.
- Evaluation script: run each fault mode multiple times, record detected fault vs. ground truth, and whether the top retrieved document and the LLM's stated fault are correct.
- Produce a results table in `docs/evaluation.md`, including failures and what caused them.
- Note limitations honestly (simulated data, small knowledge base, local model size).

**Done when:** `docs/evaluation.md` has real measured results from real runs.

---

## Stage 11 — Documentation and delivery

**Goal:** everything needed for submission, GitHub, resume, and viva.

- `README.md`: overview, architecture diagram, setup, how to run, demo steps, screenshots.
- Architecture diagram (simple, in Markdown/Mermaid).
- College deliverables as required by Stage 0 answers (report sections: abstract, objectives, methodology, architecture, modules, results, limitations, future scope; PPT outline).
- `docs/viva_prep.md`: likely questions with short answers (why MQTT, what a broker is, what RAG is and why it reduces hallucination, how detection works, why a local LLM, limitations).
- Resume bullets that describe **only what was actually built**.

**Done when:** a new person can clone the repo, follow the README, and reproduce the demo.

---

## Stage checklist

- [ ] Stage 0 — Clarify
- [ ] Stage 1 — Project baseline
- [ ] Stage 2 — MQTT pipeline
- [ ] Stage 3 — Simulator with fault modes
- [ ] Stage 4 — Fault detection
- [ ] Stage 5 — Knowledge base
- [ ] Stage 6 — RAG retrieval
- [ ] Stage 7 — Local LLM
- [ ] Stage 8 — Integration
- [ ] Stage 9 — Interface (if approved)
- [ ] Stage 10 — Testing and evaluation
- [ ] Stage 11 — Documentation
