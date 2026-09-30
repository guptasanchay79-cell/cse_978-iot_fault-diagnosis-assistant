# Technical Diagnosis Manual: Hydraulic Water Hammer & Pressure Surge Shock

**Document ID:** KB-PUMP-014  
**Target Asset:** Industrial Centrifugal Slurry / Water Pump  
**Subsystem:** Discharge Non-Return Check Valve & Piping System  
**Severity Level:** Extreme (Catastrophic Piping Rupture & Flange Shear Risk)

---

## 1. Diagnostic Symptoms & Sensor Telemetry Profile
- **Discharge Pressure:** Violent transient pressure spikes soaring to **8.0 – 12.0+ bar** followed by rapid under-pressure troughs, oscillating wildly before settling.
- **Physical Piping Shock:** Severe pipe whip, structural banging thuds, and pipe support vibration.
- **Vibration Velocity RMS:** Transient high shock peaks exceeding **10.0+ mm/s** during valve closure events.
- **Steady State Parameters:** Following the shock event, steady-state pressure and temperature return to normal (**5.0 bar**, **52°C**).

---

## 2. Physical Root Causes
1. **Rapid Valve Closure:** Motorized or manual quarter-turn isolation valve slammed shut faster than the critical pipe wave travel time ($T_c = 2L/a$).
2. **Check Valve Slam:** Sluggish or worn non-return check valve allowing reverse fluid flow before violently slamming shut against its seat.
3. **Sudden Power Trip:** Unscheduled power outage causing immediate pump coast-down and column separation in high-head pipelines.
4. **Entrapped Air Pockets:** Failure to purge trapped air pockets at high pipeline elevation points, causing explosive compression.

---

## 3. Immediate Diagnostic Verification Checks
1. **Check Valve Inspection:** Inspect check valve counterweight, dashpot, or spring-assist mechanism for binding or broken springs.
2. **Pipe Support Inspection:** Walk the discharge pipeline; inspect pipe guides, anchors, spring hangers, and expansion joints for sheared anchor bolts or structural distortion.
3. **Air Release Valve Check:** Verify that automatic air release and vacuum relief valves installed at high points are venting properly.
4. **Transient Event Timing:** Correlate DCS timestamp of pressure spike with valve closure or pump stop signals.

---

## 4. Recommended Corrective Maintenance Actions
1. **Install Non-Slam Check Valves:** Replace swing check valves with fast-closing nozzle-type or spring-assisted dual-plate check valves.
2. **Adjust Valve Actuator Stroking Time:** Reconfigure motorized discharge control valve actuators to close with an S-curve or minimum 30-second stroking time.
3. **Surge Suppression Vessels:** Maintain proper nitrogen pre-charge pressure in hydropneumatic surge accumulator tanks or surge relief valves.
4. **Re-anchor Piping:** Re-weld cracked pipe support brackets and re-torque loose foundation anchor bolts.

---

## 5. Safety Warnings & LOTO Notes
- **DANGER:** Shock pressure waves can violently rupture cast-iron pump casings, blow out gaskets, and launch shrapnel.
- **LOTO:** Depressurize pipeline system completely prior to servicing discharge check valves or surge vessels.
