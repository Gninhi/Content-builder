import pytest
import time
import logging
from unittest.mock import patch, MagicMock
from pydantic import BaseModel, Field
from typing import List, Optional

from services.orchestration.nodes.analytics import normalize_metrics_node
from services.orchestration.nodes.scheduling import schedule_job_node
from services.orchestration.nodes.publishing import verify_approval_and_publish_node
from services.orchestration.nodes.insights import generate_strategy_insights_node
from packages.domain.state_machine import ContentStatus
from packages.domain.idempotency import compute_payload_hash
from packages.observability.correlation import (
    get_correlation_id,
    set_correlation_id,
    CorrelationIdLogFilter,
    setup_correlated_logging,
)
from packages.observability.json_logger import StructuredJSONFormatter, setup_structured_logging
from packages.observability.tracing import ObservabilityTracer
from packages.resilience.circuit_breaker import CycleBudget, BudgetExceededException, CircuitBreaker, CircuitBreakerOpenException
from packages.resilience.errors import (
    LLMError,
    LLMAuthenticationError,
    LLMModelNotFoundError,
    LLMRateLimitError,
    LLMTimeoutError,
    LLMProviderUnavailableError,
    normalize_llm_error,
)
from packages.resilience.rate_limiter import RateLimiter
from services.orchestration.structured_output import (
    make_schema_template,
    record_structured_output_metric,
)
from packages.tools.schemas import (
    utc_now,
    SearchEngineType,
    WebSearchResultItem,
    WebSearchResponse,
    BrowseRequest,
)
from packages.tools.data_connectors import OfficialDataConnectors


# =====================================================================
# 1. Analytics Node Coverage
# =====================================================================
def test_normalize_metrics_node_nominal():
    state = {
        "raw_metrics": {
            "impressions": 1000,
            "engagements": 50,
            "clicks": 20,
            "comments": 5,
            "shares": 10,
        }
    }
    result = normalize_metrics_node(state)
    assert result["status"] == "MEASURED"
    metrics = result["normalized_metrics"]
    assert metrics["impressions"] == 1000
    assert metrics["engagement_rate_pct"] == 5.0
    assert metrics["click_through_rate_pct"] == 2.0
    assert metrics["amplification_rate_pct"] == 1.0
    assert metrics["performance_index"] == 3.8


def test_normalize_metrics_node_zero_impressions():
    state = {"raw_metrics": {}}
    result = normalize_metrics_node(state)
    assert result["status"] == "MEASURED"
    metrics = result["normalized_metrics"]
    assert metrics["impressions"] == 1
    assert metrics["engagement_rate_pct"] == 0.0


# =====================================================================
# 2. Scheduling Node Coverage
# =====================================================================
def test_schedule_job_node_unapproved():
    state = {"status": ContentStatus.DRAFT}
    result = schedule_job_node(state)
    assert "error" in result
    assert result["status"] == ContentStatus.DRAFT


def test_schedule_job_node_success():
    state = {
        "status": ContentStatus.APPROVED,
        "workspace_id": "ws_123",
        "variant_id": "var_456",
        "platform": "linkedin",
        "scheduled_at": "2026-10-20T10:00:00Z",
    }
    result = schedule_job_node(state)
    assert result["status"] == ContentStatus.SCHEDULED
    assert result["error"] is None
    assert result["job_id"].startswith("job_")
    assert result["idempotency_key"] is not None


# =====================================================================
# 3. Publishing Graph & Node Coverage
# =====================================================================
def test_verify_approval_and_publish_tampered():
    payload = {"text": "Original text"}
    state = {
        "payload": payload,
        "approval_hash": "different_hash_value",
        "idempotency_key": "key_1",
        "platform": "linkedin",
    }
    result = verify_approval_and_publish_node(state)
    assert result["status"] == ContentStatus.PUBLISH_FAILED
    assert "Security failure" in result["error"]


def test_verify_approval_and_publish_unsupported_platform():
    payload = {"text": "Valid post"}
    h = compute_payload_hash(payload)
    state = {
        "payload": payload,
        "approval_hash": h,
        "idempotency_key": "key_2",
        "platform": "unsupported_social",
    }
    result = verify_approval_and_publish_node(state)
    assert result["status"] == ContentStatus.PUBLISH_FAILED
    assert "Unsupported publishing platform" in result["error"]


def test_verify_approval_and_publish_linkedin_sandbox():
    payload = {"body": "Publish to LinkedIn"}
    h = compute_payload_hash(payload)
    state = {
        "payload": payload,
        "approval_hash": h,
        "idempotency_key": "key_3",
        "platform": "linkedin",
    }
    result = verify_approval_and_publish_node(state)
    assert result["status"] == ContentStatus.PUBLISHED
    assert result["receipt"] is not None
    assert result["error"] is None


def test_verify_approval_and_publish_x_sandbox():
    payload = {"body": "Publish to X"}
    h = compute_payload_hash(payload)
    state = {
        "payload": payload,
        "approval_hash": h,
        "idempotency_key": "key_4",
        "platform": "x",
    }
    result = verify_approval_and_publish_node(state)
    assert result["status"] == ContentStatus.PUBLISHED
    assert result["receipt"] is not None


# =====================================================================
# 4. Strategy Insights Node Coverage
# =====================================================================
def test_generate_strategy_insights_no_data():
    state = {
        "workspace_id": "ws_test",
        "pillars": ["Pillar 1"],
        "metric_snapshots": [],
    }
    result = generate_strategy_insights_node(state)
    assert result["status"] == "NO_DATA"
    assert result["hypotheses"] == []
    assert result["recommendations"] == []
    assert "run_id" in result


# =====================================================================
# 5. Observability: Correlation, JSON Logger, Tracing Coverage
# =====================================================================
def test_correlation_id_lifecycle():
    cid = set_correlation_id("custom_corr_123")
    assert cid == "custom_corr_123"
    assert get_correlation_id() == "custom_corr_123"

    auto_cid = set_correlation_id(None)
    assert auto_cid.startswith("trace_")


def test_correlation_id_log_filter():
    filt = CorrelationIdLogFilter()
    record = logging.LogRecord("test_logger", logging.INFO, "test.py", 10, "Test message", (), None)
    assert filt.filter(record) is True
    assert hasattr(record, "correlation_id")


def test_structured_json_formatter_and_setup():
    formatter = StructuredJSONFormatter(service_name="test-service")
    record = logging.LogRecord("test_logger", logging.INFO, "test.py", 10, "User email: test@example.com", (), None)
    formatted = formatter.format(record)
    assert "test-service" in formatted
    assert "[REDACTED_EMAIL]" in formatted

    # Test with exception
    try:
        raise ValueError("Simulated failure")
    except ValueError:
        import sys
        record.exc_info = sys.exc_info()
    formatted_exc = formatter.format(record)
    assert "Simulated failure" in formatted_exc

    # Test setup functions
    orig_handlers = list(logging.getLogger().handlers)
    try:
        setup_correlated_logging()
        setup_structured_logging(as_json=True)
        setup_structured_logging(as_json=False)
    finally:
        logging.getLogger().handlers = orig_handlers


def test_observability_tracer_configuration(monkeypatch):
    monkeypatch.setenv("LANGFUSE_PUBLIC_KEY", "pk_test")
    monkeypatch.setenv("LANGFUSE_SECRET_KEY", "sk_test")
    monkeypatch.setenv("LANGFUSE_HOST", "https://langfuse.internal")
    monkeypatch.setenv("LANGFUSE_TRACING_ENABLED", "true")

    pub, sec, host = ObservabilityTracer._resolve_credentials()
    assert pub == "pk_test"
    assert sec == "sk_test"
    assert host == "https://langfuse.internal"
    assert ObservabilityTracer.is_tracing_enabled() is True

    meta = ObservabilityTracer.get_run_metadata("ws_abc", "graph_1", "node_1")
    assert meta["workspace_id"] == "ws_abc"
    assert meta["graph"] == "graph_1"
    assert "run_id" in meta


# =====================================================================
# 6. Resilience: CircuitBreaker, CycleBudget & RateLimiter Coverage
# =====================================================================
def test_cycle_budget_enforcement():
    budget = CycleBudget(max_tokens=100, max_duration_seconds=10.0)
    budget.add_tokens(50)
    assert budget.used_tokens == 50

    with pytest.raises(BudgetExceededException, match="token budget"):
        budget.add_tokens(60)

    slow_budget = CycleBudget(max_tokens=1000, max_duration_seconds=0.01)
    time.sleep(0.02)
    with pytest.raises(BudgetExceededException, match="duration limit"):
        slow_budget.check_budget()


def test_rate_limiter_acquire_and_retry_after():
    limiter = RateLimiter(requests_per_minute=600, name="test_limiter")
    assert limiter.acquire(timeout=1.0) is True

    # Test record retry-after
    limiter.record_retry_after(0.05)
    assert limiter._retry_after_until is not None
    time.sleep(0.08)
    assert limiter.acquire(timeout=1.0) is True


# =====================================================================
# 7. Structured Output Template Generator Coverage
# =====================================================================
class NestedModel(BaseModel):
    tag: str = Field(description="Nom du tag")
    score: float = Field(default=0.9)


class SampleModel(BaseModel):
    title: str = Field(description="Titre du post")
    count: int = Field(default=5)
    is_active: bool = Field(default=True)
    tags: List[str] = Field(default_factory=list)
    nested: Optional[NestedModel] = None


def test_make_schema_template_and_metrics():
    template = make_schema_template(SampleModel)
    assert "title" in template
    assert "count" in template
    assert "is_active" in template

    record_structured_output_metric("agent_test", valid=True, repaired=False)
    record_structured_output_metric("agent_test", valid=False, repaired=True)


# =====================================================================
# 8. Tools & Schemas Coverage
# =====================================================================
def test_tool_schemas_and_properties():
    now = utc_now()
    assert now is not None

    item = WebSearchResultItem(
        title="Title",
        url="https://example.com/post/1",
        snippet="Snippet text",
        engine=SearchEngineType.GOOGLE.value,
    )
    assert item.canonical_url == "https://example.com/post/1"
    assert item.domain == "Web"

    resp = WebSearchResponse(
        query="test query",
        engine_used="google",
        total_results=1,
        results=[item],
    )
    assert len(resp.items) == 1

    req = BrowseRequest(url="https://example.com")
    assert req.mode == "main_content"
    assert req.timeout_seconds == 15.0


def test_data_connectors_arxiv_parsing():
    sample_xml = """<?xml version="1.0" encoding="utf-8"?>
    <feed xmlns="http://www.w3.org/2005/Atom">
        <entry>
            <id>http://arxiv.org/abs/2401.00001</id>
            <title>Advances in Multi-Agent Reasoning</title>
            <summary>Comprehensive overview of autonomous agent graphs.</summary>
            <published>2026-01-01T00:00:00Z</published>
        </entry>
    </feed>"""

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = sample_xml

    with patch("httpx.Client.get", return_value=mock_resp):
        signals = OfficialDataConnectors.fetch_arxiv_signals(query="multi-agent", max_results=1)
        assert len(signals) == 1
        assert signals[0].title == "Advances in Multi-Agent Reasoning"
        assert "2401.00001" in signals[0].identifier


# =====================================================================
# 9. CircuitBreaker & LLM Error Normalization Coverage
# =====================================================================
def test_circuit_breaker_state_transitions():
    cb = CircuitBreaker(failure_threshold=2, recovery_timeout=0.05, name="test_cb")
    assert cb.state.value == "CLOSED"

    # Simulate failures to open circuit
    def failing_fn():
        raise ValueError("Simulated remote failure")

    with pytest.raises(ValueError):
        cb.execute(failing_fn)
    assert cb.state.value == "CLOSED"

    with pytest.raises(ValueError):
        cb.execute(failing_fn)
    assert cb.state.value == "OPEN"

    # When OPEN, call should immediately raise CircuitBreakerOpenException
    with pytest.raises(CircuitBreakerOpenException):
        cb.execute(lambda: "should_not_run")

    # Wait for recovery timeout to transition to HALF_OPEN
    time.sleep(0.06)
    assert cb.can_execute() is True
    assert cb.state.value == "HALF_OPEN"

    # Successful call in HALF_OPEN resets to CLOSED
    res = cb.execute(lambda: "recovered")
    assert res == "recovered"
    assert cb.state.value == "CLOSED"


def test_normalize_llm_error_mapping():
    err_401 = Exception("401 Unauthorized: invalid_api_key")
    norm_401 = normalize_llm_error(err_401, provider_id="prov1", model_id="mod1")
    assert isinstance(norm_401, LLMAuthenticationError)

    err_404 = Exception("404 Model does not exist")
    norm_404 = normalize_llm_error(err_404, provider_id="prov1", model_id="mod1")
    assert isinstance(norm_404, LLMModelNotFoundError)

    err_429 = Exception("429 rate limit exceeded. retry-after: 5.5")
    norm_429 = normalize_llm_error(err_429, provider_id="prov1", model_id="mod1")
    assert isinstance(norm_429, LLMRateLimitError)
    assert norm_429.retry_after == 5.5

    err_timeout = Exception("Deadline exceeded: readtimeout")
    norm_timeout = normalize_llm_error(err_timeout, provider_id="prov1", model_id="mod1")
    assert isinstance(norm_timeout, LLMTimeoutError)

    err_503 = Exception("503 Service Unavailable")
    norm_503 = normalize_llm_error(err_503, provider_id="prov1", model_id="mod1")
    assert isinstance(norm_503, LLMProviderUnavailableError)

    err_generic = Exception("Random unexpected error")
    norm_generic = normalize_llm_error(err_generic, provider_id="prov1", model_id="mod1")
    assert isinstance(norm_generic, LLMError)
    # Check idempotency when already an LLMError
    assert normalize_llm_error(norm_generic) is norm_generic

