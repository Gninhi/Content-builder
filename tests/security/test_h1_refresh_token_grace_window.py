import uuid
import time
from datetime import datetime, timedelta
import pytest
from fastapi.testclient import TestClient
from apps.api.main import app
from infra.db.database import get_db_session
from infra.db.repository import ContentOpsRepository
from infra.db.models import utc_now, UserRefreshTokenModel

client = TestClient(app, raise_server_exceptions=False)


def test_concurrent_refresh_within_grace_window_does_not_revoke_family():
    """
    Test H1:
    When a refresh token is presented within the grace window (20s) after being rotated,
    the server must NOT treat it as a malicious replay attack and must NOT revoke the token family.
    It should accommodate multi-tab concurrent refreshes smoothly.
    """
    uid = f"usr_{uuid.uuid4().hex[:8]}"
    email = f"user_{uuid.uuid4().hex[:8]}@company.com"
    pwd = "StrongPassword2026!#"

    # Register user
    reg_res = client.post(
        "/v1/auth/register",
        json={
            "email": email,
            "password": pwd,
            "full_name": "Grace User",
            "cgu_accepted": True,
            "privacy_accepted": True,
        },
    )
    assert reg_res.status_code in (200, 201)

    # Login to obtain initial refresh token
    login_res = client.post("/v1/auth/login", json={"email": email, "password": pwd})
    assert login_res.status_code == 200
    token_a = login_res.cookies.get("refresh_token")
    assert token_a is not None

    # Tab 1 performs rotation: Token A -> Token B
    client.cookies.set("refresh_token", token_a)
    rot1_res = client.post("/v1/auth/refresh")
    assert rot1_res.status_code == 200, rot1_res.text
    token_b = rot1_res.cookies.get("refresh_token")
    assert token_b != token_a

    # Tab 2 performs concurrent refresh with Token A within grace window
    client.cookies.set("refresh_token", token_a)
    rot2_res = client.post("/v1/auth/refresh")
    assert rot2_res.status_code == 200, f"Concurrent refresh with Token A failed! Status: {rot2_res.status_code}, {rot2_res.text}"

    # Verify that Token B is STILL valid (family was NOT revoked)
    client.cookies.set("refresh_token", token_b)
    rot3_res = client.post("/v1/auth/refresh")
    assert rot3_res.status_code == 200, f"Token B was revoked by concurrent refresh! Status: {rot3_res.status_code}, {rot3_res.text}"


def test_refresh_reuse_after_grace_window_triggers_family_revocation():
    """
    Test H1:
    When a revoked token is reused AFTER the grace window (>20s),
    breach detection triggers and revokes the whole family.
    """
    email = f"reuse_{uuid.uuid4().hex[:8]}@company.com"
    pwd = "StrongPassword2026!#"

    client.post(
        "/v1/auth/register",
        json={
            "email": email,
            "password": pwd,
            "full_name": "Reuse User",
            "cgu_accepted": True,
            "privacy_accepted": True,
        },
    )
    login_res = client.post("/v1/auth/login", json={"email": email, "password": pwd})
    token_a = login_res.cookies.get("refresh_token")

    # Rotate Token A
    client.cookies.set("refresh_token", token_a)
    rot1_res = client.post("/v1/auth/refresh")
    assert rot1_res.status_code == 200
    token_b = rot1_res.cookies.get("refresh_token")

    # Manually backdate revoked_at of Token A in DB by 30 seconds to simulate elapsed grace window
    with get_db_session() as db:
        tokens = db.query(UserRefreshTokenModel).all()
        for t in tokens:
            if t.is_revoked:
                t.revoked_at = utc_now() - timedelta(seconds=35)
        db.commit()

    # Reuse Token A after grace period
    client.cookies.set("refresh_token", token_a)
    stale_res = client.post("/v1/auth/refresh")
    assert stale_res.status_code == 401
    assert "réutilisation" in stale_res.text.lower() or "alerte" in stale_res.text.lower()

    # Token B should now be revoked
    client.cookies.set("refresh_token", token_b)
    final_res = client.post("/v1/auth/refresh")
    assert final_res.status_code == 401
