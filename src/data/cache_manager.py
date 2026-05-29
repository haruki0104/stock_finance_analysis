import sqlite3
from datetime import datetime, timedelta
from io import StringIO

import pandas as pd
from loguru import logger

from src.config import CACHE_DB_PATH


def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(str(CACHE_DB_PATH))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA cache_size=-64000")
    return conn


def init_db():
    conn = _get_conn()
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS cache (
            dataset TEXT NOT NULL,
            data_id TEXT NOT NULL DEFAULT '',
            start_date TEXT NOT NULL DEFAULT '',
            end_date TEXT NOT NULL DEFAULT '',
            data TEXT,
            fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (dataset, data_id, start_date, end_date)
        );
        CREATE INDEX IF NOT EXISTS idx_cache_expiry ON cache(fetched_at);
        """
    )
    conn.commit()
    conn.close()


def get_cached(
    dataset: str,
    data_id: str = "",
    start_date: str = "",
    end_date: str = "",
    max_age_days: int = 1,
) -> pd.DataFrame | None:
    init_db()
    conn = _get_conn()
    cutoff = (datetime.now() - timedelta(days=max_age_days)).isoformat()
    row = conn.execute(
        """SELECT data FROM cache
           WHERE dataset=? AND data_id=? AND start_date=? AND end_date=?
             AND fetched_at > ?""",
        (dataset, data_id, start_date, end_date, cutoff),
    ).fetchone()
    conn.close()
    if row and row[0]:
        try:
            return pd.read_json(StringIO(row[0]), orient="split")
        except Exception as e:
            logger.warning(f"Cache deserialize error: {e}")
    return None


def set_cache(
    dataset: str,
    df: pd.DataFrame,
    data_id: str = "",
    start_date: str = "",
    end_date: str = "",
):
    init_db()
    conn = _get_conn()
    blob = df.to_json(orient="split", date_format="iso")
    conn.execute(
        """INSERT OR REPLACE INTO cache
           (dataset, data_id, start_date, end_date, data, fetched_at)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (dataset, data_id, start_date, end_date, blob, datetime.now().isoformat()),
    )
    conn.commit()
    conn.close()


def clear_cache(dataset: str = None):
    init_db()
    conn = _get_conn()
    if dataset:
        conn.execute("DELETE FROM cache WHERE dataset=?", (dataset,))
    else:
        conn.execute("DELETE FROM cache")
    conn.commit()
    conn.close()
    logger.info(f"Cache cleared {'for ' + dataset if dataset else 'all'}")
