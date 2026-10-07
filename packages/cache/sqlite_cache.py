import json
import logging
import sqlite3
import time
from pathlib import Path
from typing import Any, Dict, Optional
from packages.cache.base import BaseLLMCache

logger = logging.getLogger(__name__)


class SQLiteLLMCache(BaseLLMCache):
    """
    SQLite-backed cache for deterministic LLM calls with TTL and invalidation.
    Thread-safe and persistent across process restarts.
    """

    def __init__(self, db_path: str = "artifacts/cache/llm_cache.sqlite", default_ttl_seconds: int = 86400):
        self.db_path = db_path
        self.default_ttl = default_ttl_seconds
        self._shared_conn: Optional[sqlite3.Connection] = None

        if self.db_path == ":memory:":
            self._shared_conn = sqlite3.connect(":memory:", timeout=10.0, check_same_thread=False)
            self._shared_conn.row_factory = sqlite3.Row

        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        if self._shared_conn is not None:
            return self._shared_conn
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.db_path, timeout=10.0)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        conn = self._get_connection()
        with conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS llm_cache (
                    cache_key TEXT PRIMARY KEY,
                    value_json TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    expires_at REAL NOT NULL
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_llm_cache_expires_at ON llm_cache (expires_at)
            """)
        if self._shared_conn is None:
            conn.close()

    def get(self, key: str) -> Optional[Dict[str, Any]]:
        now = time.time()
        conn = self._get_connection()
        try:
            cursor = conn.execute(
                "SELECT value_json, expires_at FROM llm_cache WHERE cache_key = ?",
                (key,)
            )
            row = cursor.fetchone()
            if not row:
                return None

            expires_at = row["expires_at"]
            if expires_at < now:
                # Expired: clean up entry
                with conn:
                    conn.execute("DELETE FROM llm_cache WHERE cache_key = ?", (key,))
                return None

            try:
                return json.loads(row["value_json"])
            except Exception as e:
                logger.error(f"Failed to deserialize cached json for key {key}: {e}")
                return None
        finally:
            if self._shared_conn is None:
                conn.close()

    def set(self, key: str, value: Dict[str, Any], ttl_seconds: Optional[int] = None) -> None:
        now = time.time()
        ttl = ttl_seconds if ttl_seconds is not None else self.default_ttl
        expires_at = now + ttl
        value_json = json.dumps(value, ensure_ascii=False)

        conn = self._get_connection()
        try:
            with conn:
                conn.execute("""
                    INSERT INTO llm_cache (cache_key, value_json, created_at, expires_at)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(cache_key) DO UPDATE SET
                        value_json = excluded.value_json,
                        created_at = excluded.created_at,
                        expires_at = excluded.expires_at
                """, (key, value_json, now, expires_at))
        finally:
            if self._shared_conn is None:
                conn.close()

    def invalidate(self, key: str) -> bool:
        conn = self._get_connection()
        try:
            with conn:
                cursor = conn.execute("DELETE FROM llm_cache WHERE cache_key = ?", (key,))
                return cursor.rowcount > 0
        finally:
            if self._shared_conn is None:
                conn.close()

    def clear(self) -> None:
        conn = self._get_connection()
        try:
            with conn:
                conn.execute("DELETE FROM llm_cache")
        finally:
            if self._shared_conn is None:
                conn.close()
