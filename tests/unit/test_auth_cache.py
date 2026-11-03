import time
from apps.api.dependencies import AuthSessionCache


def test_auth_session_cache_user_status():
    AuthSessionCache.clear_all()
    assert AuthSessionCache.get_user_status("usr_test1") is None

    AuthSessionCache.set_user_status("usr_test1", True, tokens_valid_after=None, ttl=2.0)
    status = AuthSessionCache.get_user_status("usr_test1")
    assert status is not None
    assert status[0] is True
    assert status[1] is None

    AuthSessionCache.invalidate_user("usr_test1")
    assert AuthSessionCache.get_user_status("usr_test1") is None


def test_auth_session_cache_session_revoked():
    AuthSessionCache.clear_all()
    assert AuthSessionCache.is_session_revoked("jti_123") is None

    AuthSessionCache.set_session_revoked("jti_123", False, ttl=2.0)
    assert AuthSessionCache.is_session_revoked("jti_123") is False

    # Invalidation marks session as revoked immediately
    AuthSessionCache.invalidate_session("jti_123")
    assert AuthSessionCache.is_session_revoked("jti_123") is True


def test_auth_session_cache_member_role():
    AuthSessionCache.clear_all()
    assert AuthSessionCache.get_member_role("ws_abc", "usr_1") is None

    AuthSessionCache.set_member_role("ws_abc", "usr_1", "admin", ttl=2.0)
    assert AuthSessionCache.get_member_role("ws_abc", "usr_1") == "admin"

    AuthSessionCache.invalidate_member_role("ws_abc", "usr_1")
    assert AuthSessionCache.get_member_role("ws_abc", "usr_1") is None


def test_auth_session_cache_ttl_expiration():
    AuthSessionCache.clear_all()
    AuthSessionCache.set_user_status("usr_expire", True, ttl=0.05)
    assert AuthSessionCache.get_user_status("usr_expire") is not None

    time.sleep(0.08)
    assert AuthSessionCache.get_user_status("usr_expire") is None
