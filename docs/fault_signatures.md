# Industrial Centrifugal Pump Fault Signatures — P_311

This document specifies the physical telemetry signatures, nominal baseline ranges, fault dynamics, and sample JSON payloads for the five operational modes implemented in `mqtt/sensor_simulator.py`.

---

## 1. Monitored Sensor Channels

The simulated asset is an **Industrial Centrifugal Slurry/Water Pump with an Electric Drive Motor**. Telemetry streams three physical parameters:

| Sensor | Physical Quantity | Engineering Unit | Nominal Steady-State Range | Anomaly Warning Threshold |
|---|---|---|---|---|
| **`temperature`** | Drive-End Bearing / Motor Stator Temp | °C (Celsius) | 45.0°C – 65.0°C | **> 75.0°C** |
| **`vibration`** | Radial Bearing Housing Velocity RMS | mm/s (ISO 10816-3) | 0.8 mm/s – 2.5 mm/s | **> 4.5 mm/s** (Zone D: Unacceptable) |
| **`pressure`** | Discharge Flange Hydraulic Pressure | bar | 4.0 bar – 6.0 bar | **< 3.0 bar** |

---

## 2. Operational & Fault Modes

### Mode 1: Normal Operation (`normal`)
- **Physical Mechanism:** Nominal pump operation under rated flow and head conditions. Lubricant film is intact, cooling is adequate, impeller is balanced.
- **Telemetry Behavior:** Values exhibit continuous, mean-reverting Ornstein-Uhlenbeck drift around healthy setpoints (~54°C, 1.4 mm/s, 5.0 bar) with small Gaussian noise.
- **Expected Anomaly Status:** None. All values stay comfortably within healthy limits.
- **Sample Payload:**
  ```json
  {
    "device_id": "pump_centrifugal_01",
    "timestamp": "2026-10-01T01:14:00.123456Z",
    "temperature": 54.12,
    "vibration": 1.38,
    "pressure": 5.04
  }
  ```

---

### Mode 2: Overheating (`overheating`)
- **Physical Mechanism:** Restricted ventilation/cooling fan blockage, prolonged electrical overload, or dry friction on bearing seals.
- **Telemetry Behavior:** Temperature climbs progressively (+1.2°C to +2.2°C per reading) until stabilizing in the severe thermal hazard zone (80.0°C – 86.0°C). Vibration and discharge pressure remain within nominal boundaries.
- **Expected Anomaly Status:** `temperature > 75.0°C` trigger.
- **Sample Payload:**
  ```json
  {
    "device_id": "pump_centrifugal_01",
    "timestamp": "2026-10-01T01:14:15.123456Z",
    "temperature": 82.45,
    "vibration": 1.42,
    "pressure": 4.96
  }
  ```

---

### Mode 3: Bearing Wear (`bearing_wear`)
- **Physical Mechanism:** Fatigue spalling on bearing raceways, cage degradation, or loss of lubrication. High mechanical shock creates severe radial vibration.
- **Telemetry Behavior:** Vibration velocity RMS spikes sharply (+0.4 to +0.8 mm/s per reading) past the ISO 10816 Zone D boundary (4.5 mm/s), peaking at 5.8 to 7.2 mm/s. Frictional dissipation causes a secondary moderate rise in temperature (~66°C to 70°C). Hydraulic pressure remains normal.
- **Expected Anomaly Status:** `vibration > 4.5 mm/s` trigger, accompanied by secondary thermal rise.
- **Sample Payload:**
  ```json
  {
    "device_id": "pump_centrifugal_01",
    "timestamp": "2026-10-01T01:14:30.123456Z",
    "temperature": 67.80,
    "vibration": 6.34,
    "pressure": 5.01
  }
  ```

---

### Mode 4: Pressure Drop (`pressure_drop`)
- **Physical Mechanism:** Discharge piping leakage, ruptured discharge flange gasket, or severe impeller cavitation causing loss of hydraulic head.
- **Telemetry Behavior:** Discharge pressure drops rapidly (-0.35 to -0.6 bar per reading), falling well below the critical minimum of 3.0 bar down to 1.6 – 2.4 bar. Collapsing cavitation vapor bubbles introduce turbulent mechanical jitter to vibration (+0.3 to +0.6 mm/s). Temperature remains normal.
- **Expected Anomaly Status:** `pressure < 3.0 bar` trigger with elevated vibration jitter.
- **Sample Payload:**
  ```json
  {
    "device_id": "pump_centrifugal_01",
    "timestamp": "2026-10-01T01:14:45.123456Z",
    "temperature": 53.90,
    "vibration": 2.15,
    "pressure": 2.18
  }
  ```

---

### Mode 5: Sensor Malfunction (`sensor_failure`)
- **Physical Mechanism:** Sensor hardware fault, broken wire harness, ADC freeze, or telemetry conditioning board failure while the pump continues running normally.
- **Sub-types:**
  1. **Flat-line (`--sensor-failure-type flatline`):** Temperature sensor output freezes to an exact static float value with 0.00 standard deviation over consecutive samples.
  2. **Disconnect (`--sensor-failure-type disconnect`):** Temperature reading outputs an out-of-range flag value `-999.0` representing an open circuit / disconnected wire.
- **Expected Anomaly Status:** Sensor zero-variance flag or out-of-valid-range exception (`temp < -20°C` or `temp > 150°C`).
- **Sample Payload (Flat-line):**
  ```json
  {
    "device_id": "pump_centrifugal_01",
    "timestamp": "2026-10-01T01:15:00.123456Z",
    "temperature": 54.00,
    "vibration": 1.45,
    "pressure": 4.98
  }
  ```
- **Sample Payload (Disconnect):**
  ```json
  {
    "device_id": "pump_centrifugal_01",
    "timestamp": "2026-10-01T01:15:05.123456Z",
    "temperature": -999.0,
    "vibration": 1.41,
    "pressure": 5.02
  }
  ```

---

## 3. Evaluation Isolation: Ground-Truth Labeling

In standard operational mode (`python mqtt/sensor_simulator.py --mode <mode>`), the MQTT payload strictly contains only:
`device_id`, `timestamp`, `temperature`, `vibration`, `pressure`.

To satisfy Constraint 5 and Constraint 6 (prevention of ground-truth leakage), the `ground_truth_fault` field is **never** included in standard operation.

Only when the simulator is executed with `--test-mode` (used by Stage 10 evaluation scripts) does it append:
```json
"ground_truth_fault": "bearing_wear"
```
This enables automated scoring of diagnostic accuracy without giving the fault detector, RAG retriever, or LLM access to the answer.
