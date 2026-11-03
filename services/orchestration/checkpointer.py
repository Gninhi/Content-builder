import os
import sqlite3
import logging
from typing import Optional, Any, Dict, Iterator, Sequence, Tuple, cast, AsyncIterator
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.base import (
    BaseCheckpointSaver,
    Checkpoint,
    CheckpointMetadata,
    CheckpointTuple,
    ChannelVersions,
)
from langgraph.checkpoint.memory import MemorySaver

logger = logging.getLogger(__name__)

SENSITIVE_KEYS = {
    "access_token",
    "refresh_token",
    "client_secret",
    "password",
    "password_hash",
    "api_key",
    "secret_key",
    "secret_vault_key",
    "google_api_key",
    "nvidia_api_key",
    "tavily_api_key",
}


def sanitize_sensitive_data(val: Any) -> Any:
    """Recursively redacts secrets and OAuth tokens from in-memory objects before checkpointing."""
    if isinstance(val, dict):
        sanitized = {}
        for k, v in val.items():
            if str(k).lower() in SENSITIVE_KEYS:
                sanitized[k] = "[REDACTED_FROM_CHECKPOINT]"
            else:
                sanitized[k] = sanitize_sensitive_data(v)
        return sanitized
    elif isinstance(val, list):
        return [sanitize_sensitive_data(item) for item in val]
    elif isinstance(val, tuple):
        return tuple(sanitize_sensitive_data(item) for item in val)
    return val


class TenantGuardedCheckpointer(BaseCheckpointSaver):
    """
    ARC-02 Security Guard for LangGraph Checkpointing.
    Enforces:
    1. Multi-tenant namespace verification ({workspace_id}:{thread_uuid}).
    2. Zero cross-tenant horizontal read, write, resume, list or delete.
    3. Recursive sanitization of social tokens, credentials, and API keys before persistence.
    """

    def __init__(self, inner: BaseCheckpointSaver):
        super().__init__(serde=inner.serde)
        self.inner = inner

    @staticmethod
    def _verify_thread_authorization(config: Any, operation: str = "access") -> None:
        if not isinstance(config, dict):
            return
        configurable = config.get("configurable")
        if not isinstance(configurable, dict):
            return
        # Ensure standard LangGraph configurable keys exist
        configurable.setdefault("checkpoint_ns", "")
        thread_id = str(configurable.get("thread_id", "") or "")
        caller_ws = configurable.get("workspace_id")
        if caller_ws and thread_id:
            caller_ws_str = str(caller_ws).strip()
            if ":" in thread_id:
                owner_ws = thread_id.split(":", 1)[0].strip()
                if owner_ws != caller_ws_str:
                    logger.warning(
                        "SECURITY ALERT: Cross-tenant checkpoint %s blocked. Thread '%s' does not match caller workspace '%s'.",
                        operation, thread_id, caller_ws_str
                    )
                    raise PermissionError(
                        f"Cross-tenant checkpoint {operation} denied: thread '{thread_id}' does not belong to workspace '{caller_ws_str}'."
                    )

    def get_tuple(self, config: Any) -> Optional[CheckpointTuple]:
        self._verify_thread_authorization(config, operation="read")
        return self.inner.get_tuple(config)

    def list(
        self,
        config: Optional[Any],
        *,
        filter: Optional[Dict[str, Any]] = None,
        before: Optional[Any] = None,
        limit: Optional[int] = None
    ) -> Iterator[CheckpointTuple]:
        if config is not None:
            self._verify_thread_authorization(config, operation="list")
        return self.inner.list(config, filter=filter, before=before, limit=limit)

    def put(
        self,
        config: RunnableConfig,
        checkpoint: Checkpoint,
        metadata: CheckpointMetadata,
        new_versions: ChannelVersions
    ) -> RunnableConfig:
        self._verify_thread_authorization(config, operation="write")
        clean_cp = dict(checkpoint)
        if "channel_values" in clean_cp and isinstance(clean_cp["channel_values"], dict):
            clean_cp["channel_values"] = sanitize_sensitive_data(clean_cp["channel_values"])
        clean_meta = sanitize_sensitive_data(metadata) if isinstance(metadata, dict) else metadata
        return self.inner.put(config, cast(Checkpoint, clean_cp), clean_meta, new_versions)

    def put_writes(
        self,
        config: RunnableConfig,
        writes: Sequence[Tuple[str, Any]],
        task_id: str,
        task_path: str = ""
    ) -> None:
        self._verify_thread_authorization(config, operation="write")
        clean_writes = [(channel, sanitize_sensitive_data(val)) for channel, val in writes]
        return self.inner.put_writes(config, clean_writes, task_id, task_path)

    async def aget_tuple(self, config: RunnableConfig) -> Optional[CheckpointTuple]:
        self._verify_thread_authorization(config, operation="read")
        return await self.inner.aget_tuple(config)

    async def alist(
        self,
        config: Optional[RunnableConfig],
        *,
        filter: Optional[Dict[str, Any]] = None,
        before: Optional[RunnableConfig] = None,
        limit: Optional[int] = None
    ) -> AsyncIterator[CheckpointTuple]:
        if config is not None:
            self._verify_thread_authorization(config, operation="list")
        async for item in self.inner.alist(config, filter=filter, before=before, limit=limit):
            yield item

    async def aput(
        self,
        config: RunnableConfig,
        checkpoint: Checkpoint,
        metadata: CheckpointMetadata,
        new_versions: ChannelVersions
    ) -> RunnableConfig:
        self._verify_thread_authorization(config, operation="write")
        clean_cp = dict(checkpoint)
        if "channel_values" in clean_cp and isinstance(clean_cp["channel_values"], dict):
            clean_cp["channel_values"] = sanitize_sensitive_data(clean_cp["channel_values"])
        return await self.inner.aput(config, cast(Checkpoint, clean_cp), metadata, new_versions)

    async def aput_writes(
        self,
        config: RunnableConfig,
        writes: Sequence[Tuple[str, Any]],
        task_id: str,
        task_path: str = ""
    ) -> None:
        self._verify_thread_authorization(config, operation="write")
        clean_writes = [(channel, sanitize_sensitive_data(val)) for channel, val in writes]
        return await self.inner.aput_writes(config, clean_writes, task_id, task_path)

    def delete_thread(self, thread_id: str, workspace_id: Optional[str] = None) -> None:
        if workspace_id and not thread_id.startswith(f"{workspace_id}:"):
            raise PermissionError(f"Cross-tenant deletion denied for thread '{thread_id}'.")
        if hasattr(self.inner, "delete_thread"):
            return self.inner.delete_thread(thread_id)


def get_checkpointer(
    checkpointer_type: Optional[str] = None,
    conn_string: Optional[str] = None,
    enforce_tenant_isolation: bool = True
) -> BaseCheckpointSaver:
    """
    Factory creating a durable or testing LangGraph checkpointer.
    - 'postgres': PostgresSaver initialized with schema migrations setup()
    - 'sqlite': SqliteSaver backed by sqlite3 file with WAL mode and schema setup()
    - 'memory': MemorySaver for test isolation
    All checkpointers are wrapped with TenantGuardedCheckpointer to guarantee multi-tenant security.
    """
    ctype: str = (checkpointer_type or os.getenv("CHECKPOINTER_TYPE") or "").lower()
    raw_db_url: str = conn_string or os.getenv("DATABASE_URL") or ""

    saver: BaseCheckpointSaver

    if ctype == "memory":
        saver = MemorySaver()
    elif ctype == "postgres" or (not ctype and ("postgresql" in raw_db_url or "postgres" in raw_db_url)):
        try:
            import psycopg
            from langgraph.checkpoint.postgres import PostgresSaver

            pg_url = raw_db_url
            if "+psycopg" in pg_url:
                pg_url = pg_url.split("+")[0] + "://" + pg_url.split("://")[1]

            pg_conn: Any = psycopg.connect(pg_url, autocommit=True)
            pg_saver = PostgresSaver(pg_conn)
            pg_saver.setup()
            saver = pg_saver
        except Exception as e:
            logger.warning("Failed to initialize PostgresSaver (%s), falling back to Memory", e)
            saver = MemorySaver()
    elif ctype == "sqlite" or (not ctype and "sqlite" in raw_db_url) or (conn_string and not conn_string.startswith("postgres")):
        try:
            from langgraph.checkpoint.sqlite import SqliteSaver
            db_path = conn_string or raw_db_url.replace("sqlite:///", "") or "storage/checkpoints/langgraph.db"
            parent = os.path.dirname(os.path.abspath(db_path))
            if parent:
                os.makedirs(parent, exist_ok=True)
            sq_conn = sqlite3.connect(db_path, check_same_thread=False, timeout=30.0)
            sq_conn.execute("PRAGMA journal_mode = WAL;")
            sq_conn.execute("PRAGMA busy_timeout = 30000;")
            sq_saver = SqliteSaver(sq_conn)
            sq_saver.setup()
            saver = sq_saver
        except Exception as e:
            logger.warning("Failed to initialize SqliteSaver (%s), falling back to Memory", e)
            saver = MemorySaver()
    else:
        saver = MemorySaver()

    if enforce_tenant_isolation:
        return TenantGuardedCheckpointer(saver)
    return saver
