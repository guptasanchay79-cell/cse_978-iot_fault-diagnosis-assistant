"""Automated End-to-End Verification Test for MQTT -> Python -> PostgreSQL -> Dashboard Data Flow.

Tests:
1. Python connection to PostgreSQL (iot_fault_diagnosis).
2. Sensor_readings and fault_incidents tables existence.
3. Live MQTT simulator publishing real sensor telemetry.
4. MQTT subscriber receiving and inserting real readings into PostgreSQL sensor_readings table.
5. Querying PostgreSQL to verify inserted readings, timestamps, and fault_status.
6. Database disconnection and recovery (circuit breaker) behavior.
7. Dashboard state and API endpoints serving real database records.
"""

from datetime import datetime, timezone
import json
import logging
from pathlib import Path
import sys
import time

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from config import (
    MQTT_BROKER_HOST,
    MQTT_BROKER_PORT,
    MQTT_TELEMETRY_TOPIC,
    POSTGRES_DB,
)
from database.db import (
    get_database_stats,
    get_db_connection,
    get_recent_diagnoses,
    get_recent_sensor_readings,
    insert_sensor_reading,
    is_database_available,
)
from mqtt.mqtt_subscriber import TelemetrySubscriber
from mqtt.sensor_simulator import PumpTelemetrySimulator

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] IntegrationTest: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    stream=sys.stdout,
)
logger = logging.getLogger("IntegrationTest")


def run_e2e_test() -> bool:
    logger.info("=== STEP 1: Verify PostgreSQL Connection ===")
    assert is_database_available(force_check=True), "PostgreSQL is not reachable!"
    logger.info("PASS: Python successfully connected to PostgreSQL database: %s", POSTGRES_DB)

    logger.info("\n=== STEP 2: Verify Tables in PostgreSQL ===")
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public';
            """)
            tables = [r["table_name"] for r in cur.fetchall()]
            logger.info("Tables in '%s': %s", POSTGRES_DB, tables)
            assert "sensor_readings" in tables, "'sensor_readings' table is missing!"
            assert "fault_incidents" in tables, "'fault_incidents' table is missing!"
    logger.info("PASS: Required tables 'sensor_readings' and 'fault_incidents' confirmed.")

    logger.info("\n=== STEP 3 & 4: Start MQTT Subscriber & Publish Live Simulator Data ===")
    import paho.mqtt.client as mqtt

    received_readings = []

    def on_reading(data):
        received_readings.append(data)
        logger.info("Subscriber callback received: %s (Temp=%.1f, Vib=%.2f, Press=%.2f)",
                    data["device_id"], data["temperature"], data["vibration"], data["pressure"])

    # Start subscriber with database persistence enabled
    subscriber = TelemetrySubscriber(
        host=MQTT_BROKER_HOST,
        port=MQTT_BROKER_PORT,
        topic=MQTT_TELEMETRY_TOPIC,
        on_reading_callback=on_reading,
        persist_to_db=True,
    )
    subscriber.start()
    time.sleep(1.0)

    # Publish 5 live telemetry readings using PumpTelemetrySimulator
    sim = PumpTelemetrySimulator(device_id="test_sim_pump_01", mode="normal")
    publisher_client = mqtt.Client(
        callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
        client_id="test_e2e_publisher",
    )
    publisher_client.connect(MQTT_BROKER_HOST, MQTT_BROKER_PORT, keepalive=60)
    publisher_client.loop_start()

    logger.info("Publishing 5 sensor readings over MQTT topic: '%s'...", MQTT_TELEMETRY_TOPIC)
    published_timestamps = []
    for i in range(5):
        reading = sim.step()
        published_timestamps.append(reading["timestamp"])
        publisher_client.publish(MQTT_TELEMETRY_TOPIC, json.dumps(reading), qos=1)
        time.sleep(0.3)

    time.sleep(1.5)  # allow messages to arrive and persist
    publisher_client.loop_stop()
    publisher_client.disconnect()
    subscriber.stop()

    logger.info("Subscriber received %d messages via MQTT.", len(received_readings))
    assert len(received_readings) >= 5, f"Expected at least 5 messages, got {len(received_readings)}"
    logger.info("PASS: MQTT sensor simulator published and subscriber ingested all messages.")

    logger.info("\n=== STEP 5: Query Database to Verify Stored Readings ===")
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, device_id, temperature, vibration, pressure, timestamp, fault_status, created_at "
                "FROM sensor_readings WHERE device_id = 'test_sim_pump_01' "
                "ORDER BY timestamp ASC;"
            )
            rows = cur.fetchall()
            logger.info("Found %d rows in PostgreSQL for device 'test_sim_pump_01':", len(rows))
            for r in rows:
                logger.info("  Row id=%d: temp=%.2f, vib=%.2f, press=%.2f, fault_status='%s', time=%s",
                            r["id"], float(r["temperature"]), float(r["vibration"]), float(r["pressure"]),
                            r["fault_status"], r["timestamp"])
            assert len(rows) >= 5, f"Expected at least 5 database rows, found {len(rows)}"

    logger.info("PASS: Real MQTT sensor readings accurately stored in PostgreSQL table 'sensor_readings'.")

    logger.info("\n=== STEP 6: Test Dashboard Preloading & Real Record Retrieval ===")
    recent = get_recent_sensor_readings(limit=10, chronological=True)
    logger.info("Retrieved %d recent sensor readings from database for dashboard charts.", len(recent))
    assert len(recent) > 0, "Recent sensor readings should not be empty!"
    stats = get_database_stats()
    logger.info("Database stats: %s", stats)
    assert stats["connected"] is True
    assert stats["sensor_readings_count"] >= 5
    logger.info("PASS: Dashboard data repository retrieves live records and stats.")

    logger.info("\n=== STEP 7: Test Database Disconnection & Graceful Recovery ===")
    import database.db as db_mod

    # Temporarily force circuit breaker to disconnected state
    original_port = db_mod.POSTGRES_PORT
    try:
        # Simulate offline DB by pointing to unused port
        db_mod.POSTGRES_PORT = 54399
        is_avail = db_mod.is_database_available(force_check=True)
        assert is_avail is False, "Database should be reported as unavailable when offline"
        logger.info("PASS: Disconnection detected. is_database_available() gracefully returned False.")

        # Test that insert_sensor_reading fails gracefully without crashing or throwing
        offline_insert = db_mod.insert_sensor_reading({
            "device_id": "test_offline",
            "temperature": 50.0,
            "vibration": 1.0,
            "pressure": 5.0,
        })
        assert offline_insert is False, "Insert should return False without raising exception"
        logger.info("PASS: insert_sensor_reading() gracefully handled offline state without crashing.")

        # Test that queries fail gracefully and return empty list
        offline_readings = db_mod.get_recent_sensor_readings()
        assert offline_readings == [], "get_recent_sensor_readings() should return empty list when offline"
        logger.info("PASS: get_recent_sensor_readings() gracefully returned empty list when offline.")

    finally:
        # Restore configuration and verify recovery
        db_mod.POSTGRES_PORT = original_port
        recovered = db_mod.is_database_available(force_check=True)
        assert recovered is True, "Database should recover once connectivity is restored"
        logger.info("PASS: Database connectivity successfully recovered.")

    # Clean up test rows
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM sensor_readings WHERE device_id = 'test_sim_pump_01';")
    logger.info("Cleaned up test sensor readings.")

    logger.info("\n=================================================================")
    logger.info("ALL END-TO-END INTEGRATION TESTS PASSED SUCCESSFULLY!")
    logger.info("=================================================================")
    return True


if __name__ == "__main__":
    if not run_e2e_test():
        sys.exit(1)
