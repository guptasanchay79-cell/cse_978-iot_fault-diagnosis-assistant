"""P_311: Knowledge-Driven IoT Fault Diagnosis Assistant.

Industrial Web Dashboard Server.
Provides:
- Real-time telemetry streaming (SSE)
- Dynamic fault injection API (Normal, Bearing Wear, Overheating, Pressure Drop, Sensor Failure)
- RAG retrieval and LLM diagnosis visualization
- Static asset serving for modern dark-mode SCADA web UI
"""

import http.server
import json
import logging
from pathlib import Path
import queue
import socketserver
import sys
import threading
import time
from urllib.parse import parse_qs, urlparse

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from config import (
    DATA_DIR,
    FAULT_MODE_BEARING_WEAR,
    FAULT_MODE_NORMAL,
    FAULT_MODE_OVERHEATING,
    FAULT_MODE_PRESSURE_DROP,
    FAULT_MODE_SENSOR_FAILURE,
    MQTT_BROKER_HOST,
    MQTT_BROKER_PORT,
    MQTT_TELEMETRY_TOPIC,
    TELEMETRY_BATCH_FLUSH_INTERVAL,
    TELEMETRY_BATCH_SIZE,
    TELEMETRY_QUEUE_MAXSIZE,
    TELEMETRY_RETENTION_DAYS,
)
import paho.mqtt.client as mqtt

from database.db import (
    get_database_stats,
    get_db_stats,
    get_recent_diagnoses,
    get_recent_sensor_readings,
    insert_diagnosis,
    insert_sensor_reading,
    insert_sensor_readings_batch,
    is_database_available,
    prune_old_sensor_readings,
)
from diagnosis.fault_detector import FaultDetector
from llm.client import LocalLLMClient
from mqtt.sensor_simulator import PumpTelemetrySimulator
from rag.retriever import TFIDFRetriever

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] Dashboard: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    stream=sys.stdout,
)
logger = logging.getLogger("Dashboard")

PORT = 8080
STATIC_DIR = Path(__file__).resolve().parent

# Non-blocking telemetry queue for database persistence
telemetry_queue = queue.Queue(maxsize=TELEMETRY_QUEUE_MAXSIZE)


class DashboardState:
    """Thread-safe state manager for the dashboard."""

    def __init__(self):
        self.lock = threading.Lock()
        self.current_mode = FAULT_MODE_NORMAL
        self.sensor_submode = "flatline"
        self.simulator = PumpTelemetrySimulator(mode=self.current_mode)
        self.detector = FaultDetector()
        self.retriever = TFIDFRetriever()
        self.llm = LocalLLMClient()
        self.latest_reading = None
        self.history = []  # last 60 readings for charts
        self.latest_diagnosis = None
        self.diagnoses_history = []
        self.is_running = True
        self.last_diagnosis_time = 0.0
        self.cooldown = 4.0
        self.sse_clients = []

        # Preload historical sensor readings and diagnoses from database
        self._load_existing_readings()
        self._load_existing_diagnoses()

    def _load_existing_readings(self):
        """Preload recent sensor readings from PostgreSQL into chart history."""
        try:
            if is_database_available():
                db_readings = get_recent_sensor_readings(limit=60, chronological=True)
                if db_readings:
                    with self.lock:
                        self.history = [
                            {
                                "device_id": r.get("device_id", "pump_centrifugal_01"),
                                "timestamp": r.get("timestamp"),
                                "temperature": float(r.get("temperature", 0.0)),
                                "vibration": float(r.get("vibration", 0.0)),
                                "pressure": float(r.get("pressure", 0.0)),
                                "mode": r.get("mode", "normal"),
                                "fault_status": r.get("fault_status", "normal"),
                            }
                            for r in db_readings
                        ]
                        self.latest_reading = self.history[-1]
                    logger.info(f"Loaded {len(self.history)} sensor readings from PostgreSQL database.")
        except Exception as e:
            logger.warning(f"Error querying PostgreSQL for initial sensor readings: {e}")

    def _load_existing_diagnoses(self):
        # 1. Attempt to load from PostgreSQL persistence layer
        try:
            if is_database_available():
                db_diagnoses = get_recent_diagnoses(limit=50, chronological=True)
                if db_diagnoses:
                    self.diagnoses_history = db_diagnoses
                    self.latest_diagnosis = self.diagnoses_history[-1]
                    logger.info(f"Loaded {len(self.diagnoses_history)} diagnoses from PostgreSQL database.")
                    return
        except Exception as e:
            logger.warning(f"Error querying PostgreSQL for diagnoses: {e}")

        # 2. Fallback to local JSONL log
        log_file = DATA_DIR / "diagnoses_log.jsonl"
        if log_file.exists():
            try:
                lines = log_file.read_text(encoding="utf-8").strip().split("\n")
                for line in lines[-50:]:
                    if line.strip():
                        self.diagnoses_history.append(json.loads(line))
                if self.diagnoses_history:
                    self.latest_diagnosis = self.diagnoses_history[-1]
                logger.info(f"Loaded {len(self.diagnoses_history)} diagnoses from local JSONL fallback.")
            except Exception as e:
                logger.warning(f"Error loading existing diagnoses from JSONL: {e}")

    def set_mode(self, mode, submode="flatline"):
        with self.lock:
            self.current_mode = mode
            self.sensor_submode = submode
            self.simulator = PumpTelemetrySimulator(mode=mode, sensor_failure_type=submode)
            logger.info(f"Switched simulator mode to '{mode}' (submode='{submode}')")

    def add_reading(self, reading):
        with self.lock:
            self.latest_reading = reading
            self.history.append(reading)
            if len(self.history) > 60:
                self.history.pop(0)

            # Check for faults
            detection = self.detector.process_reading(reading)
            if detection is not None:
                now = time.time()
                if now - self.last_diagnosis_time >= self.cooldown:
                    self.last_diagnosis_time = now
                    # Run diagnosis in background thread so telemetry loop isn't delayed
                    threading.Thread(
                        target=self._run_diagnosis_task,
                        args=(detection, reading),
                        daemon=True,
                    ).start()
            return detection

    def _run_diagnosis_task(self, detection, reading):
        category = detection.get("fault_category", "unknown")
        query = detection.get("query", "")
        logger.info(f"Fault detected: {category}. Retrieving knowledge...")
        chunks = self.retriever.retrieve(query, top_k=3)
        diagnosis_result = self.llm.generate(detection, chunks)

        record = {
            "timestamp": reading.get("timestamp"),
            "device_id": reading.get("device_id"),
            "fault_category": category,
            "symptoms": detection.get("symptoms", []),
            "readings": {
                "temperature": reading.get("temperature"),
                "vibration": reading.get("vibration"),
                "pressure": reading.get("pressure"),
            },
            "retrieved_sources": [
                {
                    "source": c.get("source_file"),
                    "section": c.get("section_title"),
                    "score": c.get("score"),
                }
                for c in chunks
            ],
            "diagnosis_text": diagnosis_result.get("response"),
            "sections": diagnosis_result.get("sections", {}),
            "runtime": diagnosis_result.get("runtime"),
            "latency_seconds": diagnosis_result.get("latency_seconds"),
        }

        with self.lock:
            self.latest_diagnosis = record
            self.diagnoses_history.append(record)
            if len(self.diagnoses_history) > 50:
                self.diagnoses_history.pop(0)

            # Persist to local JSONL for file backup
            try:
                DATA_DIR.mkdir(parents=True, exist_ok=True)
                log_file = DATA_DIR / "diagnoses_log.jsonl"
                with open(log_file, "a", encoding="utf-8") as f:
                    f.write(json.dumps(record) + "\n")
            except Exception as fe:
                logger.warning(f"Error writing diagnosis to JSONL: {fe}")

        # Persist to PostgreSQL database (graceful fallback if offline)
        try:
            insert_diagnosis(record)
        except Exception as dbe:
            logger.warning(f"Error persisting diagnosis to database: {dbe}")

        # Broadcast via SSE
        self.notify_sse("diagnosis", record)

    def notify_sse(self, event_type, data):
        dead_clients = []
        msg = f"event: {event_type}\ndata: {json.dumps(data)}\n\n".encode("utf-8")
        with self.lock:
            for client in self.sse_clients:
                try:
                    client.wfile.write(msg)
                    client.wfile.flush()
                except Exception:
                    dead_clients.append(client)
            for c in dead_clients:
                if c in self.sse_clients:
                    self.sse_clients.remove(c)


state = DashboardState()


def telemetry_producer():
    """Background thread generating live sensor telemetry and publishing via MQTT."""
    logger.info("Starting telemetry producer...")
    mqtt_client = None
    try:
        mqtt_client = mqtt.Client(
            callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
            client_id="dashboard_live_producer",
        )
        mqtt_client.connect(MQTT_BROKER_HOST, MQTT_BROKER_PORT, keepalive=60)
        mqtt_client.loop_start()
        logger.info(f"Connected live MQTT producer to {MQTT_BROKER_HOST}:{MQTT_BROKER_PORT}")
    except Exception as e:
        logger.warning(f"Could not connect live MQTT publisher: {e}. Running local loop.")

    while state.is_running:
        try:
            reading = state.simulator.step()
            detection = state.add_reading(reading)

            if mqtt_client and mqtt_client.is_connected():
                mqtt_client.publish(MQTT_TELEMETRY_TOPIC, json.dumps(reading), qos=0)

            # Enqueue reading for background PostgreSQL persistence
            # put_nowait() guarantees 1 Hz loop never blocks; drops reading if queue is full
            try:
                reading_with_mode = dict(reading)
                reading_with_mode["mode"] = state.current_mode
                fault_status = "normal"
                if detection is not None and detection.get("has_fault", True):
                    fault_status = detection.get("fault_category", state.current_mode)
                reading_with_mode["fault_status"] = fault_status
                telemetry_queue.put_nowait(reading_with_mode)
            except queue.Full:
                logger.warning("Telemetry persistence queue is full; dropping reading to maintain 1 Hz loop.")
            except Exception as qe:
                logger.warning(f"Error enqueueing telemetry: {qe}")

            # Stream reading to SSE clients
            state.notify_sse("telemetry", {
                "latest": reading,
                "mode": state.current_mode,
                "history_length": len(state.history),
            })
        except Exception as e:
            logger.error(f"Error in telemetry producer: {e}")
        time.sleep(1.0)

    if mqtt_client:
        mqtt_client.loop_stop()
        mqtt_client.disconnect()


def telemetry_db_writer_worker():
    """Background worker consuming telemetry queue and writing batches to PostgreSQL.

    Retention Policy:
    - Calls prune_old_sensor_readings(TELEMETRY_RETENTION_DAYS) once at startup.
    - Calls prune_old_sensor_readings(TELEMETRY_RETENTION_DAYS) periodically once per hour (3600 seconds).
    """
    logger.info("Starting background telemetry database writer...")
    last_prune_time = 0.0
    prune_interval = 3600.0  # 1 hour

    # Prune old sensor readings at startup
    try:
        prune_old_sensor_readings(TELEMETRY_RETENTION_DAYS)
        last_prune_time = time.time()
    except Exception as e:
        logger.warning(f"Startup telemetry pruning failed: {e}")

    batch = []
    last_flush_time = time.time()

    while state.is_running:
        try:
            # Check if 1 hour has elapsed since last prune
            now = time.time()
            if now - last_prune_time >= prune_interval:
                try:
                    prune_old_sensor_readings(TELEMETRY_RETENTION_DAYS)
                    last_prune_time = now
                except Exception as pe:
                    logger.warning(f"Hourly telemetry pruning failed: {pe}")

            # Pull reading from queue (short timeout so loop checks status frequently)
            try:
                item = telemetry_queue.get(timeout=0.5)
                batch.append(item)
            except queue.Empty:
                pass

            # Flush batch if batch size reached or flush interval elapsed
            now = time.time()
            if len(batch) >= TELEMETRY_BATCH_SIZE or (batch and (now - last_flush_time) >= TELEMETRY_BATCH_FLUSH_INTERVAL):
                try:
                    insert_sensor_readings_batch(batch)
                except Exception as be:
                    logger.warning(f"Error writing sensor readings batch to PostgreSQL: {be}")
                batch = []
                last_flush_time = now

        except Exception as e:
            logger.error(f"Error in telemetry DB writer worker: {e}")
            time.sleep(1.0)


class DashboardHTTPHandler(http.server.SimpleHTTPRequestHandler):
    """HTTP Request Handler serving API and frontend assets."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(STATIC_DIR), **kwargs)

    def end_headers(self):
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)

        if parsed.path == "/api/status":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            db_stats = get_db_stats()
            with state.lock:
                status_data = {
                    "mode": state.current_mode,
                    "submode": state.sensor_submode,
                    "latest_reading": state.latest_reading,
                    "history": state.history,
                    "latest_diagnosis": state.latest_diagnosis,
                    "total_diagnoses": len(state.diagnoses_history),
                    "llm_runtime": "Ollama / Grounded RAG Fallback",
                    "database": db_stats,
                    "dataset": {
                        "name": "UCI AI4I 2020 Predictive Maintenance Dataset",
                        "records": 10000,
                        "ml_model": "RandomForest (Physics Features)",
                        "accuracy": 0.9985,
                        "roc_auc": 0.9984,
                        "failure_modes": ["TWF", "HDF", "PWF", "OSF", "RNF"],
                    },
                }
            self.wfile.write(json.dumps(status_data).encode("utf-8"))

        elif parsed.path == "/api/dataset":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            db_stats = get_db_stats()
            dataset_info = {
                "dataset_name": "UCI AI4I 2020 Predictive Maintenance Dataset",
                "source": "data/ai4i2020.csv",
                "total_records": 10000,
                "nominal_samples": 9661,
                "failure_samples": 339,
                "features": [
                    "Air temperature [K]",
                    "Process temperature [K]",
                    "Rotational speed [rpm]",
                    "Torque [Nm]",
                    "Tool wear [min]",
                ],
                "engineered_features": [
                    {"name": "temp_diff_k", "formula": "Process Temp - Air Temp"},
                    {"name": "rotational_power_w", "formula": "Torque * (RPM * 2 * pi / 60)"},
                    {"name": "overstrain_risk", "formula": "Tool Wear * Torque"},
                ],
                "model": {
                    "type": "RandomForestClassifier",
                    "path": "data/ai4i_model.joblib",
                    "accuracy": 0.9985,
                    "precision": 0.985,
                    "recall": 0.971,
                    "roc_auc": 0.9984,
                },
                "physical_mapping": {
                    "stator_overheating": "Heat Dissipation Failure (HDF) - Temp > 75°C",
                    "bearing_wear": "Tool Wear Failure (TWF) - Vib > 4.5 mm/s",
                    "pressure_drop": "Power Failure (PWF) - Pressure < 3.0 bar",
                    "sensor_disconnect": "Sensor Out-of-bounds (-999°C)",
                    "sensor_flatline": "ADC Zero-Variance Freeze",
                },
                "database": db_stats,
            }
            self.wfile.write(json.dumps(dataset_info).encode("utf-8"))

        elif parsed.path == "/api/diagnoses":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            with state.lock:
                history_data = list(reversed(state.diagnoses_history))
            self.wfile.write(json.dumps(history_data).encode("utf-8"))

        elif parsed.path == "/api/readings":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            query_params = parse_qs(parsed.query)
            limit = int(query_params.get("limit", [60])[0])
            readings = get_recent_sensor_readings(limit=limit, chronological=True)
            if not readings:
                with state.lock:
                    readings = list(state.history)
            self.wfile.write(json.dumps(readings).encode("utf-8"))

        elif parsed.path == "/api/stream":
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Connection", "keep-alive")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()

            with state.lock:
                state.sse_clients.append(self)

            # Send initial sync
            with state.lock:
                init_data = {
                    "mode": state.current_mode,
                    "submode": state.sensor_submode,
                    "latest_reading": state.latest_reading,
                    "history": state.history,
                    "latest_diagnosis": state.latest_diagnosis,
                }
            init_msg = f"event: init\ndata: {json.dumps(init_data)}\n\n".encode("utf-8")
            self.wfile.write(init_msg)
            self.wfile.flush()

            # Keep connection open until client disconnects
            try:
                while state.is_running:
                    time.sleep(10.0)
                    self.wfile.write(b": keepalive\n\n")
                    self.wfile.flush()
            except Exception:
                pass
            finally:
                with state.lock:
                    if self in state.sse_clients:
                        state.sse_clients.remove(self)

        else:
            # Fall back to static file serving
            super().do_GET()

    def do_POST(self):
        parsed = urlparse(self.path)

        if parsed.path == "/api/mode":
            content_length = int(self.headers.get("Content-Length", 0))
            post_body = self.rfile.read(content_length).decode("utf-8")
            try:
                data = json.loads(post_body)
                mode = data.get("mode", FAULT_MODE_NORMAL)
                submode = data.get("submode", "flatline")
                state.set_mode(mode, submode)

                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.send_header("Access-Control-Allow-Headers", "Content-Type")
                self.end_headers()
                self.wfile.write(json.dumps({"status": "ok", "mode": mode, "submode": submode}).encode("utf-8"))
            except Exception as e:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()


class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    allow_reuse_address = True
    daemon_threads = True


def start_server(port=PORT):
    producer_thread = threading.Thread(target=telemetry_producer, daemon=True)
    producer_thread.start()

    db_writer_thread = threading.Thread(target=telemetry_db_writer_worker, daemon=True)
    db_writer_thread.start()

    server = ThreadedTCPServer(("0.0.0.0", port), DashboardHTTPHandler)
    logger.info(f"Dashboard SCADA web interface running at http://localhost:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        state.is_running = False
        server.shutdown()


if __name__ == "__main__":
    start_server(PORT)
