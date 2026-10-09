"""Automated end-to-end verification for P_311 Dashboard."""
import json
import time
import urllib.request
import urllib.error

BASE_URL = "http://localhost:8080"

def get(path):
    req = urllib.request.Request(f"{BASE_URL}{path}")
    with urllib.request.urlopen(req, timeout=10) as resp:
        return resp.status, resp.read().decode("utf-8")

def post_json(path, data):
    body = json.dumps(data).encode("utf-8")
    req = urllib.request.Request(f"{BASE_URL}{path}", data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        return resp.status, json.loads(resp.read().decode("utf-8"))

def wait_for_diagnosis(target_category, timeout=60):
    start = time.time()
    last_count = 0
    # get initial count
    _, status_str = get("/api/status")
    status_data = json.loads(status_str)
    initial_count = status_data.get("total_diagnoses", 0)
    
    while time.time() - start < timeout:
        _, status_str = get("/api/status")
        status_data = json.loads(status_str)
        curr_count = status_data.get("total_diagnoses", 0)
        latest_diag = status_data.get("latest_diagnosis")
        latest_reading = status_data.get("latest_reading", {})
        
        print(f"  [T+{time.time()-start:.1f}s] Telemetry: T={latest_reading.get('temperature')} V={latest_reading.get('vibration')} P={latest_reading.get('pressure')} | Total Diags: {curr_count}")
        
        if curr_count > initial_count and latest_diag:
            if target_category in latest_diag.get("fault_category", ""):
                elapsed = time.time() - start
                return latest_diag, latest_reading, elapsed
        time.sleep(1.0)
    return None, None, time.time() - start

print("=== Starting E2E Pipeline Verification ===")

# Check 4: Normal Mode
print("\n--- Check 4: Normal Mode ---")
post_json("/api/mode", {"mode": "normal"})
time.sleep(3.0)
_, status_str = get("/api/status")
status = json.loads(status_str)
r = status.get("latest_reading", {})
print(f"Normal telemetry: Temp={r.get('temperature')}°C, Vib={r.get('vibration')} mm/s, Press={r.get('pressure')} bar")
assert 45.0 <= r.get("temperature") <= 65.0, f"Temp out of normal range: {r.get('temperature')}"
assert 0.8 <= r.get("vibration") <= 2.5, f"Vib out of normal range: {r.get('vibration')}"
assert 4.0 <= r.get("pressure") <= 6.0, f"Pressure out of normal range: {r.get('pressure')}"
print("PASS: Normal telemetry within nominal bounds.")

# Check 5: Bearing Wear
print("\n--- Check 5: Bearing Wear ---")
post_json("/api/mode", {"mode": "bearing_wear"})
diag, reading, elapsed = wait_for_diagnosis("bearing_wear", timeout=45)
if diag:
    print(f"PASS: Bearing wear diagnosis arrived in {elapsed:.2f}s!")
    print(f"  Category: {diag.get('fault_category')}")
    print(f"  Vibration: {reading.get('vibration')} mm/s")
    print(f"  Runtime: {diag.get('runtime')}")
    print(f"  Top source: {diag.get('retrieved_sources')[0] if diag.get('retrieved_sources') else 'None'}")
else:
    print(f"FAIL: Bearing wear diagnosis timed out.")

# Check 6: Overheating
print("\n--- Check 6: Stator Overheating ---")
post_json("/api/mode", {"mode": "overheating"})
diag, reading, elapsed = wait_for_diagnosis("overheating", timeout=45)
if diag:
    print(f"PASS: Overheating diagnosis arrived in {elapsed:.2f}s!")
    print(f"  Category: {diag.get('fault_category')}")
    print(f"  Temperature: {reading.get('temperature')} °C")
    print(f"  Runtime: {diag.get('runtime')}")
else:
    print(f"FAIL: Overheating diagnosis timed out.")

# Check 7: Pressure Drop
print("\n--- Check 7: Pressure Drop ---")
post_json("/api/mode", {"mode": "pressure_drop"})
diag, reading, elapsed = wait_for_diagnosis("pressure_drop", timeout=45)
if diag:
    print(f"PASS: Pressure drop diagnosis arrived in {elapsed:.2f}s!")
    print(f"  Category: {diag.get('fault_category')}")
    print(f"  Pressure: {reading.get('pressure')} bar")
    print(f"  Runtime: {diag.get('runtime')}")
else:
    print(f"FAIL: Pressure drop diagnosis timed out.")

# Check 8: RTD Disconnect
print("\n--- Check 8: RTD Disconnect ---")
post_json("/api/mode", {"mode": "sensor_failure", "submode": "disconnect"})
diag, reading, elapsed = wait_for_diagnosis("sensor_failure", timeout=45)
if diag:
    print(f"PASS: RTD Disconnect diagnosis arrived in {elapsed:.2f}s!")
    print(f"  Category: {diag.get('fault_category')}")
    print(f"  Temperature: {reading.get('temperature')} (should be -999.0)")
    print(f"  Runtime: {diag.get('runtime')}")
else:
    print(f"FAIL: RTD Disconnect diagnosis timed out.")

# Check 9: ADC Flatline
print("\n--- Check 9: ADC Flatline ---")
post_json("/api/mode", {"mode": "sensor_failure", "submode": "flatline"})
diag, reading, elapsed = wait_for_diagnosis("sensor_failure", timeout=45)
if diag:
    print(f"PASS: ADC Flatline diagnosis arrived in {elapsed:.2f}s!")
    print(f"  Category: {diag.get('fault_category')}")
    print(f"  Runtime: {diag.get('runtime')}")
else:
    print(f"FAIL: ADC Flatline diagnosis timed out.")

# Reset to Normal
print("\n--- Check 13: Reset to Normal ---")
post_json("/api/mode", {"mode": "normal"})
time.sleep(2.0)
_, status_str = get("/api/status")
status = json.loads(status_str)
print(f"Reset mode: {status.get('mode')}")
assert status.get("mode") == "normal"
print("PASS: Mode successfully reset to normal.")
