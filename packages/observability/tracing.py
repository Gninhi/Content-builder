import os
import uuid
from typing import Dict, Any, Optional
from packages.observability.pii import PIIRedactor


class ObservabilityTracer:
    """
    Manages LangSmith tracing, structured telemetry, and audit correlations.
    """

    @classmethod
    def get_run_metadata(
        cls,
        workspace_id: str,
        graph_name: str,
        node_name: str,
        extra_tags: Optional[list] = None
    ) -> Dict[str, Any]:
        run_id = str(uuid.uuid4())
        return {
            "run_id": run_id,
            "workspace_id": workspace_id,
            "graph": graph_name,
            "node": node_name,
            "tags": ["contentops", graph_name] + (extra_tags or []),
            "langsmith_project": os.getenv("LANGCHAIN_PROJECT", "contentops-harness"),
            "tracing_enabled": os.getenv("LANGCHAIN_TRACING_V2", "false").lower() == "true",
        }

    @classmethod
    def sanitize_payload_for_trace(cls, data: Any) -> Any:
        """
        Recursively applies PII redactor to strings in dictionaries or lists.
        """
        if isinstance(data, str):
            return PIIRedactor.redact(data)
        elif isinstance(data, dict):
            return {k: cls.sanitize_payload_for_trace(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [cls.sanitize_payload_for_trace(item) for item in data]
        return data
