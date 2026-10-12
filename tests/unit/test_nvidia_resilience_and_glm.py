import time
import pytest
from unittest.mock import MagicMock
from packages.resilience import (
    RateLimiter,
    LLMAuthenticationError,
    LLMModelNotFoundError,
    LLMRateLimitError,
    LLMTimeoutError,
    CircuitBreaker,
    CircuitState,
    CircuitBreakerOpenException,
    normalize_llm_error
)
from services.orchestration.providers.nvidia import (
    strip_reasoning_tokens,
    ResilientChatNVIDIA,
    NVIDIAProviderAdapter
)
from services.orchestration.structured_output import (
    extract_json_from_text,
    record_structured_output_metric,
    get_structured_output_validity_rates
)


def test_strip_reasoning_tokens():
    raw_with_think = "<think>Analyzing the user prompt carefully...\nConsidering factors</think>Final response here."
    cleaned = strip_reasoning_tokens(raw_with_think)
    assert cleaned == "Final response here."
    assert "<think>" not in cleaned

    no_think = "Simple text without reasoning."
    assert strip_reasoning_tokens(no_think) == "Simple text without reasoning."


def test_extract_json_from_text_with_reasoning():
    raw_output = """<think>
I need to generate a JSON with title and score.
Let me build it now.
</think>
```json
{
  "title": "Agent Governance",
  "score": 92.5
}
```
Hope this helps!"""
    import json
    extracted = extract_json_from_text(raw_output)
    parsed = json.loads(extracted)
    assert parsed["title"] == "Agent Governance"
    assert parsed["score"] == 92.5
    assert "<think>" not in extracted


def test_rate_limiter_token_bucket_and_timeout():
    # 60 RPM = 1 token per second
    limiter = RateLimiter(requests_per_minute=60, name="test_limiter")
    # First token immediately available
    assert limiter.acquire(timeout=0.1) is True

    # Test Retry-After cooldown
    limiter.record_retry_after(0.2)
    t0 = time.time()
    assert limiter.acquire(timeout=1.0) is True
    elapsed = time.time() - t0
    assert elapsed >= 0.2, f"Should have waited at least 0.2s, waited {elapsed}s"


def test_error_normalization_taxonomy():
    err_401 = Exception("401 Client Error: Unauthorized for url https://integrate.api.nvidia.com/v1")
    norm_401 = normalize_llm_error(err_401, provider_id="nvidia", model_id="z-ai/glm-5.3-flash")
    assert isinstance(norm_401, LLMAuthenticationError)

    err_404 = Exception("404 Model not found: unknown-model")
    norm_404 = normalize_llm_error(err_404, provider_id="nvidia", model_id="unknown-model")
    assert isinstance(norm_404, LLMModelNotFoundError)

    err_429 = Exception("429 Too Many Requests: retry-after: 5")
    norm_429 = normalize_llm_error(err_429, provider_id="nvidia", model_id="z-ai/glm-5.3-flash")
    assert isinstance(norm_429, LLMRateLimitError)
    assert norm_429.retry_after == 5.0

    err_timeout = Exception("ReadTimeout: HTTPSConnectionPool(host='integrate.api.nvidia.com') timed out")
    norm_timeout = normalize_llm_error(err_timeout, provider_id="nvidia", model_id="z-ai/glm-5.3-flash")
    assert isinstance(norm_timeout, LLMTimeoutError)


def test_resilient_chat_nvidia_wrapper_execution_and_circuit():
    mock_raw = MagicMock()
    mock_resp = MagicMock()
    mock_resp.content = "<think>Internal reasoning</think>Direct Answer"
    mock_raw.invoke.return_value = mock_resp

    limiter = RateLimiter(requests_per_minute=100, name="wrapper_test")
    cb = CircuitBreaker(failure_threshold=2, recovery_timeout=0.2, name="wrapper_cb")

    wrapper = ResilientChatNVIDIA(
        raw_model=mock_raw,
        model_id="z-ai/glm-5.3-flash",
        rate_limiter=limiter,
        circuit_breaker=cb,
        timeout=10.0
    )

    # 1. Success call
    res = wrapper.invoke("Test prompt")
    assert res.content == "Direct Answer"
    assert cb.state == CircuitState.CLOSED

    # 2. Failure simulation trips circuit breaker
    mock_raw.invoke.side_effect = Exception("503 Service Unavailable")
    with pytest.raises(Exception):
        wrapper.invoke("Fail 1")
    with pytest.raises(Exception):
        wrapper.invoke("Fail 2")

    assert cb.state == CircuitState.OPEN

    # 3. Blocked immediately by circuit breaker
    with pytest.raises(CircuitBreakerOpenException):
        wrapper.invoke("Blocked call")


def test_structured_output_validity_rates_tracking():
    record_structured_output_metric("ideation_agent", True)
    record_structured_output_metric("ideation_agent", True)
    record_structured_output_metric("ideation_agent", False)

    rates = get_structured_output_validity_rates()
    assert "ideation_agent" in rates
    # 2 out of 3 = 66.67%
    assert rates["ideation_agent"] == 66.67


def test_nvidia_curated_catalog_includes_glm():
    adapter = NVIDIAProviderAdapter()
    models = adapter.list_models()
    model_ids = [m.model_id for m in models]
    assert "z-ai/glm-5.3-flash" in model_ids
    assert "z-ai/glm-5.3" in model_ids
    assert "zai-org/GLM-5.3" in model_ids
    assert adapter.get_default_model_id() == "z-ai/glm-5.3-flash"
