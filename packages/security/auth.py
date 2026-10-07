import os
from typing import Dict, Any, Optional, Set, Union
from datetime import datetime, timezone, timedelta
from enum import Enum
import jwt


class Role(str, Enum):
    OWNER = "Owner"
    EDITOR = "Editor"
    VIEWER = "Viewer"
    SERVICE_AGENT = "ServiceAgent"


ROLE_PERMISSIONS: Dict[Role, Set[str]] = {
    Role.OWNER: {"read", "write", "approve_variant", "publish", "delete", "admin"},
    Role.EDITOR: {"read", "write", "approve_variant", "publish"},
    Role.VIEWER: {"read"},
    Role.SERVICE_AGENT: {"read", "write", "publish"},
}


DEFAULT_DEV_JWT_SECRET = "contentops-hardened-jwt-secret-key-must-be-rotated-in-production-2026"
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", DEFAULT_DEV_JWT_SECRET)
JWT_KEY_ID = os.getenv("JWT_KEY_ID", "key_v1")
JWT_ALGORITHM = "HS256"
JWT_ISSUER = "contentops-auth"
JWT_AUDIENCE = "contentops-api"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))

# Key ring for key rotation support: kid -> secret_key
_KEY_RING: Dict[str, str] = {
    JWT_KEY_ID: JWT_SECRET_KEY,
}
if os.getenv("JWT_ROTATION_KEYS"):
    for pair in os.getenv("JWT_ROTATION_KEYS", "").split(","):
        if ":" in pair:
            kid, ksecret = pair.split(":", 1)
            _KEY_RING[kid.strip()] = ksecret.strip()


def validate_jwt_configuration() -> None:
    """
    Enforces fail-closed validation of JWT keys in production.
    Raises RuntimeError if insecure defaults or weak keys are used.
    """
    env = (os.getenv("ENV") or "production").strip().lower()
    if env == "production":
        secret = os.getenv("JWT_SECRET_KEY", "")
        if not secret or secret == DEFAULT_DEV_JWT_SECRET or len(secret) < 32:
            raise RuntimeError(
                "Production Startup Denied: JWT_SECRET_KEY must be configured with a dedicated strong secret "
                "of at least 32 characters in production. Default development keys are strictly rejected."
            )


def create_access_token(
    user_id: str,
    role: Union[str, Role],
    workspace_id: str,
    expires_delta: Optional[timedelta] = None,
    key_id: Optional[str] = None
) -> str:
    """
    Mints a signed JWT access token with verified claims and key id (kid) header.
    """
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    payload = {
        "sub": user_id,
        "role": role.value if isinstance(role, Role) else str(role),
        "workspace_id": workspace_id,
        "iss": JWT_ISSUER,
        "aud": JWT_AUDIENCE,
        "iat": now.timestamp(),
        "nbf": now.timestamp(),
        "exp": expire.timestamp(),
    }

    kid = key_id or JWT_KEY_ID
    secret = _KEY_RING.get(kid, JWT_SECRET_KEY)
    headers = {"kid": kid}

    return jwt.encode(payload, secret, algorithm=JWT_ALGORITHM, headers=headers)


def decode_access_token(token: str) -> Dict[str, Any]:
    """
    Verifies signature using matching kid, expiration, issuer, audience, and algorithms strictly.
    """
    try:
        unverified_headers = jwt.get_unverified_header(token)
        kid = unverified_headers.get("kid", JWT_KEY_ID)
    except Exception:
        kid = JWT_KEY_ID

    secret = _KEY_RING.get(kid, JWT_SECRET_KEY)
    payload = jwt.decode(
        token,
        secret,
        algorithms=[JWT_ALGORITHM],
        issuer=JWT_ISSUER,
        audience=JWT_AUDIENCE,
        options={
            "verify_signature": True,
            "verify_exp": True,
            "verify_iss": True,
            "verify_aud": True,
            "require": ["exp", "iss", "aud", "sub", "role", "workspace_id"]
        }
    )
    return payload
