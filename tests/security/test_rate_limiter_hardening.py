from unittest.mock import MagicMock
from packages.security.limiter import (
    get_client_ip,
    mask_storage_uri,
    _init_limiter,
)


def test_mask_storage_uri():
    """Passwords in Redis and Rediss URIs must be masked in logs and diagnostics."""
    assert mask_storage_uri("redis://:my_secret_pass@localhost:6379/0") == "redis://:***@localhost:6379/0"
    assert mask_storage_uri("redis://admin:super_secret_pw@redis.internal:6379/1") == "redis://admin:***@redis.internal:6379/1"
    assert mask_storage_uri("rediss://user:pw123@cache.prod.internal:6380/0") == "rediss://user:***@cache.prod.internal:6380/0"
    assert mask_storage_uri("memory://") == "memory://"
    assert mask_storage_uri(None) is None


def test_untrusted_client_cannot_spoof_ip_with_x_forwarded_for(monkeypatch):
    """Untrusted client IP cannot spoof rate limit key with X-Forwarded-For header."""
    monkeypatch.setenv("TRUSTED_PROXIES", "127.0.0.1,::1")
    monkeypatch.setenv("TRUST_ALL_PROXIES", "false")

    # Request from untrusted external IP
    mock_request = MagicMock()
    mock_request.client.host = "203.0.113.50"
    mock_request.headers = {"X-Forwarded-For": "198.51.100.99"}

    resolved_ip = get_client_ip(mock_request)
    assert resolved_ip == "203.0.113.50", "Untrusted proxy must not honor X-Forwarded-For"


def test_trusted_client_honors_x_forwarded_for_and_cidr(monkeypatch):
    """Trusted proxy IP (direct or in CIDR) safely honors X-Forwarded-For header."""
    monkeypatch.setenv("TRUSTED_PROXIES", "127.0.0.1,::1,10.0.0.0/8")
    monkeypatch.setenv("TRUST_ALL_PROXIES", "false")

    # Request from trusted loopback
    req1 = MagicMock()
    req1.client.host = "127.0.0.1"
    req1.headers = {"X-Forwarded-For": "198.51.100.99, 10.0.0.1"}
    assert get_client_ip(req1) == "198.51.100.99"

    # Request from trusted private subnet CIDR 10.0.0.0/8
    req2 = MagicMock()
    req2.client.host = "10.0.4.15"
    req2.headers = {"X-Forwarded-For": "203.0.113.77"}
    assert get_client_ip(req2) == "203.0.113.77"


def test_rate_limit_global_is_honored(monkeypatch):
    """RATE_LIMIT_GLOBAL takes precedence over default limits."""
    monkeypatch.setenv("RATE_LIMIT_GLOBAL", "45/minute")
    monkeypatch.setenv("RATE_LIMIT_STORAGE_URI", "memory://")
    limiter_instance = _init_limiter()
    limit_items = [item.limit for lg in limiter_instance._default_limits for item in lg]
    assert any(limit.amount == 45 for limit in limit_items)
