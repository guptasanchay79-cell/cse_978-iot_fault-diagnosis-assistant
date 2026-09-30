# Technical Diagnosis Manual: ADC Telemetry Freeze & Frozen Sensor Flat-Line

**Document ID:** KB-PUMP-008  
**Target Asset:** Industrial IoT Data Acquisition Gateway  
**Subsystem:** Microcontroller ADC Channel & Analog Signal Conditioning  
**Severity Level:** Medium (Undetected Fault Risk Due to Stale Telemetry)

---

## 1. Diagnostic Symptoms & Sensor Telemetry Profile
- **Reported Temperature:** Value completely static (e.g., exactly **54.00°C**) with **0.000 variance** across multiple consecutive sampling cycles.
- **Physical Noise Absence:** Completely missing natural thermal micro-variations ($\sigma < 0.001^\circ\text{C}$); real physical thermal sensors always exhibit minor Gaussian fluctuation.
- **Other Sensors Active:** Vibration and pressure continue to register normal realistic live variations.
- **Detector Status:** Flags `temperature sensor flat-line detected`.

---

## 2. Physical Root Causes
1. **Microcontroller ADC Bus Lockup:** Analog-to-Digital Converter peripheral registers frozen due to I2C/SPI bus lockup or clock stall.
2. **Software Buffer Deadlock:** Ring buffer in the IoT edge acquisition daemon locked on a stale cached memory pointer.
3. **Signal Isolator Saturation:** Field 4-20mA loop isolator output clamped against its rail or sample-and-hold capacitor locked.
4. **Firmware Watchdog Failure:** Edge firmware sensor polling thread crashed while the MQTT publisher thread continues running.

---

## 3. Immediate Diagnostic Verification Checks
1. **Dynamic Heat Stimulation:** Gently warm the external RTD thermowell with a heat gun or hot damp rag; check if the MQTT telemetry updates. If reading stays frozen, electronics are locked.
2. **Gateway Diagnostic Logs:** SSH / access the IoT edge gateway logs; inspect for I2C timeout or SPI bus bus-error exceptions.
3. **Hardware Multimeter Check:** Probe the 4-20mA loop or 0-10V analog input terminals on the ADC card; check if raw physical voltage/current changes while digital readout stays frozen.
4. **Reboot Test:** Perform a soft reset of the data acquisition daemon or gateway hardware.

---

## 4. Recommended Corrective Maintenance Actions
1. **Reset Acquisition Service:** Restart the edge sensor polling daemon: `systemctl restart iot-sensor-daq`.
2. **Power-Cycle Edge Hardware:** Power-cycle the edge DAQ unit to clear locked ADC silicon registers.
3. **Firmware Update:** Flash updated firmware containing automated I2C/SPI bus timeout recovery and hardware watchdog timers.
4. **Replace Signal Conditioning Module:** If the analog isolator or ADC input channel has suffered electrostatic discharge (ESD) damage, replace the input module.

---

## 5. Safety Warnings & LOTO Notes
- **WARNING:** A flatlined sensor is a severe safety hazard because it blinds the control system to real catastrophic thermal runaway.
- **CAUTION:** Take asset monitoring off automatic safety interlock bypass only after verifying live dynamic response.
