import json
import logging
from datetime import datetime, timezone
from packages.observability.correlation import get_correlation_id
from packages.observability.pii import PIIRedactor


class StructuredJSONFormatter(logging.Formatter):
    """
    Formatter that outputs log records as structured JSON,
    redacting sensitive credentials and attaching correlation IDs.
    """

    def __init__(self, service_name: str = "contentops-harness"):
        super().__init__()
        self.service_name = service_name

    def format(self, record: logging.LogRecord) -> str:
        # 1. Format raw message
        raw_message = record.getMessage()

        # 2. Redact sensitive patterns (PII, Bearer tokens, API keys)
        sanitized_message = PIIRedactor.redact(raw_message)

        # 3. Build structured JSON payload
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": sanitized_message,
            "correlation_id": getattr(record, "correlation_id", get_correlation_id()),
            "service": self.service_name,
            "path": record.pathname,
            "line": record.lineno,
        }

        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_entry, ensure_ascii=False)


def setup_structured_logging(as_json: bool = False, level: int = logging.INFO) -> None:
    """Configures application-wide logging with redaction and correlation."""
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    handler = logging.StreamHandler()
    if as_json:
        handler.setFormatter(StructuredJSONFormatter())
    else:
        formatter = logging.Formatter(
            "[%(asctime)s] [%(levelname)s] [corr:%(correlation_id)s] %(name)s: %(message)s"
        )
        handler.setFormatter(formatter)

    # Replace existing handlers
    root_logger.handlers = [handler]
