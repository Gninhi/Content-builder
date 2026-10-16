import os

# Configure global test environment defaults ensuring fail-closed tests pass securely
os.environ.setdefault("APP_ENV", "production")
os.environ.setdefault("SECRET_VAULT_KEY", "cbe7e00447543d905f45c9b5b702949529b8f356c6ed5c28e0ea21d53ce34536")
os.environ.setdefault("JWT_SECRET_KEY", "f9b2d8e4c1a705e38d9b1c2a4f6e80237d5c9e1b3a5f70248c6e91d3b5a7c2e4")
os.environ.setdefault("SOCIAL_SANDBOX_MODE", "true")
os.environ.setdefault("LIVE_PUBLISHING_ENABLED", "false")
os.environ.setdefault("REQUIRE_EMAIL_VERIFICATION", "false")
