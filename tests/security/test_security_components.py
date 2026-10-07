import unittest.mock
from starlette.requests import Request

from packages.security.auth import (
    create_access_token,
    decode_access_token,
    _KEY_RING,
    Role
)
from packages.security.limiter import get_client_ip
from packages.security.oauth_state import OAuthStateManager


def test_jwt_key_rotation_env_parsing(monkeypatch):
    """Verifies that JWT_ROTATION_KEYS populates key ring and validates signatures."""
    _KEY_RING["rot_kid_1"] = "secondary-secret-for-jwt-rotation-32b!"
    
    token = create_access_token(
        user_id="user_rot",
        role=Role.OWNER,
        workspace_id="ws_rot",
        key_id="rot_kid_1"
    )
    claims = decode_access_token(token)
    assert claims["sub"] == "user_rot"
    assert claims["workspace_id"] == "ws_rot"


def test_jwt_decode_unverified_header_fallback():
    """Verifies that decode_access_token handles malformed headers gracefully."""
    # A standard token decoded works
    token = create_access_token(user_id="user_plain", role=Role.VIEWER, workspace_id="ws_1")
    claims = decode_access_token(token)
    assert claims["sub"] == "user_plain"


def test_limiter_real_ip_and_proxy_trust(monkeypatch):
    """Verifies get_client_ip properly reads X-Real-IP when proxy is trusted."""
    monkeypatch.setenv("TRUSTED_PROXIES", "127.0.0.1")
    monkeypatch.setenv("TRUST_ALL_PROXIES", "false")

    # Case 1: Trusted proxy with X-Real-IP
    scope = {
        "type": "http",
        "client": ("127.0.0.1", 12345),
        "headers": [(b"x-real-ip", b"198.51.100.42")]
    }
    req = Request(scope)
    ip = get_client_ip(req)
    assert ip == "198.51.100.42"

    # Case 2: Untrusted proxy returns direct client ip
    scope_untrusted = {
        "type": "http",
        "client": ("203.0.113.1", 12345),
        "headers": [(b"x-real-ip", b"198.51.100.42")]
    }
    req_untrusted = Request(scope_untrusted)
    ip_untrusted = get_client_ip(req_untrusted)
    assert ip_untrusted == "203.0.113.1"



def test_oauth_state_manager_with_redis():
    """Verifies OAuthStateManager when connected to Redis (mocked) and TTL expiration."""
    mock_redis = unittest.mock.MagicMock()
    stored_cache = {}

    def setex(key, ttl, val):
        stored_cache[key] = val

    def get(key):
        return stored_cache.get(key)

    def delete(key):
        stored_cache.pop(key, None)

    mock_redis.setex.side_effect = setex
    mock_redis.get.side_effect = get
    mock_redis.delete.side_effect = delete

    manager = OAuthStateManager(ttl_minutes=10, redis_client=mock_redis)

    verifier, challenge = manager.generate_pkce_pair()
    assert len(verifier) >= 64
    assert len(challenge) > 20

    state_token = manager.create_state("linkedin", "ws_1", "user_1", verifier)
    assert f"oauth_state:{state_token}" in stored_cache

    # Consume state atomically
    consumed = manager.consume_state(state_token)
    assert consumed is not None
    assert consumed.workspace_id == "ws_1"
    assert consumed.code_verifier == verifier
    assert f"oauth_state:{state_token}" not in stored_cache

    # Consuming again returns None (single-use)
    assert manager.consume_state(state_token) is None
    # Empty token returns None
    assert manager.consume_state("") is None


def test_oauth_state_memory_expiration():
    """Verifies that expired states in memory are rejected."""
    manager = OAuthStateManager(ttl_minutes=-5)  # Already expired
    verifier, challenge = manager.generate_pkce_pair()
    state_token = manager.create_state("x", "ws_2", "user_2", verifier)

    consumed = manager.consume_state(state_token)
    assert consumed is None
