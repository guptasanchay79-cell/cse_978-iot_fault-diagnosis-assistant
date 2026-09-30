# Technical Diagnosis Manual: Motor Electrical Phase Imbalance & Stator Hum

**Document ID:** KB-PUMP-013  
**Target Asset:** Industrial 3-Phase AC Induction Drive Motor  
**Subsystem:** Motor Power Supply & Stator Windings  
**Severity Level:** High (Rapid Exponential Stator Heating)

---

## 1. Diagnostic Symptoms & Sensor Telemetry Profile
- **Stator Temperature:** Moderate to high heating (**68.0°C – 78.0°C**), localized on specific winding phases.
- **Audible Noise:** Deep, distinctive electrical buzzing or 100 Hz / 120 Hz line-frequency magnetic hum.
- **Vibration Velocity RMS:** Elevated electrical vibration (**2.8 – 4.2 mm/s**) strictly at **twice line frequency** (100 Hz on 50 Hz grid, 120 Hz on 60 Hz grid).
- **Discharge Pressure:** Normal hydraulic pressure output (**4.8 – 5.4 bar**).

---

## 2. Physical Root Causes
1. **Supply Voltage Unbalance:** Unbalanced incoming 3-phase line voltages from plant electrical distribution transformer (> 1% voltage unbalance induces > 6-10% current unbalance).
2. **High-Resistance Terminal Connection:** Oxidized or loose terminal lug on one phase lead in the motor conduit box.
3. **Blown Power Factor Capacitor:** Blown capacitor or single-phased fuse on an adjacent feeder bus.
4. **Internal Stator Turn-to-Turn Short:** Early dielectric breakdown between turns in a single stator winding slot.

---

## 3. Immediate Diagnostic Verification Checks
1. **Voltage Measurement:** Measure Line-to-Line voltages ($V_{AB}, V_{BC}, V_{CA}$) with a True-RMS digital multimeter at motor terminals.
   - Calculate $\%$ Voltage Unbalance = $100 \times \frac{\text{Max Deviation from Average}}{\text{Average Voltage}}$.
   - Value must not exceed $1.0\%$.
2. **Phase Current Check:** Measure individual phase currents ($I_A, I_B, I_C$) with a calibrated current clamp meter.
3. **Phase Resistance Balance:** De-energize motor, disconnect motor leads, and measure winding phase resistance with a micro-ohmmeter; phases must balance within $1.0\%$.
4. **Thermal Camera Scan:** Inspect motor junction box terminal lugs for high-resistance thermal hot-spots.

---

## 4. Recommended Corrective Maintenance Actions
1. **Re-torque Motor Terminals:** Clean oxidized copper contacts and torque terminal box hardware to specified Newton-meters.
2. **Balance Electrical Feeder:** Report incoming utility or transformer voltage imbalance to plant electrical maintenance.
3. **De-rate Motor Load:** If voltage unbalance between 1% and 3% cannot be immediately resolved, de-rate motor operating load per NEMA MG-1 curves.
4. **Motor Rewind / Replacement:** If phase resistance or surge test indicates shorted stator turns, send motor to electrical shop for stator rewind.

---

## 5. Safety Warnings & LOTO Notes
- **DANGER:** High voltage arc flash hazard! 415V / 480V 3-phase electrical systems can produce lethal arc blasts. Wear NFPA 70E rated arc-flash PPE.
- **LOTO:** Lock out and tag out the main motor circuit breaker at the MCC before opening motor electrical junction boxes.
