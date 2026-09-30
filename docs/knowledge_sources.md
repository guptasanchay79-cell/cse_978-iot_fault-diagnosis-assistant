# Knowledge Base Provenance & Attribution Register — P_311

This register documents the origin, methodology, and verification status of every technical manual in `knowledge_base/`.

In strict adherence to **Project Constraint 5 (Honesty Regarding Sources)**, none of these documents are claimed to be proprietary OEM manufacturer manuals. They have been authored systematically by Antigravity and structured according to established engineering standards:
- **ISO 10816-3:** Mechanical vibration evaluation on industrial machines.
- **API 610 / ISO 13709:** Centrifugal pumps for petroleum, petrochemical, and natural gas industries.
- **IEEE 841:** Standard for severe duty premium efficiency electric motors.

---

## Technical Documents Manifest (14 Files)

| File Name | Primary Topic | Category | Origin & Reference Standards | Verification Status |
|---|---|---|---|---|
| `KB01_bearing_inner_raceway_fatigue.md` | Deep groove/spherical roller bearing raceway spalling and fatigue | Fault Match (`bearing_wear`) | Synthetic technical summary based on ISO 10816-3 Zone D vibration profiles | Reviewed & Approved |
| `KB02_bearing_lubrication_starvation.md` | Grease degradation, boundary lubrication breakdown, and frictional wear | Fault Match (`bearing_wear`) | Synthetic technical summary based on SKF Bearing Maintenance Handbook | Reviewed & Approved |
| `KB03_motor_winding_overheating.md` | Stator winding insulation thermal breakdown and cooling fan shroud blockage | Fault Match (`overheating`) | Synthetic summary referencing NEMA Class F insulation & IEEE 841 thermal limits | Reviewed & Approved |
| `KB04_bearing_housing_thermal_runaway.md` | Bearing friction thermal buildup from excessive preload or seal rubbing | Fault Match (`overheating`) | Synthetic summary referencing industrial rotating machinery maintenance SOPs | Reviewed & Approved |
| `KB05_discharge_pipe_rupture_leakage.md` | Discharge line flange gasket blowout and pipe rupture causing sudden loss of head | Fault Match (`pressure_drop`) | Synthetic summary referencing ASME B31.3 process piping hydraulic leak diagnostics | Reviewed & Approved |
| `KB06_impeller_cavitation_hydraulic_loss.md` | Vapor bubble collapse in impeller eye due to insufficient NPSH available | Fault Match (`pressure_drop`) | Synthetic summary referencing Hydraulic Institute (HI) standards for cavitation | Reviewed & Approved |
| `KB07_rtd_temperature_sensor_disconnect.md` | Pt100 RTD sensor wire break / open-circuit fault (-999°C flag) | Fault Match (`sensor_failure`) | Synthetic summary based on industrial 3-wire RTD sensor failure characteristics | Reviewed & Approved |
| `KB08_adc_telemetry_sensor_flatline.md` | Analog-to-Digital Converter freeze, frozen sample-and-hold circuit | Fault Match (`sensor_failure`) | Synthetic summary based on microcontroller ADC hardware lockup symptoms | Reviewed & Approved |
| `KB09_dynamic_impeller_unbalance.md` | Mass unbalance due to slurry buildup or broken vane (1X RPM vibration) | Distractor | Synthetic summary referencing ISO 1940-1 dynamic balancing standards | Reviewed & Approved |
| `KB10_shaft_angular_misalignment.md` | Pump-motor angular and parallel shaft misalignment (2X RPM vibration) | Distractor | Synthetic summary based on laser shaft alignment technical guides | Reviewed & Approved |
| `KB11_mechanical_seal_face_failure.md` | Mechanical seal carbon face chipping, leakage, and seal flush loss | Distractor | Synthetic summary based on API 682 mechanical seal piping plans | Reviewed & Approved |
| `KB12_suction_strainer_clogging.md` | Debris accumulation on suction basket strainer causing vacuum rise | Distractor | Synthetic summary based on industrial centrifugal pump intake manuals | Reviewed & Approved |
| `KB13_motor_electrical_phase_imbalance.md` | Voltage unbalance across 3-phase AC stator windings causing 100/120 Hz hum | Distractor | Synthetic summary based on IEEE 112 polyphase induction motor diagnostics | Reviewed & Approved |
| `KB14_hydraulic_water_hammer_shock.md` | Rapid check-valve slamming and pressure wave oscillations | Distractor | Synthetic summary based on hydraulic transient analysis guidelines | Reviewed & Approved |
