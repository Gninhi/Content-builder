import os
import uuid
import logging
from typing import Dict, Any, Optional, List
from packages.observability.pii import PIIRedactor

logger = logging.getLogger(__name__)


class ObservabilityTracer:
    """
    Manages Langfuse end-to-end tracing, structured telemetry, and score correlations
    across the entire editorial system.
    """

    _client = None

    @classmethod
    def _resolve_credentials(cls):
        public_key = (os.getenv("LANGFUSE_PUBLIC_KEY") or "").strip("\"'")
        secret_key = (os.getenv("LANGFUSE_SECRET_KEY") or "").strip("\"'")
        host = (os.getenv("LANGFUSE_HOST") or os.getenv("LANGFUSE_BASE_URL") or "https://cloud.langfuse.com").strip("\"'")
        # Harmonize in os.environ so third-party handlers reading os.environ work seamlessly
        if public_key:
            os.environ["LANGFUSE_PUBLIC_KEY"] = public_key
        if secret_key:
            os.environ["LANGFUSE_SECRET_KEY"] = secret_key
        if host:
            os.environ["LANGFUSE_HOST"] = host
            os.environ["LANGFUSE_BASE_URL"] = host
        return public_key, secret_key, host

    @classmethod
    def is_tracing_enabled(cls) -> bool:
        """Checks if Langfuse tracing is enabled and configured."""
        enabled_flag = os.getenv("LANGFUSE_TRACING_ENABLED", "true").lower() == "true"
        pub, sec, _ = cls._resolve_credentials()
        return enabled_flag and bool(pub and sec)

    @classmethod
    def get_langfuse_client(cls):
        """Returns a singleton instance of the Langfuse client if configured."""
        if cls._client is not None:
            return cls._client

        if not cls.is_tracing_enabled():
            return None

        try:
            from langfuse import Langfuse
            pub, sec, host = cls._resolve_credentials()
            cls._client = Langfuse(
                public_key=pub,
                secret_key=sec,
                host=host
            )
            return cls._client
        except Exception as e:
            logger.warning(f"Unable to initialize Langfuse client: {e}")
            return None

    @classmethod
    def get_callback_handler(
        cls,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
        tags: Optional[List[str]] = None
    ):
        """
        Returns a Langfuse CallbackHandler for LangChain and LangGraph executions.
        Gracefully returns None if Langfuse is not configured.
        """
        if not cls.is_tracing_enabled():
            return None

        try:
            from langfuse.langchain import CallbackHandler
            pub, _, _ = cls._resolve_credentials()
            handler = CallbackHandler(
                public_key=pub
            )
            return handler
        except Exception as e:
            logger.warning(f"Unable to instantiate Langfuse CallbackHandler: {e}")
            return None

    @classmethod
    def record_score(
        cls,
        name: str,
        value: float,
        trace_id: Optional[str] = None,
        comment: Optional[str] = None
    ) -> bool:
        """
        Records an evaluation score (e.g. human_approval, qa_score) in Langfuse.
        """
        client = cls.get_langfuse_client()
        if not client or not trace_id:
            return False

        try:
            client.create_score(
                name=name,
                value=float(value),
                trace_id=trace_id,
                comment=comment
            )
            return True
        except Exception as e:
            logger.warning(f"Failed to record score in Langfuse: {e}")
            return False

    @classmethod
    def tag_trace(cls, trace_id: str, tags: List[str]) -> bool:
        """
        Appends or updates tags (e.g. 'degraded') on a Langfuse trace.
        """
        client = cls.get_langfuse_client()
        if not client or not trace_id:
            return False

        try:
            if hasattr(client, "trace"):
                trace_obj = client.trace(id=trace_id)
                if hasattr(trace_obj, "update"):
                    trace_obj.update(tags=tags)
            return True
        except Exception as e:
            logger.warning(f"Failed to update trace tags in Langfuse: {e}")
            return False

    @classmethod
    def get_run_metadata(
        cls,
        workspace_id: str,
        graph_name: str,
        node_name: str,
        extra_tags: Optional[List[str]] = None,
        trace_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generates correlation metadata for Langfuse traces and local audit logs.
        """
        from packages.observability.correlation import get_correlation_id
        active_cid = get_correlation_id()
        resolved_trace_id = trace_id or (active_cid if active_cid and active_cid != "system" else str(uuid.uuid4()))
        return {
            "run_id": resolved_trace_id,
            "trace_id": resolved_trace_id,
            "correlation_id": resolved_trace_id,
            "workspace_id": workspace_id,
            "graph": graph_name,
            "node": node_name,
            "tags": ["contentops", graph_name, node_name] + (extra_tags or []),
            "langfuse_host": os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com"),
            "tracing_enabled": cls.is_tracing_enabled(),
        }

    @classmethod
    def sanitize_payload_for_trace(cls, data: Any) -> Any:
        """
        Recursively applies PII and secret redactor to dictionary, list, or string payloads.
        """
        if isinstance(data, str):
            return PIIRedactor.redact(data)
        elif isinstance(data, dict):
            return {k: cls.sanitize_payload_for_trace(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [cls.sanitize_payload_for_trace(item) for item in data]
        return data
