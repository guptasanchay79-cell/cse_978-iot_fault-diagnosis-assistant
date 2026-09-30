# Technical Diagnosis Manual: Bearing Lubrication Starvation & Grease Degradation

**Document ID:** KB-PUMP-002  
**Target Asset:** Industrial Centrifugal Slurry / Water Pump  
**Subsystem:** Bearing Lubrication System  
**Severity Level:** High (Rapid Accelerated Wear)

---

## 1. Diagnostic Symptoms & Sensor Telemetry Profile
- **Bearing Housing Temperature:** Rapid upward climb from nominal (52°C) towards **70.0°C – 78.0°C**, triggering thermal warnings.
- **Vibration Velocity RMS:** High-frequency broadband "carpet" vibration rising from 1.2 mm/s up to **4.8 – 6.5 mm/s**.
- **Vibration Pattern:** High crest factor, non-synchronous broadband friction noise rather than clean defect frequency peaks.
- **Discharge Pressure:** Normal hydraulic output (**4.5 – 5.5 bar**).

---

## 2. Physical Root Causes
1. **Grease Depletion / Starvation:** Insufficient regreasing interval or collapsed grease path.
2. **Thermal Grease Oxidation / Cake Formation:** Base oil bleeding away leaving dry, hard soap thickener residue.
3. **Moisture Emulsification:** Water ingress past defective lip seals washing away lubricant film.
4. **Grease Incompatibility:** Mixing incompatible grease thickeners (e.g., lithium complex mixed with polyurea), causing liquefaction.

---

## 3. Immediate Diagnostic Verification Checks
1. **Purge Port Inspection:** Open bearing housing grease relief valve; inspect color and consistency of purged grease (black/burned indicates thermal degradation).
2. **Housing Contact Thermography:** Measure temperature differential between bearing cap and motor frame using an infrared thermometer.
3. **Ultrasonic Lubrication Tooling:** Listen to acoustic friction levels using ultrasound; dry metal-to-metal boundary friction produces continuous rushing noise.
4. **Seal Integrity Inspection:** Inspect labyrinth/lip seals for grease leaking onto the baseplate.

---

## 4. Recommended Corrective Maintenance Actions
1. **Regrease While Running:** Inject manufacturer-specified grease slowly using a calibrated manual grease gun while the pump runs, monitoring ultrasound until acoustic decibels drop.
2. **Housing Relief Cleanout:** Ensure the grease relief drain plug is clear to prevent over-pressurization and grease packing against seals.
3. **Oil Quality Analysis:** If oil-bath lubricated, sample oil for viscosity degradation, acid number (TAN), and water content (> 200 ppm requires change).
4. **Seal Replacement:** Replace hardened elastomer lip seals during next planned outage.

---

## 5. Safety Warnings & LOTO Notes
- **CAUTION:** Over-greasing can be as destructive as under-greasing. Packing the bearing cavity 100% full will cause churning overheating (> 85°C).
- **LOTO:** Do not insert fingers into bearing housing inspection ports while machinery is rotating.
