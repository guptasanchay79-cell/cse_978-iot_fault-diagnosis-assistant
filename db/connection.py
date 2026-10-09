"""P_311: Knowledge-Driven IoT Fault Diagnosis Assistant.

Database connection manager for PostgreSQL persistence layer.
Handles connections, circuit breaking for offline Docker states, and health checks.
"""

from contextlib import contextmanager
import logging
import time
from typing import Generator, Optional

import psycopg
from psycopg.rows import dict_row

from config import (
    DB_CONNECT_TIMEOUT_SECONDS,
    POSTGRES_DB,
    POSTGRES_HOST,
    POSTGRES_PASSWORD,
    POSTGRES_PORT,
    POSTGRES_USER,
)

logger = logging.getLogger("DatabaseConnection")

# Circuit breaker state to prevent blocking HTTP requests when Docker is offline
_DB_AVAILABLE: Optional[bool] = None
_LAST_CHECK_TIME: float = 0.0
_CHECK_COOLDOWN_SECONDS: float = 5.0


def get_connection_params() -> dict:
    """Return dictionary of connection parameters."""
    return {
        "host": POSTGRES_HOST,
        "port": POSTGRES_PORT,
        "dbname": POSTGRES_DB,
        "user": POSTGRES_USER,
        "password": POSTGRES_PASSWORD,
        "connect_timeout": DB_CONNECT_TIMEOUT_SECONDS,
    }


def is_database_available(force_check: bool = False) -> bool:
    """Check if PostgreSQL database is reachable.
    
    Caches result for 5 seconds to avoid repeated connection timeout delays
    when Docker is offline.
    """
    global _DB_AVAILABLE, _LAST_CHECK_TIME
    now = time.time()

    if not force_check and _DB_AVAILABLE is not None and (now - _LAST_CHECK_TIME) < _CHECK_COOLDOWN_SECONDS:
        return _DB_AVAILABLE

    try:
        params = get_connection_params()
        with psycopg.connect(**params) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1;")
                cur.fetchone()
        _DB_AVAILABLE = True
        _LAST_CHECK_TIME = now
        return True
    except Exception as e:
        if _DB_AVAILABLE is not False:
            logger.warning(
                f"PostgreSQL database is currently unavailable ({e}). "
                "Operating in in-memory / JSONL fallback mode."
            )
        _DB_AVAILABLE = False
        _LAST_CHECK_TIME = now
        return False


@contextmanager
def get_db_connection(timeout: int = DB_CONNECT_TIMEOUT_SECONDS) -> Generator[psycopg.Connection, None, None]:
    """Context manager providing a transactional psycopg connection.
    
    Automatically commits on normal exit, rolls back on exception,
    and closes the connection.
    """
    params = get_connection_params()
    params["connect_timeout"] = timeout
    conn = None
    try:
        conn = psycopg.connect(**params, row_factory=dict_row)
        yield conn
        conn.commit()
    except Exception:
        if conn is not None and not conn.closed:
            try:
                conn.rollback()
            except Exception:
                pass
        raise
    finally:
        if conn is not None and not conn.closed:
            try:
                conn.close()
            except Exception:
                pass
