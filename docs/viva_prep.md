# Viva & Interview Defense Guide — P_311

This document provides concise, technically rigorous questions and answers to prepare for college viva voce examinations, project defense panels, and technical interviews for **P_311: Knowledge-Driven IoT Fault Diagnosis Assistant**.

---

## 1. Core IoT & Networking Questions

### Q1: Why did you choose MQTT instead of HTTP/REST for sensor telemetry?
**Answer:**  
HTTP is an application-layer request-response protocol designed for web documents. It incurs high header overhead (hundreds of bytes per request), requires establishing a new TCP connection (or keeping heavy persistent connections open), and operates on a 1-to-1 client-server model.  
In contrast, **MQTT (Message Queuing Telemetry Transport)** is a lightweight binary pub/sub protocol specifically architected for constrained IoT networks. It features a minimal 2-byte fixed header, maintains a single persistent TCP connection via keepalives, and completely decouples data producers (sensors) from consumers (detectors and diagnostics) through a central broker.

### Q2: What is an MQTT Broker and what role does Mosquitto play?
**Answer:**  
An MQTT broker is the central hub of a publish/subscribe network. Publishers send messages to named hierarchical topics (e.g., `industrial/pump/centrifugal_01/telemetry`), and the broker filters and distributes these packets to all clients subscribed to those topics.  
In this project, **Eclipse Mosquitto** runs as a local Windows service on port 1883. It handles message routing with QoS 1 (at least once delivery), buffering, and client session management.

### Q3: What is QoS in MQTT and which level did you implement?
**Answer:**  
MQTT defines three Quality of Service (QoS) delivery guarantees:
- **QoS 0 (At most once):** "Fire and forget" with no acknowledgment.
- **QoS 1 (At least once):** Sender retries until broker sends a `PUBACK` acknowledgment packet. Used in our project (`qos=1`) to guarantee telemetry packets are not silently dropped.
- **QoS 2 (Exactly once):** Four-step handshake guaranteeing zero duplicates, but introduces noticeable network latency.

---

## 2. Fault Detection & Physics Questions

### Q4: Why did you choose rule-based statistical windows for fault detection instead of Machine Learning or Deep Learning?
**Answer:**  
In industrial machinery health monitoring, **explainability and determinism are paramount**. Machine learning models (e.g., autoencoders or LSTMs) operate as black boxes, require vast amounts of labeled historical failure data that plants rarely possess, and can fail unpredictably on out-of-distribution drifts.  
Our rule-based engine:
1. Is grounded in established international engineering standards: **ISO 10816-3 Class II** guidelines dictate that vibration velocity RMS exceeding 4.5 mm/s enters the dangerous Zone D.
2. Uses a short rolling window (3 samples) to compute moving averages and first derivatives, filtering out single-sample electrical noise spikes without lagging behind real physical failures.
3. Consumes negligible CPU cycles and provides an immediate, transparent audit trail for plant operators.

### Q5: How do you differentiate between actual machine failure and sensor malfunction?
**Answer:**  
We evaluate physical sensor characteristics:
- **Sensor Disconnect / Open-Circuit:** Instantaneously flags readings falling outside physical transducer validity boundaries (e.g., $-999^\circ\text{C}$ on an RTD where valid range is $-20^\circ\text{C}$ to $+150^\circ\text{C}$).
- **ADC Flatline / Freeze:** Real physical sensors continuously fluctuate due to thermal noise and mechanical jitter ($\sigma > 0$). If consecutive readings exhibit mathematical zero variance ($\Delta < 0.001$), the detector flags a frozen ADC channel while the underlying asset runs normally.

---

## 3. RAG (Retrieval-Augmented Generation) Questions

### Q6: What is RAG and why is it superior to fine-tuning an LLM for equipment diagnosis?
**Answer:**  
**Retrieval-Augmented Generation (RAG)** dynamically injects relevant domain documents into the LLM's prompt context at inference time.
Fine-tuning permanently modifies model weights, which is computationally expensive, prone to catastrophic forgetting, cannot be easily updated when manuals change, and still hallucinates when uncertain.  
RAG grounds the model in authoritative, verifiable facts: the LLM acts purely as a reasoning and synthesis engine over the retrieved text, eliminating hallucinations and providing transparent source citations (e.g., citing `KB01_bearing_inner_raceway_fatigue.md`).

### Q7: Why did you implement TF-IDF and Cosine Similarity instead of an external vector database like ChromaDB or Pinecone?
**Answer:**  
1. **Occam's Razor & Scale Appropriateness:** Our diagnostic corpus consists of 14 technical manuals (84 section chunks). Loading a heavy vector database (which pulls in SQLite, C++ bindings, and heavy dependencies) introduces unnecessary complexity and potential failure points.
2. **Deterministic Explainability:** Vector embeddings from neural models are dense floating-point arrays where individual dimensions cannot be explained to an examiner. In contrast, TF-IDF is mathematically transparent: the similarity score is a direct dot-product of term frequencies and inverse document frequencies.
3. **Sub-millisecond Latency:** Our in-memory vector index executes in under 2 milliseconds with zero external dependencies.

---

## 4. Local LLM & System Architecture Questions

### Q8: Why run a Local LLM (Ollama / llama3.2:3b) instead of cloud APIs like OpenAI GPT-4?
**Answer:**  
1. **Industrial Data Privacy & Air-Gapped Environments:** Industrial manufacturing plants and SCADA networks are strictly isolated from the public internet for cybersecurity and intellectual property protection. Telemetry cannot be streamed to external cloud servers.
2. **Zero Operating Cost:** Running a quantized 3B model locally incurs zero per-token API fees.
3. **Low Latency & High Availability:** Local models run reliably regardless of internet outages or external cloud API rate limits.

### Q9: How do you prevent Ground-Truth data leakage during evaluation?
**Answer:**  
In `PumpTelemetrySimulator`, the `ground_truth_fault` label is strictly excluded from standard MQTT JSON payloads. The detector, RAG retriever, and LLM have zero visibility into this label.  
Only when executing dedicated benchmark trials (`--test-mode`) does the harness capture the hidden ground truth to compare against the final diagnostic report, ensuring unbiased empirical evaluation.

### Q10: What are the primary technical limitations of your project?
**Answer:**  
1. **Simulated Telemetry:** Sensor traces are generated by a stateful mathematical model with Ornstein-Uhlenbeck drift. While physically grounded, they do not include unmodeled electrical noise or chemical fluid variations.
2. **Corpus Size:** The knowledge base has 14 manuals (84 chunks), whereas enterprise systems index thousands of plant maintenance records.
3. **Single Asset Focus:** Currently tailored to industrial centrifugal pumps with electric motor drives; expanding to compressors or turbines requires authoring additional knowledge manuals and configuring thresholds.
