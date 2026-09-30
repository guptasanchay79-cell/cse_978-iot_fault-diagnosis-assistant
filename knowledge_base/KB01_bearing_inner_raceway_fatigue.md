# Technical Diagnosis Manual: Bearing Inner Raceway Fatigue & Spalling

**Document ID:** KB-PUMP-001  
**Target Asset:** Industrial Centrifugal Slurry / Water Pump  
**Subsystem:** Drive-End / Non-Drive-End Rolling Element Bearings  
**Severity Level:** High (Impending Catastrophic Seizure)

---

## 1. Diagnostic Symptoms & Sensor Telemetry Profile
- **Vibration Velocity RMS:** Spikes sharply above **4.5 mm/s**, frequently exceeding **6.0 mm/s** (ISO 10816-3 Zone D: Unsatisfactory / Dangerous).
- **Vibration Frequency Characteristics:** Dominant high-frequency harmonics at Ball Pass Frequency Inner Ring (BPFI) with sidebands at rotational shaft speed (1X).
- **Bearing Housing Temperature:** Exhibits secondary frictional rise climbing to **65.0°C – 72.0°C** due to micro-roughness friction.
- **Discharge Pressure:** Normal steady-state operation (**4.0 – 6.0 bar**). Hydraulic performance remains unaffected initially.

---

## 2. Physical Root Causes
1. **Subsurface Material Fatigue:** Extended cyclic stress exceeding the L10 bearing fatigue life.
2. **Micro-Spalling & Pitting:** Metal flakes peeling away from the rotating inner raceway contact track.
3. **Contaminant Ingress:** Solid particulate contamination bridging the thin oil lubrication film.
4. **Improper Mounting:** Excessive drive-up force or shaft thermal expansion causing excessive radial preload.

---

## 3. Immediate Diagnostic Verification Checks
1. **FFT Spectrum Analysis:** Inspect accelerometer spectrum for distinct inner raceway defect frequency (BPFI = $Z/2 \times [1 + (d/D)\cos\beta] \times f_r$).
2. **Acoustic / Shock Pulse Monitoring:** Perform shock pulse or peakvue measurements; look for high decibel crest factor peaks.
3. **Stethoscope / Ultrasound Inspection:** Check bearing housing for harsh grinding or irregular clicking sounds.
4. **Oil Sampling:** Inspect bearing grease or oil bath for metallic particulate swarf or bronze flecks.

---

## 4. Recommended Corrective Maintenance Actions
1. **Controlled Machine Shutdown:** Plan a controlled hot-standby pump transfer and stop the unit within 4 to 8 hours to avoid cage fragmentation.
2. **Bearing Replacement:** Dismount the damaged bearing assembly. Replace with new matched-clearance C3 precision bearing.
3. **Shaft & Housing Inspection:** Measure shaft journal runout and housing bore concentricity using a dial gauge before installing new bearings.
4. **Lubricant Flush:** Completely flush the bearing cavity with clean mineral oil and repack with high-temperature synthetic polyurea grease.

---

## 5. Safety Warnings & LOTO Notes
- **WARNING:** Do not run bearing when vibration exceeds 7.0 mm/s. Catastrophic cage breakup can shear the pump shaft or lock the motor.
- **LOTO:** Follow standard Lockout/Tagout protocol. De-energize 415V/480V motor breaker and dissipate hydraulic line pressure before touching housing.
