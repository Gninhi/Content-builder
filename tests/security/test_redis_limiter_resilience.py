from fastapi import Request
from slowapi.errors import RateLimitExceeded
from packages.security.limiter import (
    check_redis_connectivity,
    get_storage_status,
    safe_rate_limit_exceeded_handler,
    get_client_ip,
)


def test_redis_connectivity_check_offline():
    """Verify check_redis_connectivity returns False when Redis is offline without crashing."""
    assert check_redis_connectivity("redis://127.0.0.1:63999/0", timeout=0.2) is False


def test_storage_diagnostic_reports_status():
    """Verify get_storage_status returns a well-structured diagnostic dictionary."""
    status = get_storage_status()
    assert "status" in status
    assert "environment" in status
    assert "effective_uri" in status
    assert "degraded" in status


def test_safe_rate_limit_exceeded_handler_for_authentic_quota_exceeded():
    """Verify 429 response when authentic RateLimitExceeded is handled."""
    from limits import parse
    from slowapi.wrappers import Limit
    raw_limit = parse("200/minute")
    wrapped_limit = Limit(
        limit=raw_limit,
        key_func=lambda: "key",
        scope=None,
        per_method=False,
        methods=None,
        error_message=None,
        exempt_when=None,
        override_defaults=True,
        cost=1,
    )
    req = Request({"type": "http", "path": "/v1/sources", "headers": []})
    exc = RateLimitExceeded(wrapped_limit)
    res = safe_rate_limit_exceeded_handler(req, exc)
    assert res.status_code == 429
    assert b"Rate limit exceeded" in res.body


def test_safe_rate_limit_exceeded_handler_for_storage_connection_error():
    """Verify 503 response instead of 500 crash when Redis ConnectionError is intercepted."""
    req = Request({"type": "http", "path": "/v1/content", "headers": []})
    exc = ConnectionError("Connection refused to Redis cluster")
    res = safe_rate_limit_exceeded_handler(req, exc)
    assert res.status_code == 503
    assert b"Rate limit service temporarily unavailable" in res.body


def test_safe_rate_limit_exceeded_handler_for_sensitive_auth_route():
    """Verify 503 with specific message when rate limiting storage fails on sensitive auth route."""
    req = Request({"type": "http", "path": "/v1/auth/login", "headers": []})
    exc = ConnectionError("Connection refused")
    res = safe_rate_limit_exceeded_handler(req, exc)
    assert res.status_code == 503
    assert b"temporarily unavailable" in res.body


def test_get_client_ip_with_trusted_proxy(monkeypatch):
    """Verify IP resolution correctly adheres to trusted proxy configuration."""
    monkeypatch.setenv("TRUSTED_PROXIES", "127.0.0.1,10.0.0.1")
    monkeypatch.setenv("TRUST_ALL_PROXIES", "false")

    # Request directly from trusted proxy
    req = Request({
        "type": "http",
        "client": ("127.0.0.1", 5000),
        "headers": [(b"x-forwarded-for", b"203.0.113.195, 127.0.0.1")],
    })
    assert get_client_ip(req) == "203.0.113.195"

    # Request directly from untrusted client claiming spoofed IP
    req_untrusted = Request({
        "type": "http",
        "client": ("198.51.100.22", 5000),
        "headers": [(b"x-forwarded-for", b"203.0.113.195")],
    })
    assert get_client_ip(req_untrusted) == "198.51.100.22"
