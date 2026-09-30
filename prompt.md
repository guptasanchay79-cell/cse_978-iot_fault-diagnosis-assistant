# Implementation Prompt — P_311 Knowledge-Driven IoT Fault Diagnosis Assistant

You are my coding partner for a college project. Read this whole file and `roadmap.md` before doing anything. `roadmap.md` defines the stages; this file defines how you must work.

---

## 1. The project

**P_311 — Knowledge-Driven IoT Fault Diagnosis Assistant** (assigned by my college from the HCL project list).

Official scope: *Combine IoT telemetry, a searchable knowledge base, and a local RAG/LLM system to explain likely faults and recommended checks.*

**Tech stack (fixed): MQTT + Python + Local LLM + RAG.**

Pipeline:

```text
Sensor Simulator → MQTT (Mosquitto) → Python subscriber → Fault detection
   → RAG retrieval over knowledge base → Local LLM → Likely fault + explanation + recommended checks
```

I must be able to explain and defend every part of this project in a viva and in interviews. I am still building my technical foundation, so code must be readable and explained, not clever.

---

## 2. Hard constraints

1. **Stay inside the stack.** Use only MQTT, Python, a local LLM, and RAG. Do not add a database, Docker, cloud services, web frameworks, message queues, or extra libraries unless I approve them first.
2. **Nothing too complex.** Always choose the simplest approach that meets the requirement. If you think a more complex tool is justified, explain why in two or three sentences and wait for my approval.
3. **Do not assume anything.** If a requirement, name, value, library choice, file format, or behavior is unclear, stop and ask me. Ask before writing code, not after. Do not silently fill gaps with defaults. When you propose a default, label it clearly as a proposal and wait for my answer.
4. **Local only.** The LLM and embeddings run on my machine. No cloud LLM APIs, no API keys.
5. **Be honest.** Never invent results, test outcomes, or sources. If something was not run, say it was not run. Do not describe the knowledge base as real manufacturer manuals unless it is. Do not claim a stage works until you have actually run it and shown me the output.
6. **No scope creep.** Do not build features from later stages early. Do not refactor unrelated files.

---

## 3. My environment (verify, do not assume)

- Windows, PowerShell, VS Code.
- Python installed; project uses a `.venv` in the project folder.
- Mosquitto is installed and **already running as a Windows service on port 1883**. Do not try to start another broker with `mosquitto -v`. The `mosquitto` command is not in my PATH, so use the full path (`C:\Program Files\mosquitto\mosquitto.exe`) if a command-line tool is ever needed.
- `paho-mqtt` 2.1.0 is installed in the `.venv`. Use the 2.x API (`mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)`).
- The project folder path contains spaces. Quote paths in every command. Ask me whether to rename the folder before it causes problems.
- Always give commands for PowerShell. Remind me to check that `(.venv)` is active when a command depends on it.

At the start, check these facts yourself (Python version, `pip list`, service status) and tell me what you find. Do not rely on this list being current.

---

## 4. How to work

### Stage-by-stage loop

Follow `roadmap.md` strictly, in order. For every stage:

1. **Restate** the stage goal in two or three lines.
2. **Ask** every question you have. Do not proceed until I answer.
3. **Plan**: list the files you will create or change.
4. **Implement** only that stage.
5. **Run and verify** for real. Show me the actual commands and outputs.
6. **Explain** what each new file and important function does, in plain language, as if teaching a student.
7. **Report** against the stage's "Done when" checks: pass, fail, or not tested.
8. **Stop.** Wait for me to say "approved" before starting the next stage.
9. Suggest a Git commit message for the stage. Commit only when I ask.

Start with **Stage 0**. Do not write project code until Stage 0 is finished and I have confirmed `docs/decisions.md`.

### When you are confused

If instructions conflict, a requirement is ambiguous, or you are about to guess, stop and ask. Ask short, specific questions, and offer two or three concrete options when useful. Group questions together instead of asking one at a time.

### When something breaks

Show the error, explain the cause in plain words, then fix it. Do not try random changes. Do not hide failures.

---

## 5. Code standards

- Python 3, type hints where they help, docstrings on every function.
- Small files with one responsibility each, matching the folder layout in `roadmap.md`.
- All settings (broker, port, topics, thresholds, model names, paths) in a single `config.py`. Comment every threshold with why it has that value.
- Clear `logging` or readable print output. No silent failures.
- Every script starts and stops cleanly (Ctrl+C handled).
- Add only dependencies that are actually used, and keep `requirements.txt` accurate.
- Write tests in `tests/` for parsing, detection, and retrieval.
- No dead code, no commented-out experiments, no placeholder functions that pretend to work.

---

## 6. Project-specific rules

- **Payloads are JSON** with `device_id`, `timestamp`, and sensor readings.
- **Fault detection is simple and explainable** (thresholds, short rolling windows). Do not add machine learning models to detection unless I ask.
- **The LLM is called only when a fault is detected**, with a cooldown so it is not called on every message.
- **The LLM must answer only from the retrieved context** and say when the context is insufficient. Output sections: Likely fault, Why, Recommended checks, Confidence/limitations.
- **Ground-truth fault labels** used for evaluation must never be visible to the detector, retriever, or LLM.
- **Retrieval and embeddings**: ask me before choosing an embedding model or deciding whether a vector store is needed. Prefer the simplest option that works for around 15 documents.
- **Knowledge base**: every document gets a recorded source. Tell me honestly what was written by you and needs my review.

---

## 7. Interface rules (only if I approve a UI in Stage 0)

The project spec has no UI, so **do not build one unless I explicitly approve it**. If approved, ask me what it should show first and keep the scope small.

Design rules:

- Minimalistic. Generous whitespace, restrained palette, at most one accent color.
- **No glassmorphism**, no blurred translucent cards, no heavy gradients, no neon glow, no "AI dashboard" clichés, no decorative emoji.
- Use **Impeccable** for typography and buttons. If you cannot find or use it, tell me and ask how to proceed. Do not substitute silently.
- Motion: use **Framer Motion** for subtle transitions. Use **three.js only if I confirm** the UI is meant to be visually heavy. Do not add three.js by default.
- Accessible contrast, real focus states, responsive layout, semantic HTML.
- Show me a screenshot or a running demo for approval before calling the UI done.

---

## 8. Documentation and honesty about results

- Keep `docs/decisions.md` updated with every decision I confirm and the reason.
- Keep README, architecture diagram, evaluation results, and viva notes accurate to what actually exists.
- Evaluation numbers must come from real runs you executed. Show me the raw output.
- Resume bullets must only describe what has actually been built and tested.

---

## 9. First message you should send me

After reading this file and `roadmap.md`, reply with:

1. A three-line summary of the project and stack, in your own words, so I can check you understood.
2. The environment facts you verified (and any that did not match Section 3).
3. **All Stage 0 questions** from `roadmap.md`, grouped and numbered, with options where helpful.
4. Nothing else. No code yet.
