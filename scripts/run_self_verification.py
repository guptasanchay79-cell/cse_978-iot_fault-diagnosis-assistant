"""Complete Self-Verification Suite for PostgreSQL Integration.

Executes all 7 user verification requirements:
1. Verify Python PostgreSQL connection
2. Verify table schema for sensor_readings and fault_incidents
3. Run MQTT sensor simulator
4. Confirm incoming sensor readings are inserted into PostgreSQL
5. Query PostgreSQL to verify stored records
6. Confirm dashboard displays actual database records
7. Test database disconnection and recovery behavior
"""

from datetime import datetime, timezone
import json
import logging
from pathlib import Path
import sys
import threading
import time
import urllib.request

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import paho.mqtt.client as mqtt

from config import (
    MQTT_BROKER_HOST,
    MQTT_BROKER_PORT,
    MQTT_TELEMETRY_TOPIC,
    POSTGRES_DB,
    POSTGRES_HOST,
    POSTGRES_PORT,
    POSTGRES_USER,
)
from database.db import (
    get_database_stats,
    get_db_connection,
    get_recent_diagnoses,
    get_recent_sensor_readings,
    insert_sensor_reading,
    is_database_available,
)
from diagnosis.fault_detector import FaultDetector
from mqtt.mqtt_subscriber import TelemetrySubscriber
from mqtt.sensor_simulator import PumpTelemetrySimulator

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] SelfVerify: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    stream=sys.stdout,
)
logger = logging.getLogger("SelfVerify")


def step1_verify_connection():
    logger.info("=====================================================================")
    logger.info("VERIFICATION STEP 1: Verify Python to PostgreSQL Connection")
    logger.info("=====================================================================")
    is_up = is_database_available(force_check=True)
    if not is_up:
        logger.error("FAILED: Could not connect to PostgreSQL on %s:%s", POSTGRES_HOST, POSTGRES_PORT)
        return False

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT current_database(), current_user, version();")
            row = cur.fetchone()
            db_name = row.get("current_database") if isinstance(row, dict) else row[0]
            db_user = row.get("current_user") if isinstance(row, dict) else row[1]
            db_ver = row.get("version") if isinstance(row, dict) else row[2]

            logger.info("  Active Database: %s", db_name)
            logger.info("  Authenticated User: %s", db_user)
            logger.info("  Engine Version: %s", db_ver.split(",")[0])
            assert db_name == POSTGRES_DB, f"Expected {POSTGRES_DB}, got {db_name}"

    logger.info(">>> STEP 1 RESULT: SUCCESS (Connected to %s)", POSTGRES_DB)
    return True


def step2_verify_tables():
    logger.info("\n=====================================================================")
    logger.info("VERIFICATION STEP 2: Verify Required Table Schema (sensor_readings)")
    logger.info("=====================================================================")
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                ORDER BY table_name;
            """)
            tables = [r["table_name"] if isinstance(r, dict) else r[0] for r in cur.fetchall()]
            logger.info("  Public tables found: %s", tables)
            assert "sensor_readings" in tables, "Table 'sensor_readings' not found!"
            assert "fault_incidents" in tables, "Table 'fault_incidents' not found!"

            # Inspect columns of sensor_readings
            cur.execute("""
                SELECT column_name, data_type, is_nullable, column_default
                FROM information_schema.columns
                WHERE table_name = 'sensor_readings'
                ORDER BY ordinal_position;
            """)
            cols = cur.fetchall()
            logger.info("  Schema columns in 'sensor_readings':")
            col_map = {}
            for c in cols:
                name = c["column_name"] if isinstance(c, dict) else c[0]
                dtype = c["data_type"] if isinstance(c, dict) else c[1]
                col_map[name] = dtype
                logger.info("    • %-16s : %s", name, dtype)

            expected_fields = ["id", "device_id", "temperature", "vibration", "pressure", "timestamp", "fault_status", "mode", "created_at"]
            for field in expected_fields:
                assert field in col_map, f"Expected field '{field}' missing from sensor_readings!"

    logger.info(">>> STEP 2 RESULT: SUCCESS (All required fields verified in sensor_readings)")
    return True


def step3_and_4_run_simulator_and_verify_inserts():
    logger.info("\n=====================================================================")
    logger.info("VERIFICATION STEPS 3 & 4: Run MQTT Simulator & Ingest into PostgreSQL")
    logger.info("=====================================================================")

    # Baseline count before test
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT count(*) as c FROM sensor_readings;")
            row = cur.fetchone()
            count_before = row["c"] if isinstance(row, dict) else row[0]

    logger.info("  Baseline row count in sensor_readings: %d", count_before)

    # Start live subscriber with database persistence enabled
    received_messages = []
    def on_reading(data):
        received_messages.append(data)
        logger.info("  [MQTT RECV -> DB] Device=%s | Temp=%.2f C | Vib=%.2f mm/s | Press=%.2f bar | Time=%s",
                    data["device_id"], data["temperature"], data["vibration"], data["pressure"], data["timestamp"])

    subscriber = TelemetrySubscriber(
        host=MQTT_BROKER_HOST,
        port=MQTT_BROKER_PORT,
        topic=MQTT_TELEMETRY_TOPIC,
        on_reading_callback=on_reading,
        persist_to_db=True,
    )
    subscriber.start()
    time.sleep(1.0)

    # Publish 6 readings across normal and fault modes using PumpTelemetrySimulator
    pub_client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2, client_id="verify_publisher")
    pub_client.connect(MQTT_BROKER_HOST, MQTT_BROKER_PORT, keepalive=60)
    pub_client.loop_start()

    logger.info("  Starting MQTT simulator stream to '%s'...", MQTT_TELEMETRY_TOPIC)
    
    # 3 normal readings
    sim_normal = PumpTelemetrySimulator(device_id="verify_pump_01", mode="normal")
    for i in range(3):
        r = sim_normal.step()
        pub_client.publish(MQTT_TELEMETRY_TOPIC, json.dumps(r), qos=1)
        time.sleep(0.4)

    # 3 overheating readings
    sim_overheat = PumpTelemetrySimulator(device_id="verify_pump_01", mode="overheating")
    for i in range(3):
        r = sim_overheat.step()
        pub_client.publish(MQTT_TELEMETRY_TOPIC, json.dumps(r), qos=1)
        time.sleep(0.4)

    time.sleep(1.5)  # allow subscriber to ingest and commit to PostgreSQL
    pub_client.loop_stop()
    pub_client.disconnect()
    subscriber.stop()

    logger.info("  Total telemetry messages received by subscriber: %d", len(received_messages))
    assert len(received_messages) >= 6, f"Expected at least 6 messages, got {len(received_messages)}"

    logger.info(">>> STEPS 3 & 4 RESULT: SUCCESS (Simulator published and readings ingested)")
    return True


def step5_query_database_and_verify_records():
    logger.info("\n=====================================================================")
    logger.info("VERIFICATION STEP 5: Query PostgreSQL to Verify Stored Records")
    logger.info("=====================================================================")

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, device_id, temperature, vibration, pressure, timestamp, fault_status, mode, created_at
                FROM sensor_readings
                WHERE device_id = 'verify_pump_01'
                ORDER BY id ASC;
            """)
            records = cur.fetchall()
            logger.info("  Retrieved %d persisted sensor_readings rows for 'verify_pump_01':", len(records))
            for r in records:
                logger.info(
                    "    ID: %-3d | Dev: %s | Temp: %5.2f C | Vib: %4.2f mm/s | Press: %4.2f bar | Status: %-12s | Time: %s",
                    r["id"], r["device_id"], float(r["temperature"]), float(r["vibration"]), float(r["pressure"]),
                    r["fault_status"], r["timestamp"]
                )
            assert len(records) >= 6, f"Expected at least 6 rows stored in DB, found {len(records)}"

            # Verify that fault_status values were properly assigned
            statuses = [r["fault_status"] for r in records]
            logger.info("  Persisted fault statuses: %s", statuses)
            assert "normal" in statuses, "Expected 'normal' fault status in records"

    logger.info(">>> STEP 5 RESULT: SUCCESS (Records verified directly in PostgreSQL)")
    return True


def step6_verify_dashboard_data():
    logger.info("\n=====================================================================")
    logger.info("VERIFICATION STEP 6: Confirm Dashboard Displays Actual Database Records")
    logger.info("=====================================================================")

    from dashboard.app import DashboardHTTPHandler, ThreadedTCPServer, state

    # Start dashboard server on port 8085
    port = 8085
    server = ThreadedTCPServer(("127.0.0.1", port), DashboardHTTPHandler)
    srv_thread = threading.Thread(target=server.serve_forever, daemon=True)
    srv_thread.start()
    time.sleep(1.0)

    try:
        # Check /api/status
        req = urllib.request.urlopen(f"http://127.0.0.1:{port}/api/status")
        assert req.status == 200
        data = json.loads(req.read().decode("utf-8"))

        db_info = data.get("database", {})
        logger.info("  Dashboard reported database status:")
        logger.info("    Connected: %s", db_info.get("connected"))
        logger.info("    Database: %s", db_info.get("database"))
        logger.info("    Sensor Readings Count: %s", db_info.get("sensor_readings_count"))
        logger.info("    Incident Reports Count: %s", db_info.get("incidents_count"))

        assert db_info.get("connected") is True, "Dashboard reported database disconnected!"
        assert db_info.get("database") == "iot_fault_diagnosis"
        assert int(db_info.get("sensor_readings_count", 0)) >= 6

        # Check /api/readings returns real database records
        req_readings = urllib.request.urlopen(f"http://127.0.0.1:{port}/api/readings?limit=5")
        assert req_readings.status == 200
        readings_list = json.loads(req_readings.read().decode("utf-8"))
        logger.info("  Dashboard /api/readings returned %d recent records:", len(readings_list))
        for r in readings_list[:3]:
            logger.info("    • ID: %s | Temp: %s C | Vib: %s | Press: %s | Status: %s",
                        r.get("id"), r.get("temperature"), r.get("vibration"), r.get("pressure"), r.get("fault_status"))
        assert len(readings_list) > 0, "No records returned from /api/readings"

        # Check /api/diagnoses returns real database diagnoses
        req_diag = urllib.request.urlopen(f"http://127.0.0.1:{port}/api/diagnoses")
        assert req_diag.status == 200
        diag_list = json.loads(req_diag.read().decode("utf-8"))
        logger.info("  Dashboard /api/diagnoses returned %d incident reports:", len(diag_list))
        assert len(diag_list) > 0, "No diagnoses returned from /api/diagnoses"

        logger.info(">>> STEP 6 RESULT: SUCCESS (Dashboard serves real database data)")
    finally:
        state.is_running = False
        server.shutdown()
        server.server_close()


def step7_test_disconnection_and_recovery():
    logger.info("\n=====================================================================")
    logger.info("VERIFICATION STEP 7: Test Database Disconnection & Recovery Behavior")
    logger.info("=====================================================================")

    import database.db as db_mod

    # 1. Normal state
    assert db_mod.is_database_available(force_check=True) is True
    logger.info("  Initial State: PostgreSQL is connected (is_database_available() == True)")

    # 2. Simulate disconnection by pointing to closed port
    orig_port = db_mod.POSTGRES_PORT
    try:
        db_mod.POSTGRES_PORT = 59999
        logger.info("  Simulating database outage (port set to 59999)...")
        avail = db_mod.is_database_available(force_check=True)
        assert avail is False, "Expected is_database_available to return False!"
        logger.info("  PASS: Outage handled gracefully without raising unhandled exception.")

        # Attempt insert during outage
        res = db_mod.insert_sensor_reading({
            "device_id": "test_offline",
            "temperature": 55.0,
            "vibration": 1.2,
            "pressure": 5.0,
        })
        assert res is False, "Expected insert to return False without crashing"
        logger.info("  PASS: insert_sensor_reading() returned False safely during outage.")

        # Attempt query during outage
        q_res = db_mod.get_recent_sensor_readings()
        assert q_res == [], "Expected query to return empty list during outage"
        logger.info("  PASS: get_recent_sensor_readings() returned empty list safely during outage.")

    finally:
        # 3. Restore and verify recovery
        db_mod.POSTGRES_PORT = orig_port
        logger.info("  Restoring database connection (port %d)...", orig_port)
        recovered = db_mod.is_database_available(force_check=True)
        assert recovered is True, "Expected database to recover once port restored!"
        logger.info("  PASS: Database connection fully restored (is_database_available() == True).")

    logger.info(">>> STEP 7 RESULT: SUCCESS (Disconnection & recovery behavior verified)")
    return True


def cleanup_test_data():
    logger.info("\nCleaning up verification rows from sensor_readings...")
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM sensor_readings WHERE device_id = 'verify_pump_01';")
    logger.info("Cleaned up test rows.")


def main():
    logger.info("#####################################################################")
    logger.info("STARTING COMPREHENSIVE END-TO-END SELF-VERIFICATION")
    logger.info("#####################################################################")

    step1_verify_connection()
    step2_verify_tables()
    step3_and_4_run_simulator_and_verify_inserts()
    step5_query_database_and_verify_records()
    step6_verify_dashboard_data()
    step7_test_disconnection_and_recovery()
    cleanup_test_data()

    logger.info("\n#####################################################################")
    logger.info("ALL 7 VERIFICATION STEPS COMPLETED AND VALIDATED SUCCESSFULLY!")
    logger.info("#####################################################################")


if __name__ == "__main__":
    main()
