import os
import pytest
from fastapi.testclient import TestClient
from apps.api.main import app
from infra.db.database import SessionLocal
from infra.db.repository import ContentOpsRepository
from packages.security.email_service import get_email_service, MemoryLogEmailService

client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_email_service():
    app.state.limiter.enabled = False
    svc = get_email_service()
    if isinstance(svc, MemoryLogEmailService):
        svc.clear()
    yield
    app.state.limiter.enabled = True
    if isinstance(svc, MemoryLogEmailService):
        svc.clear()


def test_register_strict_validation():
    # 1. Short password (< 10 chars)
    res = client.post(
        "/v1/auth/register",
        json={
            "email": "test_short@example.com",
            "password": "short",
            "full_name": "Test User",
            "cgu_accepted": True,
            "privacy_accepted": True,
        },
    )
    assert res.status_code == 422
    assert "10 caractères" in res.json()["detail"]

    # 2. Common password
    res = client.post(
        "/v1/auth/register",
        json={
            "email": "test_common@example.com",
            "password": "password123",
            "full_name": "Test User",
            "cgu_accepted": True,
            "privacy_accepted": True,
        },
    )
    assert res.status_code == 422
    assert "courant" in res.json()["detail"]

    # 3. Missing CGU
    res = client.post(
        "/v1/auth/register",
        json={
            "email": "test_nocgu@example.com",
            "password": "StrongPassword2026!#",
            "full_name": "Test User",
            "cgu_accepted": False,
            "privacy_accepted": True,
        },
    )
    assert res.status_code == 400
    assert "conditions" in res.json()["detail"].lower()

    # 4. Mass assignment attempt (extra field forbidden)
    res = client.post(
        "/v1/auth/register",
        json={
            "email": "test_mass@example.com",
            "password": "StrongPassword2026!#",
            "full_name": "Test User",
            "cgu_accepted": True,
            "privacy_accepted": True,
            "role": "Owner",  # Extra field
        },
    )
    assert res.status_code == 422


def test_register_and_verify_email_flow():
    email = f"user_{os.urandom(4).hex()}@example.com"
    pwd = "StrongPassword2026!#"
    res = client.post(
        "/v1/auth/register",
        json={
            "email": email,
            "password": pwd,
            "full_name": "Alice Dupont",
            "workspace_name": "Acme Editorial",
            "cgu_accepted": True,
            "privacy_accepted": True,
        },
    )
    assert res.status_code == 201
    data = res.json()
    assert data["email"] == email

    # Check email was dispatched in memory
    email_svc = get_email_service()
    token = email_svc.get_latest_token_for(email, "verification")
    assert token is not None

    # Verify email
    verif_res = client.post("/v1/auth/verify-email", json={"token": token})
    assert verif_res.status_code == 200
    assert "succès" in verif_res.json()["message"]

    # Re-using verification token fails
    re_verif = client.post("/v1/auth/verify-email", json={"token": token})
    assert re_verif.status_code == 400


def test_duplicate_email_registration_anti_enumeration():
    email = f"dup_{os.urandom(4).hex()}@example.com"
    pwd = "StrongPassword2026!#"

    # First registration
    res1 = client.post(
        "/v1/auth/register",
        json={
            "email": email,
            "password": pwd,
            "full_name": "Bob Smith",
            "cgu_accepted": True,
            "privacy_accepted": True,
        },
    )
    assert res1.status_code == 201

    # Second registration with same email: returns success without revealing duplication
    res2 = client.post(
        "/v1/auth/register",
        json={
            "email": email,
            "password": pwd,
            "full_name": "Bob Duplicate",
            "cgu_accepted": True,
            "privacy_accepted": True,
        },
    )
    assert res2.status_code in (200, 201)
    assert "email" in res2.json()["message"].lower()


def test_login_and_refresh_token_rotation():
    email = f"login_rot_{os.urandom(4).hex()}@example.com"
    pwd = "StrongPassword2026!#"

    # Register
    client.post(
        "/v1/auth/register",
        json={
            "email": email,
            "password": pwd,
            "full_name": "Claire Martin",
            "cgu_accepted": True,
            "privacy_accepted": True,
        },
    )

    # Verify email
    email_svc = get_email_service()
    token = email_svc.get_latest_token_for(email, "verification")
    if token:
        client.post("/v1/auth/verify-email", json={"token": token})

    # Login
    login_res = client.post(
        "/v1/auth/login",
        json={"email": email, "password": pwd},
    )
    assert login_res.status_code == 200
    login_data = login_res.json()
    assert "access_token" in login_data
    assert login_data["role"] == "Owner"
    assert "refresh_token" in login_res.cookies

    initial_refresh_cookie = login_res.cookies["refresh_token"]

    # Refresh session
    refresh_res = client.post(
        "/v1/auth/refresh",
        cookies={"refresh_token": initial_refresh_cookie},
    )
    assert refresh_res.status_code == 200
    refreshed_data = refresh_res.json()
    assert "access_token" in refreshed_data
    assert refreshed_data["access_token"] != login_data["access_token"]
    assert "refresh_token" in refresh_res.cookies
    rotated_cookie = refresh_res.cookies["refresh_token"]
    assert rotated_cookie != initial_refresh_cookie

    # REUSE DETECTION: presenting the previous revoked refresh token triggers breach alert
    reuse_res = client.post(
        "/v1/auth/refresh",
        cookies={"refresh_token": initial_refresh_cookie},
    )
    assert reuse_res.status_code == 401
    assert "réutilisation" in reuse_res.json()["detail"].lower()

    # The rotated cookie should now also be invalidated because the family was revoked!
    family_invalidated_res = client.post(
        "/v1/auth/refresh",
        cookies={"refresh_token": rotated_cookie},
    )
    assert family_invalidated_res.status_code == 401


def test_account_lockout_after_failed_logins():
    email = f"lock_{os.urandom(4).hex()}@example.com"
    pwd = "StrongPassword2026!#"

    client.post(
        "/v1/auth/register",
        json={
            "email": email,
            "password": pwd,
            "full_name": "Lockout User",
            "cgu_accepted": True,
            "privacy_accepted": True,
        },
    )

    # 5 consecutive failed login attempts
    for _ in range(5):
        fail_res = client.post(
            "/v1/auth/login",
            json={"email": email, "password": "WrongPassword2026!"},
        )
        assert fail_res.status_code in (401, 423)

    # 6th attempt should be HTTP 423 Locked
    locked_res = client.post(
        "/v1/auth/login",
        json={"email": email, "password": pwd},  # even with correct password!
    )
    assert locked_res.status_code == 423
    assert "verrouillé" in locked_res.json()["detail"].lower()


def test_password_reset_flow():
    email = f"reset_{os.urandom(4).hex()}@example.com"
    pwd = "StrongPassword2026!#"
    new_pwd = "BrandNewSecurePassword2026!#"

    client.post(
        "/v1/auth/register",
        json={
            "email": email,
            "password": pwd,
            "full_name": "Reset User",
            "cgu_accepted": True,
            "privacy_accepted": True,
        },
    )

    # Forgot password
    forgot_res = client.post("/v1/auth/forgot-password", json={"email": email})
    assert forgot_res.status_code == 200

    email_svc = get_email_service()
    reset_token = email_svc.get_latest_token_for(email, "reset")
    assert reset_token is not None

    # Reset password
    reset_res = client.post(
        "/v1/auth/reset-password",
        json={"token": reset_token, "new_password": new_pwd},
    )
    assert reset_res.status_code == 200

    # Old password fails
    old_res = client.post("/v1/auth/login", json={"email": email, "password": pwd})
    assert old_res.status_code == 401

    # New password succeeds
    new_res = client.post("/v1/auth/login", json={"email": email, "password": new_pwd})
    assert new_res.status_code == 200


def test_logout_and_session_invalidation():
    email = f"logout_{os.urandom(4).hex()}@example.com"
    pwd = "StrongPassword2026!#"

    client.post(
        "/v1/auth/register",
        json={
            "email": email,
            "password": pwd,
            "full_name": "Logout User",
            "cgu_accepted": True,
            "privacy_accepted": True,
        },
    )

    login_res = client.post("/v1/auth/login", json={"email": email, "password": pwd})
    token = login_res.json()["access_token"]
    refresh_cookie = login_res.cookies["refresh_token"]

    # Logout
    logout_res = client.post(
        "/v1/auth/logout",
        headers={"Authorization": f"Bearer {token}"},
        cookies={"refresh_token": refresh_cookie},
    )
    assert logout_res.status_code == 200

    # Refresh with that cookie fails
    refresh_res = client.post(
        "/v1/auth/refresh",
        cookies={"refresh_token": refresh_cookie},
    )
    assert refresh_res.status_code == 401


def test_demo_mode_endpoint():
    demo_res = client.post("/v1/auth/demo")
    assert demo_res.status_code == 200
    data = demo_res.json()
    assert data["is_demo"] is True
    assert data["role"] == "Owner"
    assert "ws_demo_" in data["workspace_id"]
    assert "refresh_token" in demo_res.cookies

    # Authenticated get me works with demo token
    me_res = client.get(
        "/v1/auth/me",
        headers={"Authorization": f"Bearer {data['access_token']}"},
    )
    assert me_res.status_code == 200
    assert me_res.json()["is_demo"] is True


def test_get_me_and_switch_workspace():
    email = f"multiws_{os.urandom(4).hex()}@example.com"
    pwd = "StrongPassword2026!#"

    reg_res = client.post(
        "/v1/auth/register",
        json={
            "email": email,
            "password": pwd,
            "full_name": "Multi WS User",
            "cgu_accepted": True,
            "privacy_accepted": True,
        },
    )
    user_id = reg_res.json()["user_id"]
    assert "workspace_id" in reg_res.json()

    # Add user to a second workspace directly in DB
    db = SessionLocal()
    try:
        repo = ContentOpsRepository(db)
        ws2 = repo.create_workspace("Second Workspace", owner_id="other_owner")
        repo.add_workspace_member(ws2.id, user_id, "Editor")
        ws2_id = ws2.id
    finally:
        db.close()

    # Login
    login_res = client.post("/v1/auth/login", json={"email": email, "password": pwd})
    token = login_res.json()["access_token"]

    # Get me
    me_res = client.get("/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_res.status_code == 200
    me_data = me_res.json()
    assert len(me_data["workspaces"]) == 2

    # Switch workspace
    switch_res = client.post(
        "/v1/auth/switch-workspace",
        headers={"Authorization": f"Bearer {token}"},
        json={"workspace_id": ws2_id},
    )
    assert switch_res.status_code == 200
    switch_data = switch_res.json()
    assert switch_data["workspace_id"] == ws2_id
    assert switch_data["role"] == "Editor"
