"""P_311: Knowledge-Driven IoT Fault Diagnosis Assistant.

Migration utility script:
Imports historical diagnoses from data/diagnoses_log.jsonl into PostgreSQL persistence table (fault_incidents).
"""

import json
import logging
from pathlib import Path
import sys
import time

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from config import DATA_DIR
from db.connection import is_database_available
from db.repository import insert_diagnosis

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] ImportJSONL: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    stream=sys.stdout,
)
logger = logging.getLogger("ImportJSONL")


def import_jsonl_to_db(jsonl_path: Path = DATA_DIR / "diagnoses_log.jsonl") -> None:
    """Read jsonl file and import records into fault_incidents table."""
    if not jsonl_path.exists():
        logger.error(f"JSONL file not found at: {jsonl_path}")
        return

    logger.info("Checking PostgreSQL database availability...")
    if not is_database_available(force_check=True):
        logger.error("PostgreSQL database is currently unavailable. Ensure Docker container is running.")
        return

    logger.info(f"Reading records from {jsonl_path}...")
    lines = jsonl_path.read_text(encoding="utf-8").strip().split("\n")
    valid_records = []
    for idx, line in enumerate(lines, start=1):
        line = line.strip()
        if not line:
            continue
        try:
            record = json.loads(line)
            valid_records.append(record)
        except json.JSONDecodeError as e:
            logger.warning(f"Skipping malformed JSON line {idx}: {e}")

    total = len(valid_records)
    logger.info(f"Found {total} valid records to import.")

    inserted = 0
    t0 = time.time()
    for r in valid_records:
        if insert_diagnosis(r):
            inserted += 1

    elapsed = round(time.time() - t0, 3)
    logger.info(f"Import complete: {inserted}/{total} records processed into PostgreSQL in {elapsed}s.")


if __name__ == "__main__":
    import_jsonl_to_db()
