import os
from unittest.mock import patch
from fastapi.testclient import TestClient

from apps.api.main import app
from packages.observability.prometheus import (
    HTTP_REQUESTS_TOTAL,
    PUBLICATION_JOBS_TOTAL,
    LLM_INFERENCES_TOTAL,
)

client = TestClient(app, raise_server_exceptions=False)


def test_metrics_endpoint_returns_prometheus_format():
    """Verify /metrics returns 200 with standard Prometheus media type and metric descriptions."""
    # Trigger a request to /health to ensure counters are populated
    health_res = client.get("/health")
    assert health_res.status_code == 200

    # Ensure counter was recorded
    assert HTTP_REQUESTS_TOTAL.labels(method="GET", endpoint="/health", status="200")._value.get() >= 1.0

    response = client.get("/metrics")
    assert response.status_code == 200
    assert "text/plain" in response.headers.get("content-type", "")
    assert "contentops_http_requests_total" in response.text
    assert "contentops_http_request_duration_seconds" in response.text


def test_metrics_auth_token_protection():
    """Verify that when METRICS_AUTH_TOKEN is configured, unauthorized requests receive 401."""
    with patch.dict(os.environ, {"METRICS_AUTH_TOKEN": "secret-metrics-token-infra-99"}):
        # 1. Without token -> 401
        res_no_auth = client.get("/metrics")
        assert res_no_auth.status_code == 401
        assert "Unauthorized" in res_no_auth.text

        # 2. With invalid token -> 401
        res_bad_auth = client.get("/metrics", headers={"Authorization": "Bearer wrong-token"})
        assert res_bad_auth.status_code == 401

        # 3. With valid token -> 200
        res_valid = client.get("/metrics", headers={"Authorization": "Bearer secret-metrics-token-infra-99"})
        assert res_valid.status_code == 200
        assert "contentops_http_requests_total" in res_valid.text


def test_custom_metrics_incrementation():
    """Verify that custom application metrics can be incremented cleanly."""
    initial_pub_count = PUBLICATION_JOBS_TOTAL.labels(platform="linkedin", status="PUBLISHED")._value.get()
    PUBLICATION_JOBS_TOTAL.labels(platform="linkedin", status="PUBLISHED").inc()
    assert PUBLICATION_JOBS_TOTAL.labels(platform="linkedin", status="PUBLISHED")._value.get() == initial_pub_count + 1

    initial_llm_count = LLM_INFERENCES_TOTAL.labels(provider="nvidia", model="meta/llama-3.2-11b")._value.get()
    LLM_INFERENCES_TOTAL.labels(provider="nvidia", model="meta/llama-3.2-11b").inc()
    assert LLM_INFERENCES_TOTAL.labels(provider="nvidia", model="meta/llama-3.2-11b")._value.get() == initial_llm_count + 1
