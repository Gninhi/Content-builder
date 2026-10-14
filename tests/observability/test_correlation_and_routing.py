import os
from unittest.mock import patch
from fastapi.testclient import TestClient
from apps.api.main import app
from packages.observability.correlation import set_correlation_id
from packages.observability.tracing import ObservabilityTracer
from packages.resilience.circuit_breaker import CycleBudget
from services.orchestration.llm import get_gemini_model_for_task

client = TestClient(app)


def test_api_middleware_injects_and_preserves_correlation_id():
    """Verifies that API sets X-Correlation-ID on responses and honors client trace headers."""
    # 1. Custom correlation ID passed by client
    custom_cid = "trace_custom_client_12345"
    response = client.get("/health", headers={"X-Correlation-ID": custom_cid})
    assert response.status_code == 200
    assert response.headers.get("X-Correlation-ID") == custom_cid

    # 2. No correlation ID passed -> API generates one
    response_auto = client.get("/health")
    assert response_auto.status_code == 200
    generated_cid = response_auto.headers.get("X-Correlation-ID")
    assert generated_cid is not None
    assert generated_cid.startswith("trace_")


def test_tracing_metadata_correlates_with_active_context():
    """Verifies that get_run_metadata binds the active correlation ID to the Langfuse trace_id."""
    test_cid = "trace_active_session_99"
    set_correlation_id(test_cid)

    meta = ObservabilityTracer.get_run_metadata(
        workspace_id="ws_corr",
        graph_name="idea_research",
        node_name="scoring"
    )
    assert meta["trace_id"] == test_cid
    assert meta["correlation_id"] == test_cid
    assert meta["run_id"] == test_cid


def test_cycle_budget_records_langfuse_scores():
    """Verifies that CycleBudget records execution metrics in Langfuse."""
    budget = CycleBudget(max_tokens=10000, max_duration_seconds=30.0)
    budget.add_tokens(500)

    with patch.object(ObservabilityTracer, "record_score", return_value=True) as mock_record:
        success = budget.track_in_langfuse(trace_id="trace_test_langfuse_budget")
        assert success is True
        assert mock_record.call_count == 3
        calls = [c[0] for c in mock_record.call_args_list]
        score_names = [call[0] for call in calls]
        assert "cycle_tokens" in score_names
        assert "cycle_duration_seconds" in score_names
        assert "cycle_cost_usd" in score_names


def test_task_based_model_routing():
    """Verifies configurable model routing per agent task."""
    # When no API key is present, get_gemini_model_for_task returns None gracefully
    with patch.dict(os.environ, {"GOOGLE_API_KEY": "", "NVIDIA_API_KEY": "", "DEFAULT_LLM_PROVIDER": "gemini"}):
        assert get_gemini_model_for_task("ideation") is None


    # When API key is present, model routing selects specific model or default gemini-3.8-flash
    with patch.dict(os.environ, {
        "GOOGLE_API_KEY": "AIzaSyFakeKeyForUnitTestsTestingRouting12345",
        "LLM_MODEL_FOR_STRATEGY": "gemini-1.5-pro",
        "LLM_PROVIDER_FOR_STRATEGY": "gemini"
    }):
        with patch("langchain_google_genai.ChatGoogleGenerativeAI") as mock_chat:
            _ = get_gemini_model_for_task("strategy")
            mock_chat.assert_called_once()

            _, kwargs = mock_chat.call_args
            assert kwargs["model"] == "gemini-1.5-pro"
