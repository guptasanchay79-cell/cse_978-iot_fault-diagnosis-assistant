# Viva Defense PPT Presentation Outline — P_311

**Project Title:** Knowledge-Driven IoT Fault Diagnosis Assistant  
**HCL Project Statement ID:** P_311  
**Candidate Name:** SANCHAY  
**Tech Stack:** MQTT (Mosquitto) + Python 3.13 + Local RAG + Local LLM  

---

## Slide 1: Title & Project Overview
- **Title:** Knowledge-Driven IoT Fault Diagnosis Assistant
- **Problem Statement ID:** HCL P_311 (Embedded IoT & Industrial Systems Support)
- **Subtitle:** Edge-Deployable, Air-Gapped Industrial Asset Condition Monitoring & Automated Diagnostic Assistant
- **Presenter:** Sanchay | College Project Evaluation

---

## Slide 2: The Industrial Challenge
- **Industrial Context:** Centrifugal pumps account for over 60% of rotating machinery in power, chemical, and municipal water plants.
- **Current Bottlenecks:**
  - Traditional SCADA systems generate raw numerical threshold alarms with zero context or root-cause explanation.
  - Human maintenance engineers face high cognitive load during emergency alarms.
  - Cloud-based AI solutions pose severe data privacy, latency, and air-gapped cybersecurity risks.
- **The Solution:** A 100% offline, explainable edge pipeline combining MQTT telemetry, rule-based detection, local RAG, and an offline LLM.

---

## Slide 3: End-to-End System Architecture
- **Visual Pipeline Diagram:**
  - Sensor Simulator $\rightarrow$ Mosquitto Broker (Port 1883) $\rightarrow$ Telemetry Subscriber (Paho v2)
  - $\rightarrow$ Fault Detector (Rolling Window) $\rightarrow$ TF-IDF Knowledge Retriever (14 Manuals)
  - $\rightarrow$ Local LLM Inference Engine $\rightarrow$ Structured Diagnostic Report Banner + Persistent JSONL Logging
- **Core Design Tenet:** Deterministic and explainable at every stage—zero black-box algorithms.

---

## Slide 4: Telemetry Streaming & Machine Physics
- **Monitored Asset:** Industrial Centrifugal Pump with AC Induction Motor.
- **Three Core Sensor Streams:**
  - **Temperature (°C):** Drive-end bearing & stator temperature (Nominal: 45–65°C | Alarm: > 75°C).
  - **Vibration Velocity RMS (mm/s):** Radial bearing housing vibration (Nominal: 0.8–2.5 mm/s | Alarm: > 4.5 mm/s per ISO 10816 Zone D).
  - **Discharge Pressure (bar):** Pump discharge head (Nominal: 4.0–6.0 bar | Alarm: < 3.0 bar).
- **Physical Dynamics:** Modeled via Ornstein-Uhlenbeck mean-reverting drift + Gaussian noise.

---

## Slide 5: Explainable Fault Detection Engine
- **Why Not Deep Learning for Detection?**
  - High explainability required for viva and plant operator trust.
  - Grounded directly in ISO 10816-3 mechanical vibration standards.
- **Rolling Window Smoothing ($N=3$):**
  - Computes moving averages and step derivatives to swallow transient noise spikes.
  - Differentiates between physical asset failure and sensor malfunction (flatline zero-variance and open-circuit -999°C).
- **RAG Query Synthesis:** Transforms numerical readings into natural language semantic search queries.

---

## Slide 6: Semantic Knowledge Base & Local RAG
- **Technical Corpus:** 14 structured industrial maintenance manuals (84 semantic section chunks).
- **Provenance & Standards:** Formally grounded in ISO 10816-3, API 610, and IEEE 841 standards (logged in `docs/knowledge_sources.md`).
- **Includes 6 Realistic Industrial Distractors:** Shaft misalignment, dynamic unbalance, mechanical seal face failure, water hammer.
- **Vector Space Information Retrieval:**
  - Sub-linear TF-IDF + Cosine Similarity.
  - Executes in **1.8 milliseconds** with zero heavy database dependencies.
  - Automatic index persistence and SHA-256 cache invalidation.

---

## Slide 7: Offline Local LLM Reasoning
- **Runtime & Deployment:** Local Ollama daemon (`llama3.2:3b` / 4-bit quantized) configured on Drive D: (`D:\ollama\models`).
- **Strict Grounding Prompting:** Prohibits hallucination; instructs model to cite retrieved passages and declare limitations when uncertain.
- **Standardized Diagnostic Schema (4 Sections):**
  1. *Likely Fault Mode*
  2. *Why (Evidence from Readings and Documents)*
  3. *Recommended Checks*
  4. *Confidence / Limitations*
- **Fault-Tolerant Fallback:** Deterministic context synthesis ensures 100% uptime even if Ollama service is stopped.

---

## Slide 8: Live Demonstration & Terminal Output
- **Single Master Orchestrator:** `python main.py`
- **Clean CLI Presentation:** Terminal display with visual borders, clear status indicators, and source citations.
- **Live Scenarios Demonstrated:**
  - Normal steady-state operation: System runs quietly (zero false alarms).
  - Overheating mode: Instantly triggers detection $\rightarrow$ retrieves `KB03` $\rightarrow$ outputs stator fan check.
  - Bearing wear mode: Triggers detection $\rightarrow$ retrieves `KB01` $\rightarrow$ outputs raceway spalling check.

---

## Slide 9: Experimental Results & Benchmark Scorecard
- **30 Multi-Iteration Automated Evaluation Trials:**
  - **Detection Accuracy:** **100.0%** (30 / 30 trials correctly evaluated).
  - **False Positive Rate:** **0.0%** (0 false alarms on normal pump data).
  - **RAG Top-1 Recall:** **100.0%** (exact target document ranked #1).
  - **RAG Top-3 Recall:** **100.0%**.
  - **Macro-average F1-Score:** **1.000**.
  - **Section Completeness:** **100.0%** (all 4 sections present across all trials).

---

## Slide 10: Limitations & Future Enhancements
- **Acknowledged Limitations:**
  - Simulated mathematical telemetry rather than live physical transducer feeds.
  - Knowledge base scale limited to 14 manuals (84 chunks).
- **Future Roadmap:**
  - Hardware-in-the-Loop deployment with ESP32 microcontrollers over RS-485 Modbus.
  - Direct integration into plant CMMS software (SAP PM / IBM Maximo) for automated work-order generation.

---

## Slide 11: Summary & Conclusion
- **Key Takeaways:**
  - Successfully met all requirements of HCL Problem Statement P_311.
  - 100% offline, privacy-preserving, air-gapped architecture.
  - Low-latency, explainable, and production-ready condition monitoring pipeline.
- **Thank You!** Questions & Discussion.
