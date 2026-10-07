import os
import sqlite3
import logging
from typing import Optional
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import MemorySaver

logger = logging.getLogger(__name__)


def get_checkpointer(
    checkpointer_type: Optional[str] = None,
    conn_string: Optional[str] = None
) -> BaseCheckpointSaver:
    """
    Factory creating a durable or testing LangGraph checkpointer.
    - 'postgres': PostgresSaver initialized with schema migrations setup()
    - 'sqlite': SqliteSaver backed by sqlite3 file with schema setup()
    - 'memory': MemorySaver for test isolation
    """
    ctype: str = (checkpointer_type or os.getenv("CHECKPOINTER_TYPE") or "").lower()
    raw_db_url: str = conn_string or os.getenv("DATABASE_URL") or ""

    if ctype == "memory":
        return MemorySaver()

    if ctype == "postgres" or (not ctype and ("postgresql" in raw_db_url or "postgres" in raw_db_url)):
        try:
            import psycopg
            from langgraph.checkpoint.postgres import PostgresSaver

            pg_url = raw_db_url
            if "+psycopg" in pg_url:
                pg_url = pg_url.split("+")[0] + "://" + pg_url.split("://")[1]

            conn = psycopg.connect(pg_url, autocommit=True)
            saver = PostgresSaver(conn)
            saver.setup()
            return saver
        except Exception as e:
            logger.warning(f"Failed to initialize PostgresSaver ({e}), falling back")

    if ctype == "sqlite" or (not ctype and "sqlite" in raw_db_url) or (conn_string and not conn_string.startswith("postgres")):
        try:
            from langgraph.checkpoint.sqlite import SqliteSaver
            db_path = conn_string or raw_db_url.replace("sqlite:///", "") or "storage/checkpoints/langgraph.db"
            parent = os.path.dirname(os.path.abspath(db_path))
            if parent:
                os.makedirs(parent, exist_ok=True)
            conn = sqlite3.connect(db_path, check_same_thread=False)
            saver = SqliteSaver(conn)
            saver.setup()
            return saver
        except Exception as e:
            logger.warning(f"Failed to initialize SqliteSaver ({e}), falling back to Memory")

    return MemorySaver()
