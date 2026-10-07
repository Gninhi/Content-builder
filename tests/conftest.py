import os
import pytest

# Configure global test environment defaults ensuring fail-closed tests pass securely
os.environ.setdefault("ENV", "production")
os.environ.setdefault("SECRET_VAULT_KEY", "super-secret-vault-master-key-32b-testing!")
os.environ.setdefault("JWT_SECRET_KEY", "super-secret-jwt-key-32-chars-testing-environment!")
os.environ.setdefault("SOCIAL_SANDBOX_MODE", "true")
os.environ.setdefault("LIVE_PUBLISHING_ENABLED", "false")
