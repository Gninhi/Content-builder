import os
import urllib.parse
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any
import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.orm import Session

from apps.api.dependencies import require_roles, get_current_user, UserContext
from infra.db.database import get_db
from infra.db.models import ConnectedSocialAccountModel
from packages.connectors.social.models import SocialProvider
from packages.connectors.social.vault import EncryptedOAuthTokenVault
from packages.security.oauth_state import oauth_state_manager

router = APIRouter(prefix="/v1/oauth", tags=["OAuth 2.0 Management"])


@router.get("/start/{provider}")
def start_oauth_flow(
    provider: str,
    user: UserContext = Depends(require_roles("Owner")),
):
    """
    Initiates OAuth 2.0 authorization code flow with PKCE for social accounts.
    Strictly restricted to users with OWNER role.
    Generates single-use state and binds it securely to (provider, workspace_id, user_id).
    """
    provider_clean = provider.strip().lower()
    if provider_clean not in (SocialProvider.LINKEDIN.value, SocialProvider.X.value):
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported OAuth provider '{provider}'. Supported providers: linkedin, x"
        )

    code_verifier, code_challenge = oauth_state_manager.generate_pkce_pair()
    state = oauth_state_manager.create_state(
        provider=provider_clean,
        workspace_id=user.workspace_id,
        user_id=user.user_id,
        code_verifier=code_verifier
    )

    if provider_clean == SocialProvider.LINKEDIN.value:
        client_id = os.getenv("LINKEDIN_CLIENT_ID")
        redirect_uri = os.getenv(
            "LINKEDIN_REDIRECT_URI",
            "http://localhost:8000/v1/oauth/callback/linkedin"
        )
        if not client_id:
            raise HTTPException(
                status_code=500,
                detail="LINKEDIN_CLIENT_ID is not configured in environment."
            )
        
        # Scopes: openid profile w_member_social (r_liteprofile is deprecated)
        scopes = "openid profile w_member_social"
        params = {
            "response_type": "code",
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "state": state,
            "scope": scopes
        }
        auth_url = f"https://www.linkedin.com/oauth/v2/authorization?{urllib.parse.urlencode(params)}"

    else:  # X (Twitter)
        client_id = os.getenv("X_CLIENT_ID") or os.getenv("X_API_KEY")
        redirect_uri = os.getenv(
            "X_REDIRECT_URI",
            "http://localhost:8000/v1/oauth/callback/x"
        )
        if not client_id:
            raise HTTPException(
                status_code=500,
                detail="X_CLIENT_ID is not configured in environment."
            )

        # Scopes: tweet.read tweet.write users.read offline.access
        scopes = "tweet.read tweet.write users.read offline.access"
        params = {
            "response_type": "code",
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "state": state,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
            "scope": scopes
        }
        auth_url = f"https://x.com/i/oauth2/authorize?{urllib.parse.urlencode(params)}"

    return {
        "status": "INITIATED",
        "provider": provider_clean,
        "workspace_id": user.workspace_id,
        "authorization_url": auth_url,
        "state": state
    }


@router.get("/callback/{provider}")
def oauth_callback(
    provider: str,
    code: Optional[str] = Query(None),
    state: Optional[str] = Query(None),
    error: Optional[str] = Query(None),
    error_description: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """
    Public OAuth 2.0 callback endpoint invoked by LinkedIn and X upon user authorization.
    Verifies and consumes state single-use, performs server-to-server token exchange,
    and immediately persists encrypted tokens in the database vault with AES-GCM and key rotation ID.
    Never exposes or logs access tokens, refresh tokens, or code verifiers.
    """
    provider_clean = provider.strip().lower()
    if error:
        raise HTTPException(
            status_code=400,
            detail=f"OAuth authorization denied by provider: {error} ({error_description or 'No detail'})"
        )

    if not code or not state:
        raise HTTPException(
            status_code=400,
            detail="Missing required 'code' or 'state' parameter in OAuth callback."
        )

    # 1. Consume state atomically (prevents CSRF and replay attacks)
    oauth_state = oauth_state_manager.consume_state(state)
    if not oauth_state:
        raise HTTPException(
            status_code=400,
            detail="Invalid, expired or already consumed OAuth state."
        )

    if oauth_state.provider != provider_clean:
        raise HTTPException(
            status_code=400,
            detail=f"OAuth state provider mismatch (expected {oauth_state.provider}, got {provider_clean})."
        )

    vault = EncryptedOAuthTokenVault(db_session=db)
    http_timeout = httpx.Timeout(15.0)

    # 2. Server-to-server token exchange
    if provider_clean == SocialProvider.LINKEDIN.value:
        client_id = os.getenv("LINKEDIN_CLIENT_ID")
        client_secret = os.getenv("LINKEDIN_CLIENT_SECRET")
        redirect_uri = os.getenv(
            "LINKEDIN_REDIRECT_URI",
            "http://localhost:8000/v1/oauth/callback/linkedin"
        )
        if not client_id or not client_secret:
            raise HTTPException(status_code=500, detail="LinkedIn credentials missing on server.")

        token_url = "https://www.linkedin.com/oauth/v2/accessToken"
        data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri,
            "client_id": client_id,
            "client_secret": client_secret,
        }
        headers = {"Content-Type": "application/x-www-form-urlencoded"}

        try:
            with httpx.Client(timeout=http_timeout) as client:
                resp = client.post(token_url, data=data, headers=headers)
                if resp.status_code != 200:
                    raise HTTPException(
                        status_code=400,
                        detail=f"LinkedIn token exchange failed (HTTP {resp.status_code})."
                    )
                token_data = resp.json()
                access_token = token_data.get("access_token")
                expires_in = token_data.get("expires_in", 5184000)  # ~60 days

                # Fetch member userinfo
                u_resp = client.get(
                    "https://api.linkedin.com/v2/userinfo",
                    headers={"Authorization": f"Bearer {access_token}"}
                )
                if u_resp.status_code != 200:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Failed to fetch LinkedIn userinfo: {u_resp.status_code}"
                    )
                user_info = u_resp.json()
                sub = user_info.get("sub", "unknown_member")
                name = user_info.get("name", sub)

        except httpx.RequestError as exc:
            raise HTTPException(status_code=502, detail=f"Network error contacting LinkedIn: {str(exc)}")

        account_id = f"urn:li:person:{sub}"
        account_name = str(name)
        granted_scopes = ["openid", "profile", "w_member_social"]
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=int(expires_in))

        # Store in encrypted database vault
        vault.store_token(
            workspace_id=oauth_state.workspace_id,
            provider=provider_clean,
            account_id=account_id,
            access_token=str(access_token),
            refresh_token=None,
            expires_at=expires_at,
            scopes=granted_scopes,
            account_name=account_name
        )

    else:  # X (Twitter)
        client_id = os.getenv("X_CLIENT_ID") or os.getenv("X_API_KEY")
        client_secret = os.getenv("X_CLIENT_SECRET") or os.getenv("X_API_SECRET")
        redirect_uri = os.getenv(
            "X_REDIRECT_URI",
            "http://localhost:8000/v1/oauth/callback/x"
        )
        if not client_id:
            raise HTTPException(status_code=500, detail="X credentials missing on server.")

        token_url = "https://api.x.com/2/oauth2/token"
        data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri,
            "code_verifier": oauth_state.code_verifier,
            "client_id": client_id,
        }
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        try:
            with httpx.Client(timeout=http_timeout) as client:
                if client_secret:
                    resp = client.post(token_url, data=data, headers=headers, auth=(client_id, client_secret))
                else:
                    resp = client.post(token_url, data=data, headers=headers)
                if resp.status_code != 200:
                    raise HTTPException(
                        status_code=400,
                        detail=f"X token exchange failed (HTTP {resp.status_code})."
                    )
                token_data = resp.json()
                access_token = token_data.get("access_token")
                refresh_token = token_data.get("refresh_token")
                expires_in = token_data.get("expires_in", 7200)
                raw_scope = token_data.get("scope", "")

                # Fetch authenticated profile
                p_resp = client.get(
                    "https://api.x.com/2/users/me",
                    headers={"Authorization": f"Bearer {access_token}"}
                )
                if p_resp.status_code == 200:
                    profile_data = p_resp.json().get("data", {})
                    account_id = f"@{profile_data.get('username', profile_data.get('id', 'unknown'))}"
                    account_name = str(profile_data.get("name", account_id))
                else:
                    account_id = "unknown_x_user"
                    account_name = "X Account"

        except httpx.RequestError as exc:
            raise HTTPException(status_code=502, detail=f"Network error contacting X: {str(exc)}")

        granted_scopes = raw_scope.split(" ") if raw_scope else ["tweet.read", "tweet.write", "users.read", "offline.access"]
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=int(expires_in))

        # Store in encrypted database vault
        vault.store_token(
            workspace_id=oauth_state.workspace_id,
            provider=provider_clean,
            account_id=account_id,
            access_token=str(access_token),
            refresh_token=str(refresh_token) if refresh_token else None,
            expires_at=expires_at,
            scopes=granted_scopes,
            account_name=account_name
        )

    return {
        "status": "SUCCESS",
        "message": f"Successfully connected and verified {provider_clean.upper()} account.",
        "provider": provider_clean,
        "workspace_id": oauth_state.workspace_id,
        "account_id": account_id,
        "account_name": account_name,
        "scopes": granted_scopes,
        "expires_at": expires_at.isoformat()
    }


@router.get("/accounts")
def list_connected_accounts(
    user: UserContext = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Lists all connected social accounts for the caller's workspace.
    Guarantees no raw tokens or encrypted blobs are exposed in responses.
    """
    accounts = (
        db.query(ConnectedSocialAccountModel)
        .filter(ConnectedSocialAccountModel.workspace_id == user.workspace_id)
        .all()
    )

    return {
        "workspace_id": user.workspace_id,
        "count": len(accounts),
        "accounts": [
            {
                "id": str(acc.id),
                "provider": str(acc.provider),
                "account_id": str(acc.account_id),
                "account_name": str(acc.account_name),
                "status": str(acc.status),
                "scopes": acc.scopes or [],
                "expires_at": acc.expires_at.isoformat() if acc.expires_at else None,
                "created_at": acc.created_at.isoformat() if acc.created_at else None,
                "updated_at": acc.updated_at.isoformat() if acc.updated_at else None,
            }
            for acc in accounts
        ]
    }


@router.post("/disconnect/{provider}")
def disconnect_account(
    provider: str,
    account_id: str = Body(..., embed=True),
    user: UserContext = Depends(require_roles("Owner")),
    db: Session = Depends(get_db)
):
    """
    Revokes and permanently disconnects a social account.
    Restricted to workspace OWNER role.
    """
    provider_clean = provider.strip().lower()
    vault = EncryptedOAuthTokenVault(db_session=db)
    revoked = vault.revoke_token(
        workspace_id=user.workspace_id,
        provider=provider_clean,
        account_id=account_id
    )

    if not revoked:
        raise HTTPException(
            status_code=404,
            detail=f"Account '{account_id}' for provider '{provider_clean}' not found in workspace."
        )

    return {
        "status": "DISCONNECTED",
        "provider": provider_clean,
        "workspace_id": user.workspace_id,
        "account_id": account_id
    }
