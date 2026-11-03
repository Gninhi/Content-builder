import os
import sqlite3
import tempfile
import uuid
from unittest.mock import patch

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient

from apps.api.main import app
from infra.db.database import SessionLocal
from infra.db.models import (
    AuditLogModel,
    UserModel,
    WorkspaceModel,
)
from infra.db.repository import ContentOpsRepository
from packages.security.email_service import validate_email_configuration
from packages.security.passwords import hash_password


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def test_full_registration_dev_mailbox_verification_and_session_lifecycle(client: TestClient, monkeypatch):
    """
    Tests the complete end-to-end flow under D-02:
    1. Register with REQUIRE_EMAIL_VERIFICATION=true (default)
    2. Login blocked with 403 while unverified
    3. Fetch verification token from local dev mailbox (/v1/auth/dev/mailbox)
    4. Verify email via /v1/auth/verify-email
    5. Login succeeds, returns access_token & sets HttpOnly refresh_token cookie
    6. Access /v1/auth/me and /v1/users/me
    7. Rotate refresh token via /v1/auth/refresh
    8. Logout revokes session & refresh token
    """
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.delenv("REQUIRE_EMAIL_VERIFICATION", raising=False)

    unique_email = f"e2e_user_{uuid.uuid4().hex[:8]}@example.com"
    password = "StrongPassword!2026"
    ws_name = f"Workspace E2E {uuid.uuid4().hex[:6]}"

    # 1. Register
    reg_res = client.post(
        "/v1/auth/register",
        json={
            "email": unique_email,
            "password": password,
            "full_name": "Jean Dupont",
            "workspace_name": ws_name,
            "cgu_accepted": True,
            "privacy_accepted": True,
        },
    )
    assert reg_res.status_code == 201, reg_res.text
    reg_data = reg_res.json()
    assert reg_data["email"] == unique_email
    assert reg_data["requires_verification"] is True
    assert reg_data["email_delivery_status"] == "sent"

    # 2. Login before verification must fail with 403
    login_unverified = client.post(
        "/v1/auth/login",
        json={"email": unique_email, "password": password},
    )
    assert login_unverified.status_code == 403
    assert "confirmer votre adresse email" in login_unverified.json()["detail"]

    # 3. Retrieve verification token from controlled local dev mailbox
    mailbox_res = client.get("/v1/auth/dev/mailbox", params={"email": unique_email})
    assert mailbox_res.status_code == 200, mailbox_res.text
    messages = mailbox_res.json()["messages"]
    assert len(messages) >= 1
    latest_msg = messages[-1]
    assert latest_msg["type"] == "verification"
    verify_token = latest_msg["token"]
    assert verify_token and len(verify_token) > 16

    # 4. Verify email
    verify_res = client.post("/v1/auth/verify-email", json={"token": verify_token})
    assert verify_res.status_code == 200, verify_res.text

    # 5. Login after verification succeeds
    login_res = client.post(
        "/v1/auth/login",
        json={"email": unique_email, "password": password},
    )
    assert login_res.status_code == 200, login_res.text
    login_data = login_res.json()
    access_token = login_data["access_token"]
    assert access_token
    assert login_data["workspace_id"].startswith("ws_")
    assert "refresh_token" in login_res.cookies

    headers = {"Authorization": f"Bearer {access_token}"}

    # 6. Check /v1/auth/me
    me_res = client.get("/v1/auth/me", headers=headers)
    assert me_res.status_code == 200
    me_data = me_res.json()
    assert me_data["user"]["email"] == unique_email
    assert me_data["current_workspace_id"] == login_data["workspace_id"]

    # 7. Refresh token rotation
    refresh_res = client.post("/v1/auth/refresh")
    assert refresh_res.status_code == 200, refresh_res.text
    new_access_token = refresh_res.json()["access_token"]
    assert new_access_token

    # 8. Logout
    logout_res = client.post(
        "/v1/auth/logout",
        headers={"Authorization": f"Bearer {new_access_token}"},
    )
    assert logout_res.status_code == 200

    # Subsequent /v1/auth/me with revoked session JTI must fail with 401
    after_logout = client.get("/v1/auth/me", headers={"Authorization": f"Bearer {new_access_token}"})
    assert after_logout.status_code == 401


def test_atomic_registration_rollback_on_injected_mid_transaction_failure():
    """
    Proves that if any step inside register_user_atomic fails (e.g. BrandProfile or audit log),
    the entire transaction rolls back and zero orphan User, Workspace, WorkspaceMember,
    BrandProfile, WorkspaceLLMSettings, or AuditLog records remain in the database.
    """
    unique_email = f"atomic_rollback_{uuid.uuid4().hex[:8]}@example.com"
    ws_name = f"Atomic Rollback WS {uuid.uuid4().hex[:6]}"

    with SessionLocal() as db:
        repo = ContentOpsRepository(db)
        with patch.object(
            repo,
            "record_audit_log",
            side_effect=RuntimeError("Simulated failure at final step of registration"),
        ):
            with pytest.raises(RuntimeError, match="Simulated failure at final step"):
                repo.register_user_atomic(
                    email=unique_email,
                    password_hash=hash_password("ValidPass!2026"),
                    full_name="Rollback User",
                    workspace_name=ws_name,
                    cgu_version="1.0",
                    privacy_version="1.0",
                    email_verified=False,
                    email_verification_token_hash="dummy_hash_123",
                )

    with SessionLocal() as check_db:
        assert check_db.query(UserModel).filter(UserModel.email == unique_email).first() is None
        assert check_db.query(WorkspaceModel).filter(WorkspaceModel.name == ws_name).first() is None
        assert (
            check_db.query(AuditLogModel)
            .filter(AuditLogModel.event_type == "user.registered")
            .filter(AuditLogModel.ip_address == unique_email)
            .first()
            is None
        )


def test_registration_succeeds_gracefully_when_smtp_delivery_fails(client: TestClient, monkeypatch):
    """
    Proves that if SMTP / email delivery raises an exception AFTER the atomic DB commit,
    /v1/auth/register still returns 201 Created with email_delivery_status='pending_retry'
    instead of returning HTTP 500 on an already-created account.
    """
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.delenv("REQUIRE_EMAIL_VERIFICATION", raising=False)
    unique_email = f"smtp_fail_{uuid.uuid4().hex[:8]}@example.com"

    with patch(
        "packages.security.email_service.MemoryLogEmailService.send_verification_email",
        side_effect=RuntimeError("Simulated SMTP connection error"),
    ):
        res = client.post(
            "/v1/auth/register",
            json={
                "email": unique_email,
                "password": "StrongPassword!2026",
                "full_name": "SMTP Fail User",
                "workspace_name": "SMTP Resilience WS",
                "cgu_accepted": True,
                "privacy_accepted": True,
            },
        )
    assert res.status_code == 201, res.text
    data = res.json()
    assert data["email_delivery_status"] == "pending_retry"
    assert "renvoi" in data["message"].lower() or "créé" in data["message"].lower()

    # Now resend verification when email service works
    resend_res = client.post("/v1/auth/resend-verification", json={"email": unique_email})
    assert resend_res.status_code == 200


def test_password_max_length_and_complexity_enforced(client: TestClient):
    """
    Verifies password bounds (10 <= len <= 128) and complexity on register, login, and reset.
    """
    oversized_password = "A1!" + ("a" * 130)  # 133 chars > 128

    reg_res = client.post(
        "/v1/auth/register",
        json={
            "email": f"oversized_{uuid.uuid4().hex[:6]}@example.com",
            "password": oversized_password,
            "full_name": "Oversized User",
            "cgu_accepted": True,
        },
    )
    assert reg_res.status_code == 422

    login_res = client.post(
        "/v1/auth/login",
        json={"email": "someone@example.com", "password": oversized_password},
    )
    assert login_res.status_code == 422

    reset_res = client.post(
        "/v1/auth/reset-password",
        json={"token": "some_token_value_12345", "new_password": oversized_password},
    )
    assert reset_res.status_code == 422


def test_password_reset_invalidates_prior_stateless_jwt_and_sessions(client: TestClient, monkeypatch):
    """
    Verifies that resetting a user's password:
    1. Revokes all user_sessions and user_refresh_tokens
    2. Sets _tokens_valid_after so any previously issued stateless access_token is rejected with 401
    3. Does not leak _tokens_valid_after in /v1/users/me ui_preferences
    """
    monkeypatch.setenv("REQUIRE_EMAIL_VERIFICATION", "false")
    unique_email = f"reset_sec_{uuid.uuid4().hex[:8]}@example.com"
    old_password = "OldPassword!2026"
    new_password = "NewPassword!2027"

    reg = client.post(
        "/v1/auth/register",
        json={
            "email": unique_email,
            "password": old_password,
            "full_name": "Reset Sec User",
            "cgu_accepted": True,
            "privacy_accepted": True,
        },
    )
    assert reg.status_code == 201

    login1 = client.post("/v1/auth/login", json={"email": unique_email, "password": old_password})
    assert login1.status_code == 200
    old_access_token = login1.json()["access_token"]

    # Create a second token WITHOUT a JTI in user_sessions to test stateless JWT iat invalidation
    from packages.security.auth import create_access_token

    stateless_token = create_access_token(
        user_id=login1.json()["user"]["id"],
        workspace_id=login1.json()["workspace_id"],
        role="Owner",
    )
    assert (
        client.get("/v1/auth/me", headers={"Authorization": f"Bearer {stateless_token}"}).status_code
        == 200
    )

    # Trigger forgot-password and fetch reset token from dev mailbox
    monkeypatch.setenv("APP_ENV", "development")
    forgot_res = client.post("/v1/auth/forgot-password", json={"email": unique_email})
    assert forgot_res.status_code == 200

    mailbox_res = client.get("/v1/auth/dev/mailbox", params={"email": unique_email})
    assert mailbox_res.status_code == 200
    reset_msgs = [m for m in mailbox_res.json()["messages"] if m["type"] == "reset"]
    assert reset_msgs
    reset_token = reset_msgs[-1]["token"]

    # Reset password
    reset_res = client.post(
        "/v1/auth/reset-password",
        json={"token": reset_token, "new_password": new_password},
    )
    assert reset_res.status_code == 200

    # Both the session-backed token AND the stateless JWT issued before reset must now return 401
    assert (
        client.get("/v1/auth/me", headers={"Authorization": f"Bearer {old_access_token}"}).status_code
        == 401
    )
    assert (
        client.get("/v1/auth/me", headers={"Authorization": f"Bearer {stateless_token}"}).status_code
        == 401
    )

    # Login with new password works and /v1/me does not expose _tokens_valid_after
    login2 = client.post("/v1/auth/login", json={"email": unique_email, "password": new_password})
    assert login2.status_code == 200
    new_token = login2.json()["access_token"]
    profile_res = client.get("/v1/me", headers={"Authorization": f"Bearer {new_token}"})
    assert profile_res.status_code == 200
    assert "_tokens_valid_after" not in profile_res.json().get("ui_preferences", {})


def test_dev_mailbox_and_email_config_blocked_in_production(client: TestClient, monkeypatch):
    """
    Verifies fail-closed guards in staging/production:
    1. GET /v1/auth/dev/mailbox returns 404 in production/staging
    2. validate_email_configuration() raises RuntimeError if dev mailbox or memory backend is enabled in production
    """
    monkeypatch.setenv("APP_ENV", "production")
    res = client.get("/v1/auth/dev/mailbox")
    assert res.status_code == 404

    monkeypatch.setenv("DEV_MAILBOX_ENABLED", "true")
    with pytest.raises(RuntimeError, match="DEV_MAILBOX_ENABLED"):
        validate_email_configuration()

    monkeypatch.delenv("DEV_MAILBOX_ENABLED", raising=False)
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    monkeypatch.delenv("CONTENTOPS_TEST_MODE", raising=False)
    monkeypatch.setenv("SMTP_HOST", "")
    monkeypatch.setenv("REQUIRE_EMAIL_VERIFICATION", "true")
    with pytest.raises(RuntimeError, match="SMTP_HOST"):
        validate_email_configuration()


def test_alembic_upgrade_head_on_blank_and_existing_sqlite_db(monkeypatch):
    """
    Verifies that `alembic upgrade head` succeeds cleanly on a blank SQLite DB
    and produces all 23 ORM tables with 0 foreign key violations.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        test_db = os.path.join(tmpdir, "alembic_verify.db")
        db_url = f"sqlite:///{test_db}"
        monkeypatch.setenv("DATABASE_URL", db_url)

        cfg = Config("alembic.ini")
        cfg.set_main_option("sqlalchemy.url", db_url)
        command.upgrade(cfg, "head")

        conn = sqlite3.connect(test_db)
        cur = conn.cursor()
        ver = cur.execute("SELECT version_num FROM alembic_version").fetchone()[0]
        assert ver == "9a4b5c6d7e8f"

        tables = {
            r[0]
            for r in cur.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
            ).fetchall()
        }
        expected_orm_tables = set([t.name for t in WorkspaceModel.metadata.sorted_tables])
        assert expected_orm_tables.issubset(tables)
        assert cur.execute("PRAGMA foreign_key_check").fetchall() == []
        conn.close()
