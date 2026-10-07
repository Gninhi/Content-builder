import contextvars
import logging
import uuid
from typing import Optional

# Context variable holding the active trace/correlation ID across async tasks
correlation_id_ctx: contextvars.ContextVar[str] = contextvars.ContextVar(
    "correlation_id_ctx", default="system"
)


def get_correlation_id() -> str:
    """Returns the current request/trace correlation ID."""
    return correlation_id_ctx.get()


def set_correlation_id(correlation_id: Optional[str] = None) -> str:
    """Sets and returns the correlation ID in the current execution context."""
    cid = correlation_id or f"trace_{uuid.uuid4().hex[:16]}"
    correlation_id_ctx.set(cid)
    return cid


class CorrelationIdLogFilter(logging.Filter):
    """
    Logging filter that injects 'correlation_id' into all log records,
    linking application logs directly to Langfuse trace IDs.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        record.correlation_id = get_correlation_id()  # type: ignore[attr-defined]
        return True


def setup_correlated_logging(log_level: int = logging.INFO) -> None:
    """Configures root logger with correlation ID injection."""
    root_logger = logging.getLogger()
    filt = CorrelationIdLogFilter()

    # Avoid duplicate filters
    if not any(isinstance(f, CorrelationIdLogFilter) for f in root_logger.filters):
        root_logger.addFilter(filt)

    formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] [corr:%(correlation_id)s] %(name)s: %(message)s"
    )

    for handler in root_logger.handlers:
        handler.addFilter(filt)
        handler.setFormatter(formatter)
