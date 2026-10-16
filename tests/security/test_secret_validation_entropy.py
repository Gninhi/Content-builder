import pytest
from packages.security.auth import validate_jwt_configuration, validate_secret_entropy


def test_validate_secret_entropy_rejects_weak_and_pattern_secrets():
    """Secrets containing blacklisted patterns or insufficient entropy must be rejected."""
    # Common blacklisted words
    for weak_key in [
        "this-is-a-change-me-secret-key-123456789",
        "example-secret-key-that-is-at-least-32-chars-long",
        "my-secret-password-key-for-jwt-signing-test-32",
        "admin-super-secret-key-12345678901234567890",
        "qwertyuiop123456789012345678901234567890",
        "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",  # zero entropy
        "short",  # < 32 chars
    ]:
        with pytest.raises((ValueError, RuntimeError)):
            validate_secret_entropy(weak_key, secret_name="TEST_KEY")


def test_validate_secret_entropy_accepts_strong_secrets():
    """Cryptographically random secrets must pass entropy validation."""
    strong_secrets = [
        "c83b8e4e9f78326a1b92014bdf881023d7a8e24c6198f48037b42f61e457e841",
        "vN8!mK2#zQ9$pL1*wX5@bT7^dF3&hJ6(yU0)sR4_eW8+",
        "k8F2_mX90-aZ72$pLqW4!vB8@cE3#tY1%uI9^oP6&gH5*jK3",
    ]
    for strong in strong_secrets:
        # Should not raise any exception
        validate_secret_entropy(strong, secret_name="TEST_KEY")


def test_validate_jwt_configuration_in_production(monkeypatch):
    """In production, validate_jwt_configuration must fail-close on weak keys."""
    monkeypatch.setenv("APP_ENV", "production")

    # Weak secret with blacklist pattern
    monkeypatch.setenv("JWT_SECRET_KEY", "example-production-key-at-least-32-chars-long!")
    with pytest.raises(RuntimeError):
        validate_jwt_configuration()

    # Valid high-entropy secret
    monkeypatch.setenv("JWT_SECRET_KEY", "b4f2c99a807d4e5f1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a")
    # Should pass without error
    validate_jwt_configuration()
