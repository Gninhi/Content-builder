import os
import pytest
from fastapi.testclient import TestClient

from apps.api.main import app
from packages.security.env import get_app_env, is_production, is_dev_or_test

client = TestClient(app)


def test_app_env_defaults_fail_closed_to_production(monkeypatch):
    """When no environment variables are set, get_app_env() must default to 'production'."""
    monkeypatch.delenv("APP_ENV", raising=False)
    monkeypatch.delenv("ENVIRONMENT", raising=False)
    monkeypatch.delenv("ENV", raising=False)

    assert get_app_env() == "production"
    assert is_production() is True
    assert is_dev_or_test() is False


def test_app_env_priority_order(monkeypatch):
    """APP_ENV takes priority over legacy ENVIRONMENT and ENV."""
    monkeypatch.setenv("APP_ENV", "staging")
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("ENV", "local")

    assert get_app_env() == "staging"

    monkeypatch.delenv("APP_ENV")
    assert get_app_env() == "development"

    monkeypatch.delenv("ENVIRONMENT")
    assert get_app_env() == "local"


def test_dev_token_route_completely_removed(monkeypatch):
    """The /v1/auth/dev-token route must return 404 in dev as well as production."""
    for env_val in ["dev", "development", "production", "test"]:
        monkeypatch.setenv("APP_ENV", env_val)
        res = client.post(
            "/v1/auth/dev-token",
            json={"user_id": "attacker", "role": "Owner", "workspace_id": "ws_victim"}
        )
        assert res.status_code == 404, f"Expected 404 Not Found in {env_val}, got {res.status_code}"
