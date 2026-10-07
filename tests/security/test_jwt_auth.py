import os
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient
import jwt

from apps.api.main import app
from packages.security.auth import (
    create_access_token,
    decode_access_token,
    JWT_ALGORITHM,
    JWT_SECRET_KEY,
    Role
)

client = TestClient(app)


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
