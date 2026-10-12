import secrets
import hashlib
from typing import Tuple, Optional


def generate_crypto_token(length: int = 32) -> str:
    """Generates a cryptographically secure URL-safe random string."""
    return secrets.token_urlsafe(length)


def hash_crypto_token(token: str) -> str:
    """Computes SHA-256 hash of a sensitive token before database storage."""
    return hashlib.sha256(token.strip().encode("utf-8")).hexdigest()


def generate_refresh_token(family_id: Optional[str] = None) -> Tuple[str, str, str]:
    """
    Generates a new refresh token with associated hash and family ID.
    Returns: (raw_token, token_hash, family_id)
    """
    raw_token = generate_crypto_token(48)
    token_hash = hash_crypto_token(raw_token)
    assigned_family_id = family_id or generate_crypto_token(16)
    return raw_token, token_hash, assigned_family_id
