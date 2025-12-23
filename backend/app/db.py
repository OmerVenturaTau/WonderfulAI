import logging
import os
from typing import Any, Dict, List, Optional, Tuple

import psycopg2
from psycopg2.extras import RealDictCursor

logger = logging.getLogger("wonderful.db")

# PostgreSQL configuration (container-only; no SQLite fallback)
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "db")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")
POSTGRES_DB = os.getenv("POSTGRES_DB", "pharmacy")
POSTGRES_USER = os.getenv("POSTGRES_USER", "pharmacy_user")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "pharmacy_pass")


def get_conn():
    """Get PostgreSQL connection. Surface connection errors to caller."""
    try:
        conn = psycopg2.connect(
            host=POSTGRES_HOST,
            port=POSTGRES_PORT,
            database=POSTGRES_DB,
            user=POSTGRES_USER,
            password=POSTGRES_PASSWORD,
            cursor_factory=RealDictCursor,
        )
        logger.debug("Opened DB connection to %s:%s/%s", POSTGRES_HOST, POSTGRES_PORT, POSTGRES_DB)
        return conn
    except Exception as e:
        logger.exception("Database connection failed")
        # Present connection errors explicitly
        raise RuntimeError(f"Database connection failed: {e}")


def _row_to_dict(row: Any) -> Dict[str, Any]:
    """Convert database row to dictionary."""
    return dict(row) if hasattr(row, "keys") else row


def query_one(sql: str, params: Tuple[Any, ...] = ()) -> Optional[Dict[str, Any]]:
    """Execute query and return first row as dict."""
    logger.debug("query_one: %s params=%s", sql.strip().splitlines()[0], params)
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(sql, params)
        row = cur.fetchone()
        cur.close()
        return _row_to_dict(row) if row else None


def query_all(sql: str, params: Tuple[Any, ...] = ()) -> List[Dict[str, Any]]:
    """Execute query and return all rows as list of dicts."""
    logger.debug("query_all: %s params=%s", sql.strip().splitlines()[0], params)
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(sql, params)
        rows = cur.fetchall()
        cur.close()
        return [_row_to_dict(r) for r in rows]


def exec_sql(sql: str, params: Tuple[Any, ...] = ()) -> None:
    """Execute SQL statement (INSERT, UPDATE, DELETE)."""
    logger.debug("exec_sql: %s params=%s", sql.strip().splitlines()[0], params)
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(sql, params)
        conn.commit()
        cur.close()
