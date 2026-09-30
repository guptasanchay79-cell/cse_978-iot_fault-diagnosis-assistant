# Technical Diagnosis Manual: Impeller Cavitation & Hydraulic Performance Loss

**Document ID:** KB-PUMP-006  
**Target Asset:** Industrial Centrifugal Slurry / Water Pump  
**Subsystem:** Impeller Eye & Suction Casing  
**Severity Level:** High (Impeller Erosion & Premature Seal Destruction)

---

## 1. Diagnostic Symptoms & Sensor Telemetry Profile
- **Discharge Pressure:** Depressed significantly below normal rating (**1.8 – 2.9 bar**, below low alarm threshold of 3.0 bar).
- **Vibration Velocity RMS:** High-frequency erratic jitter elevated to **2.0 – 3.8 mm/s** with distinctive crackling / popping spikes.
- **Acoustic Signature:** Sounds like gravel, marbles, or small stones churning through the pump casing.
- **Temperature:** Normal steady baseline (**50.0°C – 58.0°C**).

---

## 2. Physical Root Causes
1. **NPSHA < NPSHR Deficit:** Net Positive Suction Head Available drops below the pump's Net Positive Suction Head Required.
2. **Vapor Bubble Micro-Jets:** Liquid static pressure at the impeller eye drops below vapor pressure, creating vapor cavities that violently collapse against blade surfaces at thousands of bar micro-jet pressure.
3. **Suction Restriction:** Throttled suction valve, plugged suction basket strainer, or collapsed flexible suction hose.
4. **Fluid Temperature Elevation:** Increased feed tank temperature raising the vapor pressure of the pumped liquid.

---

## 3. Immediate Diagnostic Verification Checks
1. **Acoustic Casing Inspection:** Listen directly against the pump volute casing using a mechanical stethoscope for crackling cavitation noise.
2. **Suction Pressure Gauge Inspection:** Read suction vacuum gauge; verify if suction pressure is below minimum allowable suction head.
3. **Suction Valve Position:** Verify suction isolation valve is 100% full-open and lock-wired in place.
4. **Liquid Level in Suction Sump:** Confirm feed tank / suction sump liquid level is above the minimum submergence vortex limit.

---

## 4. Recommended Corrective Maintenance Actions
1. **Throttle Discharge:** Slightly close the discharge throttle valve to shift operation left on the performance curve, reducing required NPSH.
2. **Clean Suction Strainer:** Isolate and clean the suction inlet strainer basket to remove accumulated foreign debris.
3. **Raise Suction Head:** Increase liquid level in feed tank or decrease suction line fluid temperature if heat exchangers are available.
4. **Impeller Inspection:** During next maintenance window, inspect impeller leading edges for characteristic spongy, pitted cavitation erosion.

---

## 5. Safety Warnings & LOTO Notes
- **CAUTION:** Prolonged cavitation can destroy an impeller in days and cause shock-induced mechanical seal face cracking.
- **LOTO:** Follow standard electrical and hydraulic isolation procedures when opening the pump wet end for impeller inspection.
