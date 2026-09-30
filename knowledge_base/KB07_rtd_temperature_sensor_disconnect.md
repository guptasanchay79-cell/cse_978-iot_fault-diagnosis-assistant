# Technical Diagnosis Manual: RTD Temperature Sensor Disconnect & Open-Circuit

**Document ID:** KB-PUMP-007  
**Target Asset:** Industrial Centrifugal Pump Instrumentation  
**Subsystem:** 3-Wire Pt100 RTD Sensor Channel & Transmitter  
**Severity Level:** Medium (Loss of Asset Monitoring / Telemetry Blind Spot)

---

## 1. Diagnostic Symptoms & Sensor Telemetry Profile
- **Reported Temperature:** Value drops instantly to **-999.0°C** or an out-of-scale negative/overflow error flag.
- **Physical Validity Violation:** Reading falls drastically outside the physical valid sensor envelope ($-20.0^\circ\text{C}$ to $+150.0^\circ\text{C}$).
- **Vibration & Pressure:** Normal steady values (**1.2 – 1.8 mm/s**, **4.5 – 5.5 bar**).
- **Physical Machine State:** Pump and motor are operating perfectly normally with healthy touch temperature; the fault is purely instrumentation.

---

## 2. Physical Root Causes
1. **Broken Sensor Lead Wire:** Physical severance of the copper RTD signal conductor due to conduit vibration or mechanical fatigue.
2. **Terminal Block Disconnect:** Loose screw terminal or loose spring-clamp in the field junction box.
3. **RTD Element Fracture:** Mechanical shock or thermal shock causing the platinum wire coil/thin-film element inside the thermowell to break.
4. **Transmitter Failure:** Head-mounted 4-20mA / Modbus RTD temperature transmitter internal A/D converter open-circuit fault.

---

## 3. Immediate Diagnostic Verification Checks
1. **Physical Hand-Touch / IR Check:** Measure bearing housing temperature with a portable hand-held infrared thermometer; confirm bearing is physically warm (~52°C) and NOT frozen.
2. **Terminal Box Inspection:** Open local sensor junction box; check for disconnected, pinched, or corroded terminal connections.
3. **Multimeter Resistance Measurement:** Disconnect RTD wires at the terminal block and measure resistance with a calibrated DMM:
   - Healthy Pt100 at 25°C should read $\approx 109.7\,\Omega$.
   - An open-circuit sensor will read infinite resistance ($\text{OL} / > 1\text{ M}\Omega$).
4. **Cable Continuity Test:** Verify wiring continuity between field junction box and the IoT gateway / PLC analog input card.

---

## 4. Recommended Corrective Maintenance Actions
1. **Tighten Field Terminals:** Strip wire clean and re-terminate into the spring-cage terminal block.
2. **Replace RTD Probe:** Unscrew the defective Pt100 spring-loaded probe from the thermowell and insert a new calibrated 3-wire RTD assembly.
3. **Verify Transmitter Configuration:** Recalibrate the 4-20mA head transmitter range (e.g., 0°C to 150°C = 4mA to 20mA).
4. **Secure Sensor Conduit:** Add vibration-damping conduit clamps to prevent cable flexing and future fatigue failure.

---

## 5. Safety Warnings & LOTO Notes
- **NOTE:** Thermowell allows replacement of the RTD probe while the pump is running under pressure. Do NOT loosen the main thermowell process fitting.
- **ELECTRICAL:** Low-voltage signal circuit (typically 24V DC loop). De-energize instrument loop power before stripping wires.
