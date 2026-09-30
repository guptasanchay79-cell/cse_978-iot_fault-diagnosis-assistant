# Technical Diagnosis Manual: Motor Stator Winding Overheating & Cooling Breakdown

**Document ID:** KB-PUMP-003  
**Target Asset:** Industrial Centrifugal Pump AC Induction Drive Motor  
**Subsystem:** Motor Stator Windings & Forced Air Cooling System  
**Severity Level:** Critical (Risk of Insulation Breakdown & Electrical Fire)

---

## 1. Diagnostic Symptoms & Sensor Telemetry Profile
- **Stator / Motor Temperature:** Ramps rapidly past **75.0°C**, reaching **80.0°C – 86.0°C+** (Exceeds NEMA Class B rise limits).
- **Thermal Rate of Climb:** High thermal derivative exceeding **+1.2°C per minute** under steady load.
- **Vibration Velocity RMS:** Remains within nominal range (**1.0 – 2.0 mm/s**); mechanical baseline is healthy.
- **Discharge Pressure:** Normal hydraulic output (**4.8 – 5.4 bar**). Flow rate is normal or slightly elevated.

---

## 2. Physical Root Causes
1. **Cooling Air Shroud Blockage:** External fan cowling clogged with airborne fibrous lint, dirt cakes, or coal dust.
2. **Broken or Missing Fan Blades:** Damaged external motor cooling fan impinging zero convective air across stator cooling fins.
3. **Electrical Overload:** Operating the pump continuously to the far right of the head-flow curve (runout condition), pulling excessive motor amperage.
4. **Restricted Ambient Ventilation:** High ambient room temperature (> 45°C) or enclosed pump skid with inadequate exhaust venting.

---

## 3. Immediate Diagnostic Verification Checks
1. **Airflow Verification:** Place hand safely near motor cooling cowling to feel if cooling fan is exhausting air across cooling fins.
2. **Thermal Imaging / IR Camera:** Scan motor frame for localized hot spots vs. uniform stator heating.
3. **Current Draw Measurement:** Measure 3-phase AC motor current with a clamp meter; compare with motor nameplate Full Load Amps (FLA).
4. **Finned Frame Cleanliness:** Inspect longitudinal cast iron cooling fins for heavy oil/dust blanket insulative buildup.

---

## 4. Recommended Corrective Maintenance Actions
1. **Throttle Discharge Valve:** If motor current exceeds nameplate FLA, throttle discharge valve slightly towards BEP (Best Efficiency Point) to reduce motor load.
2. **Clean Air Cowling:** Blow down cooling fan intake shroud and stator cooling fins with dry compressed air (< 30 psi).
3. **Inspect Cooling Fan:** Check plastic/aluminum motor fan for broken vanes, sheared key, or spinning loose on motor shaft.
4. **Megger Test (Insulation Resistance):** Following shutdown, perform a 1000V DC insulation resistance test on motor windings; verify > 10 Megohms.

---

## 5. Safety Warnings & LOTO Notes
- **DANGER:** High temperature hazard! Motor frame surfaces above 70°C will cause severe burns. Wear thermal protective gloves.
- **LOTO:** Lock out electrical feeder breaker at the Motor Control Center (MCC) before cleaning fan cowlings.
