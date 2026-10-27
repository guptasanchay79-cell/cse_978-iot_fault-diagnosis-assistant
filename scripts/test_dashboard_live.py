"""Test script to verify dashboard server HTTP endpoints and live PostgreSQL integration."""

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

from dashboard.app import DashboardHTTPHandler, ThreadedTCPServer, state

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] TestDashboard: %(message)s")
logger = logging.getLogger("TestDashboard")

PORT = 8089  # Use 8089 for test to avoid collision with port 8080 if running


def run_dashboard_test():
    server = ThreadedTCPServer(("127.0.0.1", PORT), DashboardHTTPHandler)
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()
    logger.info(f"Test server started on http://127.0.0.1:{PORT}")
    time.sleep(1.0)

    try:
        # 1. Test /api/status
        req = urllib.request.urlopen(f"http://127.0.0.1:{PORT}/api/status")
        assert req.status == 200
        data = json.loads(req.read().decode("utf-8"))
        logger.info(f"/api/status response: mode={data.get('mode')}, DB connected={data.get('database', {}).get('connected')}, DB={data.get('database', {}).get('database')}")
        assert data["database"]["connected"] is True
        assert data["database"]["database"] == "iot_fault_diagnosis"

        # 2. Test /api/readings
        req = urllib.request.urlopen(f"http://127.0.0.1:{PORT}/api/readings?limit=10")
        assert req.status == 200
        readings = json.loads(req.read().decode("utf-8"))
        logger.info(f"/api/readings returned {len(readings)} items")

        # 3. Test /api/diagnoses
        req = urllib.request.urlopen(f"http://127.0.0.1:{PORT}/api/diagnoses")
        assert req.status == 200
        diagnoses = json.loads(req.read().decode("utf-8"))
        logger.info(f"/api/diagnoses returned {len(diagnoses)} items")

        # 4. Test index.html
        req = urllib.request.urlopen(f"http://127.0.0.1:{PORT}/index.html")
        assert req.status == 200
        html = req.read().decode("utf-8")
        assert "IoT Fault Diagnosis Assistant" in html
        assert "iot_fault_diagnosis" in html
        logger.info("index.html loaded successfully with updated database schema!")

        logger.info("ALL DASHBOARD ENDPOINT TESTS PASSED!")
        return True
    finally:
        state.is_running = False
        server.shutdown()
        server.server_close()
        logger.info("Test server shutdown.")


if __name__ == "__main__":
    if not run_dashboard_test():
        sys.exit(1)
