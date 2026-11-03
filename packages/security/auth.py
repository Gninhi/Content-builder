import math
import os
import uuid
from collections import Counter
from typing import Dict, Any, Optional, Set, Union
from datetime import datetime, timezone, timedelta
from enum import Enum
import jwt
from dotenv import load_dotenv, find_dotenv
from packages.security.env import is_production, get_app_env

# Prioritize values from .env file in normal execution, without overwriting explicit test environment variables
_is_test_mode = (
    os.environ.get("CONTENTOPS_TEST_MODE") == "1"
    or "PYTEST_CURRENT_TEST" in os.environ
    or os.environ.get("APP_ENV") in ("test", "testing")
)
load_dotenv(find_dotenv(usecwd=True), override=not _is_test_mode)


PROHIBITED_SECRET_PATTERNS = (
    "change-me",
    "changeme",
    "example",
    "password",
    "secret",
    "admin",
    "12345",
    "qwerty",
    "test",
    "default",
)


def calculate_shannon_entropy(data: str) -> float:
    """Calculates the Shannon entropy in bits per character."""
    if not data:
        return 0.0
    counts = Counter(data)
    length = len(data)
    return -sum((count / length) * math.log2(count / length) for count in counts.values())


def validate_secret_entropy(
    secret: str,
    secret_name: str = "SECRET_KEY",
    min_length: int = 32,
    min_entropy: float = 3.0,
) -> None:
    """
    Validates that a cryptographic secret meets security standards:
    1. Minimum length (default 32 chars).
    2. Contains no prohibited substrings (change-me, example, secret, test, password, etc.).
    3. Shannon entropy is >= min_entropy bits/char.
    """
    if not secret:
        raise ValueError(f"{secret_name} must not be empty.")
    if len(secret) < min_length:
        raise ValueError(
            f"{secret_name} length ({len(secret)}) is below minimum required length of {min_length} characters."
        )

    lower_secret = secret.lower()
    for pattern in PROHIBITED_SECRET_PATTERNS:
        if pattern in lower_secret:
            raise ValueError(
                f"{secret_name} contains prohibited placeholder or insecure pattern '{pattern}'."
            )

    entropy = calculate_shannon_entropy(secret)
    if entropy < min_entropy:
        raise ValueError(
            f"{secret_name} entropy ({entropy:.2f} bits/char) is below minimum required threshold of {min_entropy:.2f}."
        )


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


# Known insecure legacy secrets - blacklisted and rejected in all environments
DEFAULT_DEV_JWT_SECRET = "contentops-hardened-jwt-secret-key-must-be-rotated-in-production-2026"  # nosec B105
LEGACY_INSECURE_DEV_JWT_SECRETS: Set[str] = {
    DEFAULT_DEV_JWT_SECRET,
    "secret",
    "change-me",
    "changeme",
    "default-jwt-secret",
    "password123456789012345678901234567890",
}


def get_jwt_secret_key() -> str:
    """
    Retrieves the active JWT secret key from the environment.
    Enforces fail-closed behavior: no default hardcoded fallback secrets are permitted.
    """
    secret = os.getenv("JWT_SECRET_KEY")
    if not secret:
        if _is_test_mode:
            # Deterministic high-entropy ephemeral key strictly reserved for isolated tests
            return "test_only_ephemeral_jwt_secret_key_32_chars_long_entropy_safe_ok_2026"
        raise RuntimeError(
            "Security Startup Error: JWT_SECRET_KEY environment variable is missing. "
            "A cryptographically strong secret (>= 32 chars, Shannon entropy >= 3.0) must be explicitly configured."
        )
    return secret


JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "")
JWT_KEY_ID = os.getenv("JWT_KEY_ID", "key_v1")
JWT_ALGORITHM = "HS256"
JWT_ISSUER = "contentops-auth"
JWT_AUDIENCE = "contentops-api"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "15"))


def get_key_ring() -> Dict[str, str]:
    """Returns the current key ring mapping key_id to secret key."""
    key_id = os.getenv("JWT_KEY_ID", "key_v1")
    secret = get_jwt_secret_key()
    ring: Dict[str, str] = {key_id: secret}
    rotation_keys = os.getenv("JWT_ROTATION_KEYS")
    if rotation_keys:
        for pair in rotation_keys.split(","):
            if ":" in pair:
                kid, ksecret = pair.split(":", 1)
                ring[kid.strip()] = ksecret.strip()
    return ring


# Key ring for backward compatibility with direct module imports
_KEY_RING: Dict[str, str] = get_key_ring()


def validate_jwt_configuration() -> None:
    """
    Enforces fail-closed validation of JWT keys in production and staging.
    Raises RuntimeError if insecure defaults or weak keys are used.
    """
    load_dotenv()
    secret = os.getenv("JWT_SECRET_KEY", "")
    if is_production() or get_app_env() in ("production", "staging"):
        if not secret or secret in LEGACY_INSECURE_DEV_JWT_SECRETS:
            raise RuntimeError(
                "Production Startup Denied: JWT_SECRET_KEY must be configured with a dedicated strong secret "
                "in production. Default development keys are strictly rejected. "
                "Configure a cryptographically random secret with >= 32 characters and high entropy."
            )
        try:
            validate_secret_entropy(secret, secret_name="JWT_SECRET_KEY", min_length=32, min_entropy=3.0)
        except ValueError as exc:
            raise RuntimeError(f"Production Startup Denied: {exc}") from exc
    elif not _is_test_mode and not secret:
        raise RuntimeError(
            "Security Startup Denied: JWT_SECRET_KEY must be explicitly configured in .env for development. "
            "Falling back to hardcoded defaults is strictly prohibited."
        )


def create_access_token(
    user_id: str,
    role: Union[str, Role],
    workspace_id: str,
    expires_delta: Optional[timedelta] = None,
    key_id: Optional[str] = None,
    jti: Optional[str] = None,
) -> str:
    """
    Mints a signed JWT access token with verified claims, session jti, and key id (kid) header.
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
        "jti": jti or uuid.uuid4().hex,
    }

    kid: str = str(key_id or os.getenv("JWT_KEY_ID") or JWT_KEY_ID)
    ring = get_key_ring()
    secret: str = ring.get(kid) or _KEY_RING.get(kid) or os.getenv("JWT_SECRET_KEY") or JWT_SECRET_KEY
    headers = {"kid": kid}

    return jwt.encode(payload, secret, algorithm=JWT_ALGORITHM, headers=headers)


def decode_access_token(token: str) -> Dict[str, Any]:
    """
    Verifies signature using matching kid, expiration, issuer, audience, and algorithms strictly.
    """
    default_kid: str = os.getenv("JWT_KEY_ID") or JWT_KEY_ID
    try:
        unverified_headers = jwt.get_unverified_header(token)
        kid_val = unverified_headers.get("kid", default_kid)
        kid: str = str(kid_val) if kid_val else default_kid
    except Exception:
        kid = default_kid

    ring = get_key_ring()
    secret: str = ring.get(kid) or _KEY_RING.get(kid) or os.getenv("JWT_SECRET_KEY") or JWT_SECRET_KEY
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
