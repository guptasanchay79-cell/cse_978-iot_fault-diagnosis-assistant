# RAG Retrieval Benchmark Results — P_311

This document records the empirical retrieval evaluation metrics across all five simulated industrial pump fault modes using the section-aware TF-IDF Vector Space Retriever implemented in `rag/retriever.py`.

---

## 1. Corpus Configuration

- **Total Documents:** 14 technical diagnostic manuals in `knowledge_base/`
- **Total Chunks:** 84 semantic section chunks
- **Vocabulary Size:** 1,550 unique terms
- **Chunking Method:** Markdown Level-2 Section Header Splitting (`## `)
- **Scoring Function:** Sub-linear TF-IDF ($\text{TF} = 1 + \ln(\text{count})$, $\text{IDF} = \ln(1 + N/\text{DF}) + 1$) + Cosine Similarity
- **Top-K Parameter:** 3

---

## 2. Empirical Benchmark Runs (Measured Output)

### Query 1: Overheating Mode
- **Symptom Query:**  
  `"Industrial centrifugal pump pump_centrifugal_01 exhibits severe motor stator / bearing overheating at 82.50 C exceeding thermal safety threshold of 75.0 C, and rapid thermal climb rate. Current telemetry shows temperature 82.50 C."`
- **Target Document(s):** `KB03_motor_winding_overheating.md` / `KB04_bearing_housing_thermal_runaway.md`
- **Hit Rate @ Top 3:** **PASS (Rank 1)**

| Rank | Score | Source Document | Matched Section |
|---|---|---|---|
| **#1** | **0.2508** | `KB03_motor_winding_overheating.md` | Diagnostic Symptoms & Sensor Telemetry Profile |
| **#2** | 0.1657 | `KB05_discharge_pipe_rupture_leakage.md` | Diagnostic Symptoms & Sensor Telemetry Profile |
| **#3** | 0.1641 | `KB03_motor_winding_overheating.md` | Safety Warnings & LOTO Notes |

---

### Query 2: Bearing Wear Mode
- **Symptom Query:**  
  `"Industrial centrifugal pump pump_centrifugal_01 exhibits critical bearing vibration velocity RMS of 6.24 mm/s exceeding ISO 10816 Zone D danger limit of 4.5 mm/s, and secondary frictional temperature rise of 67.80 C. Current telemetry shows vibration 6.24 mm/s."`
- **Target Document(s):** `KB01_bearing_inner_raceway_fatigue.md` / `KB02_bearing_lubrication_starvation.md`
- **Hit Rate @ Top 3:** **PASS (Rank 1 & Rank 3)**

| Rank | Score | Source Document | Matched Section |
|---|---|---|---|
| **#1** | **0.2919** | `KB01_bearing_inner_raceway_fatigue.md` | Diagnostic Symptoms & Sensor Telemetry Profile |
| **#2** | 0.2538 | `KB04_bearing_housing_thermal_runaway.md` | Diagnostic Symptoms & Sensor Telemetry Profile |
| **#3** | **0.1484** | `KB02_bearing_lubrication_starvation.md` | Diagnostic Symptoms & Sensor Telemetry Profile |

---

### Query 3: Pressure Drop / Cavitation Mode
- **Symptom Query:**  
  `"Industrial centrifugal pump pump_centrifugal_01 exhibits critical hydraulic discharge pressure drop to 2.10 bar falling below low operational limit of 3.0 bar, and hydraulic cavitation turbulence with vibration fluctuations. Discharge pressure is 2.10 bar."`
- **Target Document(s):** `KB05_discharge_pipe_rupture_leakage.md` / `KB06_impeller_cavitation_hydraulic_loss.md`
- **Hit Rate @ Top 3:** **PASS (Rank 1 & Rank 2)**

| Rank | Score | Source Document | Matched Section |
|---|---|---|---|
| **#1** | **0.2260** | `KB05_discharge_pipe_rupture_leakage.md` | Diagnostic Symptoms & Sensor Telemetry Profile |
| **#2** | **0.1827** | `KB06_impeller_cavitation_hydraulic_loss.md` | Diagnostic Symptoms & Sensor Telemetry Profile |
| **#3** | 0.1381 | `KB12_suction_strainer_clogging.md` | Diagnostic Symptoms & Sensor Telemetry Profile |

---

### Query 4: Sensor Flatline Mode
- **Symptom Query:**  
  `"Industrial centrifugal pump pump_centrifugal_01 exhibits temperature sensor flat-line detected: value frozen at 54.00 C with 0.00 variance across consecutive readings."`
- **Target Document(s):** `KB08_adc_telemetry_sensor_flatline.md`
- **Hit Rate @ Top 3:** **PASS (Rank 1)**

| Rank | Score | Source Document | Matched Section |
|---|---|---|---|
| **#1** | **0.3112** | `KB08_adc_telemetry_sensor_flatline.md` | Diagnostic Symptoms & Sensor Telemetry Profile |
| **#2** | 0.1558 | `KB08_adc_telemetry_sensor_flatline.md` | Overview & Metadata |
| **#3** | 0.1189 | `KB08_adc_telemetry_sensor_flatline.md` | Safety Warnings & LOTO Notes |

---

### Query 5: Sensor Disconnect Mode
- **Symptom Query:**  
  `"Industrial centrifugal pump pump_centrifugal_01 telemetry sensor failure: temperature sensor reading (-999.0 C) is outside physical valid range (sensor disconnect / open-circuit)."`
- **Target Document(s):** `KB07_rtd_temperature_sensor_disconnect.md`
- **Hit Rate @ Top 3:** **PASS (Rank 1)**

| Rank | Score | Source Document | Matched Section |
|---|---|---|---|
| **#1** | **0.3719** | `KB07_rtd_temperature_sensor_disconnect.md` | Diagnostic Symptoms & Sensor Telemetry Profile |
| **#2** | 0.3136 | `KB07_rtd_temperature_sensor_disconnect.md` | Overview & Metadata |
| **#3** | 0.2115 | `KB07_rtd_temperature_sensor_disconnect.md` | Physical Root Causes |

---

## 3. Summary Performance Metrics

- **Total Test Queries:** 5
- **Top-1 Accuracy:** **5 / 5 (100.0%)**
- **Top-3 Accuracy:** **5 / 5 (100.0%)**
- **Average Retrieval Latency (Cached):** **1.8 milliseconds**
- **Average Retrieval Latency (Cold Build):** **84.5 milliseconds**
- **False Document Intrusion Rate in Top-1:** **0.0%**
