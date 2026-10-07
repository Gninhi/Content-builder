import json
import logging
from packages.observability.json_logger import StructuredJSONFormatter
from packages.observability.correlation import set_correlation_id


def test_structured_json_formatter_outputs_valid_json_with_correlation():
    """Verifies that StructuredJSONFormatter formats records as JSON with correlation ID."""
    set_correlation_id("trace_log_json_123")
    formatter = StructuredJSONFormatter(service_name="contentops-test")

    logger = logging.getLogger("test.logger")
    record = logger.makeRecord(
        name="test.logger",
        level=logging.INFO,
        fn="test_json_logger.py",
        lno=15,
        msg="Execution cycle started successfully",
        args=(),
        exc_info=None
    )

    formatted = formatter.format(record)
    data = json.loads(formatted)

    assert data["level"] == "INFO"
    assert data["logger"] == "test.logger"
    assert data["message"] == "Execution cycle started successfully"
    assert data["correlation_id"] == "trace_log_json_123"
    assert data["service"] == "contentops-test"
    assert "timestamp" in data


def test_structured_json_formatter_redacts_credentials():
    """Verifies that secrets (Bearer tokens, api keys) are redacted in log messages."""
    formatter = StructuredJSONFormatter()
    logger = logging.getLogger("test.security")
    sensitive_msg = "User authenticated with Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.e30.secret and key=AIzaSyFakeKey12345678"

    record = logger.makeRecord(
        name="test.security",
        level=logging.WARNING,
        fn="test_json_logger.py",
        lno=30,
        msg=sensitive_msg,
        args=(),
        exc_info=None
    )

    formatted = formatter.format(record)
    data = json.loads(formatted)

    assert "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9" not in data["message"]
    assert "[REDACTED_API_KEY]" in data["message"] or "[REDACTED" in data["message"]
