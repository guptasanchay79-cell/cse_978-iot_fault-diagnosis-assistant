# Professional Resume Bullet Points — P_311

These bullet points are crafted for software engineering, embedded systems, IoT, and AI/ML roles. In strict accordance with **Project Constraint 5 and Constraint 8**, they describe **only** what was genuinely engineered, tested, and benchmarked.

---

### Option A: AI / GenAI / LLM & RAG Focus
- **Knowledge-Driven IoT Fault Diagnosis Assistant (Python, MQTT, Ollama, RAG):**
  - Architected an air-gapped, edge-deployable condition monitoring assistant that streams industrial pump telemetry over MQTT (Mosquitto) and executes offline semantic fault diagnosis with zero cloud dependencies.
  - Implemented an in-memory Vector Space Information Retrieval engine (TF-IDF + Cosine Similarity) over 14 standardized industrial maintenance manuals (84 section chunks), achieving **100% Top-3 retrieval recall** in **< 2ms** latency.
  - Formulated a grounded diagnostic prompting pipeline interfacing with a local quantized LLM (Ollama `llama3.2:3b`), enforcing strict 4-section structured outputs (Likely Fault, Evidence, Recommended Checks, Limitations) with zero hallucination.
  - Conducted 30 automated evaluation trials across 5 operating modes, validating **100% detection accuracy**, **0% false positive rate**, and a **1.000 macro-average F1-score**.

---

### Option B: Backend / Systems Engineering Focus
- **Edge IoT Anomaly Detection & Diagnostic Engine (Python, Mosquitto, Paho-MQTT, RAG):**
  - Engineered a high-throughput, resilient IoT telemetry pipeline in Python using `paho-mqtt` 2.x API to ingest real-time centrifugal pump telemetry (temperature, vibration velocity RMS, discharge pressure) at QoS 1.
  - Built an explainable anomaly extraction engine utilizing statistical rolling windows ($N=3$) and ISO 10816-3 industrial vibration limits, successfully eliminating transient noise spikes while detecting bearing fatigue, overheating, and pressure collapse.
  - Designed an automatic index caching mechanism using aggregate SHA-256 hash invalidation for rapid cold-start loading of technical documentation.
  - Authored a comprehensive automated test suite (30 unit and integration tests) achieving 100% test pass rate across schema validation, broker resilience, and end-to-end telemetry pipelines.

---

### Option C: Industrial IoT / Embedded Systems Focus
- **Air-Gapped Industrial Machinery Health Monitor (IoT, MQTT, Python, Edge AI):**
  - Developed a physics-grounded telemetry simulator utilizing mean-reverting Ornstein-Uhlenbeck drift and Gaussian noise to model nominal pump dynamics and progressive mechanical/hydraulic failure modes.
  - Created a dual-signature sensor health monitor capable of distinguishing between actual machine degradation and transducer malfunctions (open-circuit -999°C flags vs. frozen ADC flatlines with zero variance).
  - Integrated diagnostic outputs with persistent append-only structured logging (`.jsonl`) to produce auditable maintenance records for industrial plant operators.
