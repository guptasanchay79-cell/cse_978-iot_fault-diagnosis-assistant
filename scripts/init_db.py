"""P_311: Knowledge-Driven IoT Fault Diagnosis Assistant.

Database Initialization Script for Windows PostgreSQL:
1. Connects to PostgreSQL server using credentials from .env.
2. Creates the project database if it does not already exist.
3. Applies db/init.sql to create tables, indexes, constraints, and functions.
"""

import logging
from pathlib import Path
import sys

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import psycopg
from psycopg import sql

from config import (
    POSTGRES_DB,
    POSTGRES_HOST,
    POSTGRES_PASSWORD,
    POSTGRES_PORT,
    POSTGRES_USER,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] DBInit: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    stream=sys.stdout,
)
logger = logging.getLogger("DBInit")


def initialize_database() -> bool:
    """Create database and apply schema."""
    logger.info(f"Connecting to PostgreSQL at {POSTGRES_HOST}:{POSTGRES_PORT} as user '{POSTGRES_USER}'...")

    # 1. Connect to maintenance DB (postgres) with autocommit=True to check/create target database
    try:
        conn = psycopg.connect(
            host=POSTGRES_HOST,
            port=POSTGRES_PORT,
            user=POSTGRES_USER,
            password=POSTGRES_PASSWORD,
            dbname="postgres",
            autocommit=True,
            connect_timeout=5,
        )
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM pg_database WHERE datname = %s;", (POSTGRES_DB,))
            exists = cur.fetchone()
            if not exists:
                logger.info(f"Database '{POSTGRES_DB}' does not exist. Creating database...")
                cur.execute(sql.SQL("CREATE DATABASE {};").format(sql.Identifier(POSTGRES_DB)))
                logger.info(f"Database '{POSTGRES_DB}' successfully created.")
            else:
                logger.info(f"Database '{POSTGRES_DB}' already exists.")
        conn.close()
    except Exception as e:
        logger.error(f"Failed to connect or create database '{POSTGRES_DB}': {e}")
        return False

    # 2. Connect to target database and apply schema
    init_sql_path = _PROJECT_ROOT / "db" / "init.sql"
    if not init_sql_path.exists():
        logger.error(f"Schema file not found at: {init_sql_path}")
        return False

    schema_sql = init_sql_path.read_text(encoding="utf-8")
    try:
        conn = psycopg.connect(
            host=POSTGRES_HOST,
            port=POSTGRES_PORT,
            user=POSTGRES_USER,
            password=POSTGRES_PASSWORD,
            dbname=POSTGRES_DB,
            autocommit=True,
            connect_timeout=5,
        )
        with conn.cursor() as cur:
            logger.info("Applying db/init.sql schema...")
            cur.execute(schema_sql)
            logger.info("Schema applied successfully.")

            # Verify tables
            cur.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                ORDER BY table_name;
            """)
            tables = [row[0] for row in cur.fetchall()]
            logger.info(f"Active tables in '{POSTGRES_DB}': {tables}")

        conn.close()
        return True
    except Exception as e:
        logger.error(f"Failed to apply schema to '{POSTGRES_DB}': {e}")
        return False


if __name__ == "__main__":
    success = initialize_database()
    if not success:
        sys.exit(1)
