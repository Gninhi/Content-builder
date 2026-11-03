from typing import Tuple, Optional
import argon2
from argon2.exceptions import VerifyMismatchError, InvalidHash

MIN_PASSWORD_LENGTH = 10
MAX_PASSWORD_LENGTH = 128

_hasher = argon2.PasswordHasher(
    time_cost=2,
    memory_cost=65536,
    parallelism=1,
    hash_len=32,
    type=argon2.Type.ID,
)


def hash_password(plain_password: str) -> str:
    """Hashes a password using Argon2id after enforcing maximum length."""
    if len(plain_password) > MAX_PASSWORD_LENGTH:
        raise ValueError(f"Le mot de passe ne doit pas dépasser {MAX_PASSWORD_LENGTH} caractères.")
    return _hasher.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies a plain password against an Argon2id hash (rejecting oversized payloads before hashing)."""
    if not hashed_password or not plain_password or len(plain_password) > MAX_PASSWORD_LENGTH:
        return False
    try:
        return _hasher.verify(hashed_password, plain_password)
    except (VerifyMismatchError, InvalidHash):
        return False


def check_needs_rehash(hashed_password: str) -> bool:
    """Checks whether an Argon2id hash needs to be rehashed with updated cost parameters."""
    if not hashed_password:
        return False
    try:
        return bool(_hasher.check_needs_rehash(hashed_password))
    except Exception:
        return False


COMMON_PASSWORDS = {
    "password", "password123", "1234567890", "123456789", "qwertyuiop",
    "admin12345", "admin123456", "welcome123", "iloveyou123", "sunshine123",
    "princess123", "football123", "monkey1234", "dragon1234", "master1234",
    "contentops", "contentops123", "contentbuilder", "letmein123",
}


def validate_password_strength(password: str) -> Tuple[bool, Optional[str]]:
    """
    Validates password strength according to modern OWASP / NIST SP 800-63B guidelines:
    - Maximum 128 characters (prevents Argon2id CPU/memory DoS)
    - Minimum 10 characters (high length without absurd composition rules)
    - Rejection of known common / breached passwords
    - Rejection of pure whitespace or single repeated characters
    - Must not contain obvious simple sequences
    """
    if len(password) > MAX_PASSWORD_LENGTH:
        return False, f"Le mot de passe ne doit pas dépasser {MAX_PASSWORD_LENGTH} caractères."

    if len(password) < MIN_PASSWORD_LENGTH:
        return False, f"Le mot de passe doit contenir au moins {MIN_PASSWORD_LENGTH} caractères."

    if password.lower() in COMMON_PASSWORDS or password.lower().strip() in COMMON_PASSWORDS:
        return False, "Ce mot de passe est trop courant et facilement devinable."

    if len(set(password)) < 4:
        return False, "Le mot de passe contient trop de répétitions d'un même caractère."

    # Prevent common sequential strings
    lowered = password.lower()
    for seq in ["12345", "23456", "34567", "45678", "56789", "qwerty", "azerty", "abcdef"]:
        if seq in lowered:
            return False, "Le mot de passe ne doit pas contenir de suites évidentes de caractères."

    return True, None

