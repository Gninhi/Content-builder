import os
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient
import jwt

import pytest
from apps.api.main import app
from packages.security.auth import (
    create_access_token,
    decode_access_token,
    JWT_ALGORITHM,
    JWT_SECRET_KEY,
    Role
)
from infra.db.database import SessionLocal
from infra.db.models import WorkspaceModel, BrandProfileModel

client = TestClient(app)


@pytest.fixture(autouse=True)
def ensure_default_brand_profile():
    """Ensures ws_default and brand profile exist in database for authenticated endpoints."""
    with SessionLocal() as db:
        ws = db.query(WorkspaceModel).filter_by(id="ws_default").first()
        if not ws:
            db.add(WorkspaceModel(id="ws_default", name="Default Workspace", owner_id="owner_1"))
            db.commit()
        bp = db.query(BrandProfileModel).filter_by(workspace_id="ws_default").first()
        if not bp:
            db.add(BrandProfileModel(
                id="bp_default",
                workspace_id="ws_default",
                version=1,
                audience=["Tech"],
                voice="Professional",
                pillars=["AI"],
                prohibited_topics=[],
                cta_policy={}
            ))
            db.commit()
    yield


def test_forged_x_user_role_header_without_jwt_is_rejected():
    """Security check: X-User-Role header must not be trusted without valid JWT."""
    response = client.get(
        "/v1/brand-profiles/ws_default",
        headers={
            "X-User-Role": "Owner",
            "X-Workspace-Id": "ws_default"
        }
    )
    assert response.status_code == 401, f"Expected 401 Unauthorized, got {response.status_code}"


def test_tampered_jwt_signature_is_rejected():
    """Security check: Tampered signature must raise 401."""
    token = create_access_token(user_id="user_attacker", role=Role.OWNER, workspace_id="ws_default")
    tampered_token = token[:-5] + "abcde"
    response = client.get(
        "/v1/brand-profiles/ws_default",
        headers={"Authorization": f"Bearer {tampered_token}"}
    )
    assert response.status_code == 401


def test_expired_jwt_is_rejected():
    """Security check: Expired tokens must be rejected."""
    expired_token = create_access_token(
        user_id="user_old",
        role=Role.OWNER,
        workspace_id="ws_default",
        expires_delta=timedelta(seconds=-10)
    )
    response = client.get(
        "/v1/brand-profiles/ws_default",
        headers={"Authorization": f"Bearer {expired_token}"}
    )
    assert response.status_code == 401


def test_invalid_issuer_or_audience_is_rejected():
    """Security check: JWT with wrong issuer or audience must fail."""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": "user_1",
        "role": Role.OWNER,
        "workspace_id": "ws_default",
        "iss": "rogue-issuer",
        "aud": "rogue-audience",
        "exp": (now + timedelta(hours=1)).timestamp()
    }
    rogue_token = jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    response = client.get(
        "/v1/brand-profiles/ws_default",
        headers={"Authorization": f"Bearer {rogue_token}"}
    )
    assert response.status_code == 401


def test_valid_jwt_authenticates_and_extracts_claims():
    """Valid JWT extracts workspace_id and role from claims."""
    token = create_access_token(user_id="user_valid", role=Role.EDITOR, workspace_id="ws_default")
    response = client.get(
        "/v1/brand-profiles/ws_default",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    claims = decode_access_token(token)
    assert claims["sub"] == "user_valid"
    assert claims["role"] == Role.EDITOR
    assert claims["workspace_id"] == "ws_default"


def test_rbac_viewer_cannot_approve_content():
    """RBAC check: Viewer role cannot approve content."""
    token = create_access_token(user_id="user_viewer", role=Role.VIEWER, workspace_id="ws_default")
    response = client.post(
        "/v1/content/var_dummy/approve",
        headers={"Authorization": f"Bearer {token}"},
        json={"decision": "approve", "reviewer_id": "user_viewer"}
    )
    assert response.status_code == 403, f"Expected 403 Forbidden for Viewer, got {response.status_code}"


def test_dev_token_endpoint_behavior():
    """Dev token generation must work when ENV=dev and fail in production."""
    os.environ["ENV"] = "dev"
    res_dev = client.post(
        "/v1/auth/dev-token",
        json={"user_id": "dev_user", "role": "Editor", "workspace_id": "ws_default"}
    )
    assert res_dev.status_code == 200
    assert "access_token" in res_dev.json()

    os.environ["ENV"] = "production"
    res_prod = client.post(
        "/v1/auth/dev-token",
        json={"user_id": "dev_user", "role": "Editor", "workspace_id": "ws_default"}
    )
    assert res_prod.status_code in [403, 404]
    os.environ["ENV"] = "dev"


def test_jwt_key_rotation_with_kid(monkeypatch):
    """Verifies that kid header allows validating tokens signed with rotated keys."""
    from packages.security.auth import _KEY_RING
    _KEY_RING["key_v1"] = "primary-secret-key-32-bytes-minimum-length!"
    _KEY_RING["key_v2"] = "rotated-secondary-secret-32-bytes-length!!"

    token_v1 = create_access_token(user_id="user_1", role=Role.EDITOR, workspace_id="ws_1", key_id="key_v1")
    token_v2 = create_access_token(user_id="user_2", role=Role.EDITOR, workspace_id="ws_1", key_id="key_v2")

    claims_1 = decode_access_token(token_v1)
    claims_2 = decode_access_token(token_v2)

    assert claims_1["sub"] == "user_1"
    assert claims_2["sub"] == "user_2"


def test_jwt_production_validation_fail_closed(monkeypatch):
    """Enforces fail-closed refusal when production starts with weak or default JWT secret."""
    from packages.security.auth import validate_jwt_configuration, DEFAULT_DEV_JWT_SECRET
    import pytest

    monkeypatch.setenv("ENV", "production")
    monkeypatch.setenv("JWT_SECRET_KEY", DEFAULT_DEV_JWT_SECRET)
    with pytest.raises(RuntimeError) as exc:
        validate_jwt_configuration()
    assert "Production Startup Denied" in str(exc.value)

    monkeypatch.setenv("JWT_SECRET_KEY", "too-short")
    with pytest.raises(RuntimeError) as exc2:
        validate_jwt_configuration()
    assert "Production Startup Denied" in str(exc2.value)

    monkeypatch.setenv("JWT_SECRET_KEY", "a-very-strong-production-secret-key-for-contentops-2026-strict")
    validate_jwt_configuration()  # Must not raise


def test_enterprise_login_with_valid_password():
    """Enterprise login: Valid email and Argon2id password issues signed JWT."""
    from infra.db.repository import ContentOpsRepository
    from packages.security.passwords import hash_password

    with SessionLocal() as db:
        repo = ContentOpsRepository(db)
        user = repo.get_user_by_email("login_test@contentops.internal")
        if not user:
            user = repo.create_user(
                user_id="user_login_test",
                email="login_test@contentops.internal",
                full_name="Login Tester",
                password_hash=hash_password("SecurePassword2026!"),
            )
            repo.add_workspace_member(
                workspace_id="ws_default",
                user_id="user_login_test",
                role="Owner",
            )
        else:
            repo.update_user_password(user.id, hash_password("SecurePassword2026!"))

    res = client.post(
        "/v1/auth/login",
        json={
            "email": "login_test@contentops.internal",
            "password": "SecurePassword2026!",
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert "access_token" in data
    assert data["user_id"] == "user_login_test"
    assert data["role"] == "Owner"
    assert data["workspace_id"] == "ws_default"

    # Validate claims
    claims = decode_access_token(data["access_token"])
    assert claims["sub"] == "user_login_test"
    assert claims["role"] == "Owner"
    assert claims["workspace_id"] == "ws_default"
    assert "jti" in claims


def test_enterprise_login_with_invalid_password_returns_401():
    """Enterprise login: Incorrect password returns 401 Unauthorized."""
    res = client.post(
        "/v1/auth/login",
        json={
            "email": "login_test@contentops.internal",
            "password": "WrongPassword999!",
        },
    )
    assert res.status_code == 401
    assert "invalide" in res.json()["detail"].lower()


def test_enterprise_login_with_unknown_email_returns_401():
    """Enterprise login: Unknown email returns 401 Unauthorized without disclosing user existence."""
    res = client.post(
        "/v1/auth/login",
        json={
            "email": "nonexistent_user@contentops.internal",
            "password": "SomePassword123!",
        },
    )
    assert res.status_code == 401


