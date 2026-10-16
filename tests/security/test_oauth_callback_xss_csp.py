import pytest
import re
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from apps.api.main import app
from infra.db.database import init_db, SessionLocal
from infra.db.repository import ContentOpsRepository
from packages.security.oauth_state import oauth_state_manager, OAuthState

client = TestClient(app)


def test_oauth_callback_error_page_xss_and_csp():
    """H10: OAuth callback error page must escape error strings, use CSP nonce, and have no inline onclick."""
    xss_payload = '<script>alert("xss")</script><img src=x onerror=alert(1)>'
    
    resp = client.get(
        f"/v1/oauth/callback/linkedin?error={xss_payload}&error_description={xss_payload}",
        headers={"Accept": "text/html"}
    )
    assert resp.status_code == 400
    html = resp.text

    # 1. Must NOT contain raw unescaped XSS payload
    assert "<script>alert(\"xss\")</script>" not in html
    assert "<img src=x onerror=alert(1)>" not in html
    assert "&lt;script&gt;" in html or "\\u003cscript\\u003e" in html

    # 2. Must not contain inline onclick event handler
    assert "onclick=" not in html

    # 3. Must have a CSP header with script-src nonce
    csp = resp.headers.get("content-security-policy", "")
    assert "script-src" in csp
    assert "nonce-" in csp

    # 4. The script tag in the page must match the nonce in the CSP header
    nonce_match = re.search(r"nonce-([A-Za-z0-9_-]+)", csp)
    assert nonce_match, "CSP must contain a nonce"
    nonce = nonce_match.group(1)
    assert f'nonce="{nonce}"' in html


def test_oauth_callback_success_page_xss_and_csp():
    """H10: OAuth callback success page escapes account_name and conforms to strict CSP without inline onclick."""
    xss_account_name = 'Attacker"><script>alert(1)</script>\'; alert(2); //'
    state_token = "valid_state_xss_test"

    with patch("apps.api.routers.oauth.oauth_state_manager.consume_state") as mock_consume, \
         patch("apps.api.routers.oauth.EncryptedOAuthTokenVault") as mock_vault, \
         patch("apps.api.routers.oauth.httpx.Client") as mock_http_client_cls:

        mock_consume.return_value = OAuthState(
            state=state_token,
            provider="linkedin",
            workspace_id="ws_default",
            user_id="usr_test",
            created_at=100000.0,
            expires_at=200000.0,
            code_verifier="test_verifier",
            redirect_uri="http://localhost:8000/v1/oauth/callback/linkedin"
        )

        mock_http_inst = MagicMock()
        mock_http_client_cls.return_value.__enter__.return_value = mock_http_inst

        # Mock token exchange
        token_resp = MagicMock()
        token_resp.status_code = 200
        token_resp.json.return_value = {
            "access_token": "mock_token",
            "expires_in": 3600
        }
        mock_http_inst.post.return_value = token_resp

        # Mock userinfo with malicious XSS account_name
        userinfo_resp = MagicMock()
        userinfo_resp.status_code = 200
        userinfo_resp.json.return_value = {
            "sub": "linkedin_acc_123",
            "name": xss_account_name,
            "email": "test@example.com"
        }
        mock_http_inst.get.return_value = userinfo_resp

        resp = client.get(
            f"/v1/oauth/callback/linkedin?code=auth_code_123&state={state_token}",
            headers={"Accept": "text/html"}
        )
        assert resp.status_code == 200
        html = resp.text

        # 1. No raw unescaped XSS in HTML body
        assert '<script>alert(1)</script>' not in html
        assert 'Attacker&quot;&gt;' in html or 'Attacker&quot;' in html or '&lt;script&gt;' in html

        # 2. No inline onclick
        assert "onclick=" not in html

        # 3. CSP with nonce
        csp = resp.headers.get("content-security-policy", "")
        assert "script-src" in csp
        assert "nonce-" in csp

        # 4. Nonce in html matches CSP
        nonce_match = re.search(r"nonce-([A-Za-z0-9_-]+)", csp)
        assert nonce_match
        nonce = nonce_match.group(1)
        assert f'nonce="{nonce}"' in html
