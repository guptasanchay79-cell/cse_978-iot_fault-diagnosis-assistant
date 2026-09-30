# Technical Diagnosis Manual: Dynamic Impeller Mass Unbalance

**Document ID:** KB-PUMP-009  
**Target Asset:** Industrial Centrifugal Slurry / Water Pump  
**Subsystem:** Rotating Impeller & Drive Shaft Assembly  
**Severity Level:** Medium to High (Fatigue Stress on Bearings and Shaft)

---

## 1. Diagnostic Symptoms & Sensor Telemetry Profile
- **Vibration Velocity RMS:** High radial vibration (**3.8 – 5.5 mm/s**), primarily sinusoidal.
- **Spectral Characteristic:** Dominant vibration amplitude concentrated strictly at **1X rotational running frequency** (e.g., 29.5 Hz for 1770 RPM pump). Minimal high-frequency bearing harmonics.
- **Phase Relationship:** 90-degree phase shift between horizontal and vertical radial vibration probes.
- **Temperature & Pressure:** Bearing temperature and discharge pressure remain within nominal ranges (**50°C – 60°C**, **4.5 – 5.5 bar**).

---

## 2. Physical Root Causes
1. **Material Buildup / Slurry Scale:** Uneven accumulation of slurry cake, scale, or sludge inside one or more impeller vane passages.
2. **Missing Impeller Vane Piece:** Cavitation chunking or foreign object impact breaking off a piece of the impeller shroud or vane.
3. **Loss of Balance Weights:** Dynamic balance correction weights detaching from the rotor assembly.
4. **Machining Eccentricity:** Off-center bore machining during maintenance overhaul.

---

## 3. Immediate Diagnostic Verification Checks
1. **FFT Vibration Signature:** Confirm dominant 1X frequency peak with low harmonics and low axial vibration.
2. **Single-Plane Strobe Phase Check:** Measure phase angle consistency with tachometer pulse to verify pure unbalance.
3. **Internal Casing Visual Inspection:** Remove suction spool; inspect impeller eye and outer vanes with a borescope for sludge buildup or missing fragments.
4. **Hand Rotation (Feel):** Disconnect coupling and rotate pump shaft by hand; check for binding or heavy spot.

---

## 4. Recommended Corrective Maintenance Actions
1. **Hydro-Blast Washout:** Flush pump casing with clean high-pressure water to dissolve internal slurry scale.
2. **Dynamic Balancing:** Perform field dynamic balancing using portable vibration balancing kit, or remove impeller for ISO G2.5 shop balancing.
3. **Impeller Replacement:** If vanes are cracked or eroded unevenly, replace with a statically and dynamically balanced OEM impeller.

---

## 5. Safety Warnings & LOTO Notes
- **LOTO:** Lock out pump motor feeder breaker before inspecting impeller passages. Never insert fingers through casing ports while uncoupled shaft can rotate.
