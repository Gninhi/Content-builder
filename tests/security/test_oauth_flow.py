import os
import unittest.mock
import httpx
import pytest
from fastapi.testclient import TestClient

from apps.api.main import app
from packages.security.auth import create_access_token, Role
from packages.security.oauth_state import oauth_state_manager
from packages.connectors.social.vault import EncryptedOAuthTokenVault
from infra.db.database import SessionLocal
from infra.db.models import ConnectedSocialAccountModel

client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_oauth_env():
    # Set required env vars for tests
    old_env = os.environ.copy()
    os.environ["SECRET_VAULT_KEY"] = "super-secret-vault-master-key-32b!"
    os.environ["LINKEDIN_CLIENT_ID"] = "test_li_client_id"
    os.environ["LINKEDIN_CLIENT_SECRET"] = "test_li_client_secret"
    os.environ["LINKEDIN_REDIRECT_URI"] = "http://localhost:8000/v1/oauth/callback/linkedin"
    os.environ["X_CLIENT_ID"] = "test_x_client_id"
    os.environ["X_CLIENT_SECRET"] = "test_x_client_secret"
    os.environ["X_REDIRECT_URI"] = "http://localhost:8000/v1/oauth/callback/x"
    yield
    os.environ.clear()
    os.environ.update(old_env)


def test_oauth_start_requires_owner_role():
    # 1. Unauthenticated -> 401
    resp_unauth = client.get("/v1/oauth/start/linkedin")
    assert resp_unauth.status_code == 401

    # 2. Editor role -> 403 Forbidden
    editor_token = create_access_token("editor_1", Role.EDITOR.value, "ws_test_oauth")
    resp_editor = client.get(
        "/v1/oauth/start/linkedin",
        headers={"Authorization": f"Bearer {editor_token}"}
    )
    assert resp_editor.status_code == 403

    # 3. Owner role -> 200 OK
    owner_token = create_access_token("owner_1", Role.OWNER.value, "ws_test_oauth")
    resp_owner = client.get(
        "/v1/oauth/start/linkedin",
        headers={"Authorization": f"Bearer {owner_token}"}
    )
    assert resp_owner.status_code == 200
    data = resp_owner.json()
    assert data["status"] == "INITIATED"
    assert "linkedin.com/oauth/v2/authorization" in data["authorization_url"]
    assert "openid" in data["authorization_url"]
    assert "profile" in data["authorization_url"]
    assert "w_member_social" in data["authorization_url"]
    assert "state=" in data["authorization_url"]


def test_oauth_start_x_generates_pkce_challenge():
    owner_token = create_access_token("owner_1", Role.OWNER.value, "ws_test_oauth")
    resp = client.get(
        "/v1/oauth/start/x",
        headers={"Authorization": f"Bearer {owner_token}"}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "x.com/i/oauth2/authorize" in data["authorization_url"]
    assert "code_challenge=" in data["authorization_url"]
    assert "code_challenge_method=S256" in data["authorization_url"]
    assert "tweet.read" in data["authorization_url"]


def test_oauth_callback_rejects_missing_or_invalid_state():
    # 1. Missing state
    resp_no_state = client.get("/v1/oauth/callback/linkedin?code=auth_code_xyz")
    assert resp_no_state.status_code == 400
    assert "Missing required 'code' or 'state'" in resp_no_state.json()["detail"]

    # 2. Non-existent state
    resp_bogus_state = client.get("/v1/oauth/callback/linkedin?code=auth_code_xyz&state=invalid_state_123")
    assert resp_bogus_state.status_code == 400
    assert "Invalid, expired or already consumed" in resp_bogus_state.json()["detail"]


def test_oauth_callback_rejects_replayed_state():
    # Create valid state
    state = oauth_state_manager.create_state(
        provider="linkedin",
        workspace_id="ws_replay",
        user_id="user_1",
        code_verifier="test_verifier"
    )

    # First consumption succeeds
    first_res = oauth_state_manager.consume_state(state)
    assert first_res is not None

    # Immediate replay must fail (single-use)
    replay_res = oauth_state_manager.consume_state(state)
    assert replay_res is None


def test_oauth_callback_rejects_provider_mismatch():
    # Create state for LinkedIn
    state = oauth_state_manager.create_state(
        provider="linkedin",
        workspace_id="ws_mismatch",
        user_id="user_1",
        code_verifier="test_verifier"
    )

    # Attempt to use LinkedIn state on X callback
    resp = client.get(f"/v1/oauth/callback/x?code=some_code&state={state}")
    assert resp.status_code == 400
    assert "OAuth state provider mismatch" in resp.json()["detail"]


def test_oauth_callback_linkedin_full_flow_persists_in_vault():
    ws_id = "ws_li_connected"
    state = oauth_state_manager.create_state(
        provider="linkedin",
        workspace_id=ws_id,
        user_id="owner_alice",
        code_verifier="verifier_li"
    )

    def mock_handler(request: httpx.Request):
        url = str(request.url)
        if "accessToken" in url:
            assert request.method == "POST"
            return httpx.Response(200, json={
                "access_token": "secret_li_token_prod_12345",
                "expires_in": 5184000
            })
        elif "userinfo" in url:
            assert request.headers["Authorization"] == "Bearer secret_li_token_prod_12345"
            return httpx.Response(200, json={
                "sub": "linkedin_member_777",
                "name": "Alice Enterprise"
            })
        return httpx.Response(404)

    mock_client = httpx.Client(transport=httpx.MockTransport(mock_handler))

    with unittest.mock.patch("httpx.Client", return_value=mock_client):
        resp = client.get(f"/v1/oauth/callback/linkedin?code=auth_code_li_valid&state={state}")

    assert resp.status_code == 200
    res_data = resp.json()
    assert res_data["status"] == "SUCCESS"
    assert res_data["provider"] == "linkedin"
    assert res_data["account_id"] == "urn:li:person:linkedin_member_777"
    assert res_data["account_name"] == "Alice Enterprise"
    # Never expose tokens!
    assert "access_token" not in res_data
    assert "secret_li_token" not in str(res_data)

    # Verify database persistence and encryption
    db = SessionLocal()
    try:
        acc = (
            db.query(ConnectedSocialAccountModel)
            .filter(
                ConnectedSocialAccountModel.workspace_id == ws_id,
                ConnectedSocialAccountModel.provider == "linkedin"
            )
            .first()
        )
        assert acc is not None
        assert acc.status == "ACTIVE"
        assert "secret_li_token" not in acc.encrypted_token_blob
        assert acc.key_id == "v1"

        # Decrypt via vault
        vault = EncryptedOAuthTokenVault(db_session=db)
        record = vault.get_token(ws_id, "linkedin", "urn:li:person:linkedin_member_777")
        assert record is not None
        assert record["access_token"] == "secret_li_token_prod_12345"
    finally:
        db.close()


def test_oauth_callback_x_full_flow_persists_in_vault():
    ws_id = "ws_x_connected"
    state = oauth_state_manager.create_state(
        provider="x",
        workspace_id=ws_id,
        user_id="owner_bob",
        code_verifier="pkce_code_verifier_12345678901234567890"
    )

    def mock_handler(request: httpx.Request):
        url = str(request.url)
        if "/2/oauth2/token" in url:
            assert request.method == "POST"
            return httpx.Response(200, json={
                "access_token": "secret_x_token_prod_abc",
                "refresh_token": "secret_x_refresh_token_xyz",
                "expires_in": 7200,
                "scope": "tweet.read tweet.write users.read offline.access"
            })
        elif "/2/users/me" in url:
            assert request.headers["Authorization"] == "Bearer secret_x_token_prod_abc"
            return httpx.Response(200, json={
                "data": {"id": "x_id_9999", "name": "Bob Builder", "username": "bob_builds"}
            })
        return httpx.Response(404)

    mock_client = httpx.Client(transport=httpx.MockTransport(mock_handler))

    with unittest.mock.patch("httpx.Client", return_value=mock_client):
        resp = client.get(f"/v1/oauth/callback/x?code=auth_code_x_valid&state={state}")

    assert resp.status_code == 200
    res_data = resp.json()
    assert res_data["status"] == "SUCCESS"
    assert res_data["provider"] == "x"
    assert res_data["account_id"] == "@bob_builds"
    assert res_data["account_name"] == "Bob Builder"
    assert "secret_x_token" not in str(res_data)

    # Verify account listing & tenant isolation
    owner_token_bob = create_access_token("owner_bob", Role.OWNER.value, ws_id)
    resp_list = client.get(
        "/v1/oauth/accounts",
        headers={"Authorization": f"Bearer {owner_token_bob}"}
    )
    assert resp_list.status_code == 200
    accounts_bob = resp_list.json()["accounts"]
    assert any(a["account_id"] == "@bob_builds" for a in accounts_bob)

    # Other workspace cannot see Bob's account
    owner_token_other = create_access_token("owner_other", Role.OWNER.value, "ws_other")
    resp_other = client.get(
        "/v1/oauth/accounts",
        headers={"Authorization": f"Bearer {owner_token_other}"}
    )
    assert resp_other.status_code == 200
    accounts_other = resp_other.json()["accounts"]
    assert not any(a["account_id"] == "@bob_builds" for a in accounts_other)


def test_oauth_disconnect_account():
    ws_id = "ws_to_disconnect"
    db = SessionLocal()
    try:
        vault = EncryptedOAuthTokenVault(db_session=db)
        vault.store_token(
            workspace_id=ws_id,
            provider="linkedin",
            account_id="urn:li:person:to_remove",
            access_token="tok_remove"
        )
    finally:
        db.close()

    owner_token = create_access_token("owner_1", Role.OWNER.value, ws_id)
    resp = client.post(
        "/v1/oauth/disconnect/linkedin",
        headers={"Authorization": f"Bearer {owner_token}"},
        json={"account_id": "urn:li:person:to_remove"}
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "DISCONNECTED"

    # Token must be revoked in vault
    db = SessionLocal()
    try:
        vault = EncryptedOAuthTokenVault(db_session=db)
        assert vault.get_token(ws_id, "linkedin", "urn:li:person:to_remove") is None
    finally:
        db.close()
