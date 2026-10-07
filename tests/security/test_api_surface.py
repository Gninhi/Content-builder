import pytest
from fastapi.testclient import TestClient
from apps.api.main import app
from packages.security.auth import create_access_token


@pytest.fixture
def client():
    return TestClient(app, raise_server_exceptions=False)


def test_security_headers_present(client):
    """Verify standard security headers are injected into all HTTP responses."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.headers.get("X-Content-Type-Options") == "nosniff"
    assert response.headers.get("X-Frame-Options") == "DENY"
    assert "Strict-Transport-Security" in response.headers
    assert "Content-Security-Policy" in response.headers
    assert response.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"


def test_request_body_size_limit_exceeded(client):
    """Verify oversized payloads (> 1MB) receive HTTP 413 Request Entity Too Large."""
    token = create_access_token(
        user_id="test_user",
        role="Editor",
        workspace_id="ws_default"
    )
    oversized_data = {"text": "A" * (1024 * 1024 + 1024)}  # > 1MB
    response = client.post(
        "/v1/sources",
        json={
            "workspace_id": "ws_default",
            "type": "note",
            "raw_text": oversized_data["text"]
        },
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 413
    body = response.json()
    assert "detail" in body
    assert any(term in body["detail"].lower() for term in ["limite", "volumineuse", "large"])


def test_cors_restrictive_origins():
    """Verify CORS does not blindly allow unauthorized external origins with credentials."""
    untrusted_client = TestClient(app)
    response = untrusted_client.options(
        "/health",
        headers={
            "Origin": "https://malicious-site.com",
            "Access-Control-Request-Method": "GET"
        }
    )
    allow_origin = response.headers.get("Access-Control-Allow-Origin")
    assert allow_origin != "https://malicious-site.com"


def test_unhandled_exception_masks_internal_details(client, monkeypatch):
    """Verify internal unhandled errors return sanitized 500 without traceback or SQL leaks."""
    from apps.api.routers import sources

    def crashing_ingest(*args, **kwargs):
        raise RuntimeError("CRITICAL INTERNAL DB LEAK: postgresql://admin:SuperSecretKey@internal.cluster:5432/core")

    monkeypatch.setattr(sources.WebExtractorConnector, "process_source", crashing_ingest)

    token = create_access_token(
        user_id="test_user",
        role="Editor",
        workspace_id="ws_default"
    )

    response = client.post(
        "/v1/sources",
        json={
            "workspace_id": "ws_default",
            "type": "note",
            "raw_text": "Normal safe text"
        },
        headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 500
    assert "SuperSecretKey" not in response.text
    assert "internal.cluster" not in response.text
    assert "RuntimeError" not in response.text
    data = response.json()
    assert data["error"] == "internal_server_error"


def test_rate_limit_key_workspace_isolation():
    """Verify rate limit key isolates by verified workspace_id in JWT, or client IP if unauthenticated."""
    from fastapi import Request
    from packages.security.limiter import get_rate_limit_key

    # 1. Unauthenticated request -> remote client IP
    req_unauth = Request({
        "type": "http",
        "headers": [],
        "client": ("192.168.1.50", 12345)
    })
    assert get_rate_limit_key(req_unauth) == "192.168.1.50"

    # 2. Authenticated request -> isolated by tenant workspace
    token = create_access_token(
        user_id="user_tenant_a",
        role="Editor",
        workspace_id="ws_tenant_alpha"
    )
    req_auth = Request({
        "type": "http",
        "headers": [(b"authorization", f"Bearer {token}".encode("utf-8"))],
        "client": ("192.168.1.50", 12345)
    })
    assert get_rate_limit_key(req_auth) == "ws:ws_tenant_alpha"

