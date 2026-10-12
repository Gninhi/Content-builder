from typing import Tuple, Optional
import argon2
from argon2.exceptions import VerifyMismatchError, InvalidHash

_hasher = argon2.PasswordHasher(
    time_cost=2,
    memory_cost=65536,
    parallelism=1,
    hash_len=32,
    type=argon2.Type.ID,
)


def hash_password(plain_password: str) -> str:
    """Hashes a password using Argon2id."""
    return _hasher.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies a plain password against an Argon2id hash."""
    if not hashed_password:
        return False
    try:
        return _hasher.verify(hashed_password, plain_password)
    except (VerifyMismatchError, InvalidHash):
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
    - Minimum 10 characters (high length without absurd composition rules)
    - Rejection of known common / breached passwords
    - Rejection of pure whitespace or single repeated characters
    - Must not contain obvious simple sequences
    """
    if len(password) < 10:
        return False, "Le mot de passe doit contenir au moins 10 caractères."

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
