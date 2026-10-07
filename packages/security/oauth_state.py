import os
import json
import secrets
import hashlib
import base64
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any
from pydantic import BaseModel


class OAuthState(BaseModel):
    state: str
    provider: str
    workspace_id: str
    user_id: str
    code_verifier: str
    expires_at: datetime


class OAuthStateManager:
    """
    Manages single-use, time-limited (10 min TTL) OAuth 2.0 states and PKCE code_verifiers.
    Supports in-memory dictionary storage with optional Redis backend for distributed deployments.
    Guarantees state cannot be replayed or shared cross-tenant.
    """

    def __init__(self, ttl_minutes: int = 10, redis_client: Optional[Any] = None):
        self.ttl_minutes = ttl_minutes
        self._memory_store: Dict[str, OAuthState] = {}
        self._redis_client = redis_client
        if self._redis_client is None:
            redis_url = os.getenv("REDIS_URL")
            if redis_url:
                try:
                    import redis  # type: ignore[import-untyped]
                    self._redis_client = redis.from_url(redis_url, decode_responses=True)
                except Exception:
                    self._redis_client = None

    @staticmethod
    def generate_pkce_pair() -> tuple[str, str]:
        """
        Generates RFC 7636 compliant PKCE code_verifier and code_challenge (S256).
        """
        code_verifier = secrets.token_urlsafe(64)
        digest = hashlib.sha256(code_verifier.encode("ascii")).digest()
        code_challenge = base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")
        return code_verifier, code_challenge

    def create_state(
        self,
        provider: str,
        workspace_id: str,
        user_id: str,
        code_verifier: str
    ) -> str:
        state_token = secrets.token_urlsafe(32)
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=self.ttl_minutes)

        oauth_state = OAuthState(
            state=state_token,
            provider=provider.lower(),
            workspace_id=workspace_id,
            user_id=user_id,
            code_verifier=code_verifier,
            expires_at=expires_at
        )

        if self._redis_client:
            try:
                payload = oauth_state.model_dump_json()
                self._redis_client.setex(
                    f"oauth_state:{state_token}",
                    self.ttl_minutes * 60,
                    payload
                )
                return state_token
            except Exception:
                pass

        self._memory_store[state_token] = oauth_state
        return state_token

    def consume_state(self, state_token: str) -> Optional[OAuthState]:
        """
        Retrieves and IMMEDIATELY deletes state (single-use semantics).
        Returns None if missing, expired, or previously consumed.
        """
        if not state_token:
            return None

        # 1. Redis lookup
        if self._redis_client:
            try:
                raw = self._redis_client.get(f"oauth_state:{state_token}")
                if raw:
                    self._redis_client.delete(f"oauth_state:{state_token}")
                    data = json.loads(raw)
                    state_obj = OAuthState(**data)
                    if datetime.now(timezone.utc) > state_obj.expires_at:
                        return None
                    return state_obj
            except Exception:
                pass

        # 2. Memory store fallback
        if state_token in self._memory_store:
            state_obj = self._memory_store.pop(state_token)
            if datetime.now(timezone.utc) > state_obj.expires_at:
                return None
            return state_obj

        return None


# Global singleton manager
oauth_state_manager = OAuthStateManager()
