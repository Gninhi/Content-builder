import os
from typing import Dict, Any, Optional
from datetime import datetime, timezone, timedelta
from enum import Enum
import jwt


class Role(str, Enum):
    OWNER = "Owner"
    EDITOR = "Editor"
    VIEWER = "Viewer"
    SERVICE_AGENT = "ServiceAgent"


JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "contentops-hardened-jwt-secret-key-must-be-rotated-in-production-2026")
JWT_ALGORITHM = "HS256"
JWT_ISSUER = "contentops-auth"
JWT_AUDIENCE = "contentops-api"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))


def create_access_token(
    user_id: str,
    role: str,
    workspace_id: str,
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Mints a signed JWT access token with verified claims.
    """
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    payload = {
        "sub": user_id,
        "role": role if isinstance(role, str) else role.value,
        "workspace_id": workspace_id,
        "iss": JWT_ISSUER,
        "aud": JWT_AUDIENCE,
        "iat": now.timestamp(),
        "nbf": now.timestamp(),
        "exp": expire.timestamp(),
    }

    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> Dict[str, Any]:
    """
    Verifies signature, expiration, issuer, audience, and algorithms strictly.
    """
    payload = jwt.decode(
        token,
        JWT_SECRET_KEY,
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
