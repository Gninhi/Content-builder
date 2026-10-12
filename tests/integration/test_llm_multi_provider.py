import os
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from apps.api.main import app
from packages.security.auth import create_access_token
from services.orchestration.providers.registry import provider_registry
from services.orchestration.providers.nvidia import validate_nvidia_endpoint
from services.orchestration.resolver import LLMResolver, LLMResolutionError
from infra.db.database import SessionLocal
from infra.db.repository import ContentOpsRepository

client = TestClient(app)


@pytest.fixture
def owner_token() -> str:
    return create_access_token(
        user_id="user_owner", role="Owner", workspace_id="ws_default"
    )


@pytest.fixture
def viewer_token() -> str:
    return create_access_token(
        user_id="user_viewer", role="Viewer", workspace_id="ws_default"
    )


@pytest.fixture
def other_workspace_token() -> str:
    return create_access_token(
        user_id="user_other", role="Editor", workspace_id="ws_foreign"
    )


def test_list_providers_zero_secret_leakage(owner_token):
    """Verifies that listing providers never leaks API keys or secrets."""
    with patch.dict(os.environ, {
        "GOOGLE_API_KEY": "AIzaSySuperSecretGoogleKeyDoNotLeak",
        "NVIDIA_API_KEY": "nvapi-SuperSecretNvidiaKeyDoNotLeak"
    }):
        response = client.get(
            "/v1/llm/providers",
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 2

        # Check all stringified representations for absence of secrets
        body_text = response.text
        assert "AIzaSySuperSecretGoogleKeyDoNotLeak" not in body_text
        assert "nvapi-SuperSecretNvidiaKeyDoNotLeak" not in body_text

        # Verify providers present
        provider_ids = [p["provider_id"] for p in data]
        assert "gemini" in provider_ids
        assert "nvidia" in provider_ids

        # Check configured flags
        nvidia_info = next(p for p in data if p["provider_id"] == "nvidia")
        assert nvidia_info["is_configured"] is True
        assert nvidia_info["display_name"] == "NVIDIA API Catalog"


def test_list_models_catalogue_and_filtering(owner_token):
    """Verifies filtering models by provider and catalogue structure."""
    response = client.get(
        "/v1/llm/models?provider_id=nvidia",
        headers={"Authorization": f"Bearer {owner_token}"}
    )
    assert response.status_code == 200
    models = response.json()
    assert len(models) >= 4
    model_ids = [m["model_id"] for m in models]
    assert "meta/llama-3.2-11b-vision-instruct" in model_ids
    assert "nvidia/llama-3.1-nemotron-70b-instruct" in model_ids

    # Check capabilities structure
    llama70 = next(m for m in models if m["model_id"] == "meta/llama-3.2-11b-vision-instruct")
    assert llama70["capabilities"]["structured_output"] is True
    assert llama70["capabilities"]["text_generation"] is True
    assert llama70["provenance"] == "catalog"


def test_workspace_llm_config_get_and_update_lifecycle(owner_token):
    """Verifies reading, updating, and persisting workspace LLM settings."""
    # 1. Get initial config (should return baseline defaults)
    res_get = client.get(
        "/v1/llm/config/ws_default",
        headers={"Authorization": f"Bearer {owner_token}"}
    )
    assert res_get.status_code == 200
    cfg = res_get.json()
    assert cfg["workspace_id"] == "ws_default"
    assert "default_provider_id" in cfg

    # 2. Update config to use NVIDIA as default with task overrides
    update_payload = {
        "default_provider_id": "nvidia",
        "default_model_id": "meta/llama-3.2-11b-vision-instruct",
        "default_temperature": 0.45,
        "task_overrides": {
            "ideation": {
                "provider_id": "nvidia",
                "model_id": "nvidia/llama-3.1-nemotron-70b-instruct",
                "temperature": 0.3,
                "inherit_default": False
            },
            "production": {
                "provider_id": "nvidia",
                "model_id": "meta/llama-3.2-11b-vision-instruct",
                "temperature": 0.4,
                "inherit_default": True
            }
        },
        "provider_settings": {}
    }

    res_put = client.put(
        "/v1/llm/config/ws_default",
        json=update_payload,
        headers={"Authorization": f"Bearer {owner_token}"}
    )
    assert res_put.status_code == 200
    updated = res_put.json()
    assert updated["default_provider_id"] == "nvidia"
    assert updated["default_model_id"] == "meta/llama-3.2-11b-vision-instruct"
    assert updated["default_temperature"] == 0.45
    assert updated["task_overrides"]["ideation"]["model_id"] == "nvidia/llama-3.1-nemotron-70b-instruct"

    # 3. Query repository directly to verify DB persistence
    db = SessionLocal()
    try:
        repo = ContentOpsRepository(db)
        db_settings = repo.get_workspace_llm_settings("ws_default")
        assert db_settings is not None
        assert db_settings.default_provider_id == "nvidia"
        assert db_settings.default_model_id == "meta/llama-3.2-11b-vision-instruct"
    finally:
        db.close()


def test_viewer_cannot_update_config(viewer_token):
    """Verifies RBAC: Viewers cannot modify LLM settings."""
    update_payload = {
        "default_provider_id": "gemini",
        "default_model_id": "gemini-3.8-flash",
        "default_temperature": 0.7,
        "task_overrides": {},
        "provider_settings": {}
    }
    response = client.put(
        "/v1/llm/config/ws_default",
        json=update_payload,
        headers={"Authorization": f"Bearer {viewer_token}"}
    )
    assert response.status_code == 403


def test_cross_tenant_isolation_forbidden(other_workspace_token):
    """Verifies that an editor from another workspace cannot modify another tenant's config."""
    update_payload = {
        "default_provider_id": "gemini",
        "default_model_id": "gemini-3.8-flash",
        "default_temperature": 0.7,
        "task_overrides": {},
        "provider_settings": {}
    }
    response = client.put(
        "/v1/llm/config/ws_default",
        json=update_payload,
        headers={"Authorization": f"Bearer {other_workspace_token}"}
    )
    assert response.status_code == 403


def test_ssrf_guard_blocks_private_endpoints(owner_token):
    """Verifies SSRF protection against private network or loopback NIM endpoints."""
    # Test validator function directly
    with pytest.raises(PermissionError, match="Sécurité SSRF"):
        validate_nvidia_endpoint("http://127.0.0.1:8000/v1")

    with pytest.raises(PermissionError, match="Sécurité SSRF"):
        validate_nvidia_endpoint("http://192.168.1.50:8000/v1")

    with pytest.raises(PermissionError, match="Sécurité SSRF"):
        validate_nvidia_endpoint("http://10.0.0.1/v1")

    with pytest.raises(PermissionError, match="Sécurité SSRF"):
        validate_nvidia_endpoint("http://localhost:8000/v1")

    # Test via API update
    malicious_payload = {
        "default_provider_id": "gemini",
        "default_model_id": "gemini-3.8-flash",
        "default_temperature": 0.5,
        "task_overrides": {},
        "provider_settings": {
            "nvidia": {
                "base_url": "http://169.254.169.254/latest/meta-data/"
            }
        }
    }
    response = client.put(
        "/v1/llm/config/ws_default",
        json=malicious_payload,
        headers={"Authorization": f"Bearer {owner_token}"}
    )
    assert response.status_code == 400
    assert "Invalid custom endpoint" in response.json()["detail"]


def test_explicit_test_connection_diagnostics(owner_token):
    """Verifies the explicit test-connection endpoint with mocked adapter response."""
    with patch.object(
        provider_registry.get_adapter("nvidia"),
        "test_connection",
        return_value=MagicMock(
            success=True,
            provider_id="nvidia",
            model_id="meta/llama-3.2-11b-vision-instruct",
            latency_ms=145.2,
            message="Authentification NVIDIA réussie.",
            tested_at="2026-10-09T08:00:00Z"
        )
    ):
        response = client.post(
            "/v1/llm/test-connection",
            json={"provider_id": "nvidia", "model_id": "meta/llama-3.2-11b-vision-instruct"},
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["latency_ms"] == 145.2


def test_model_capabilities_validation_endpoint(owner_token):
    """Verifies model capability validation endpoint for required features."""
    # Test valid model with structured output
    valid_res = client.post(
        "/v1/llm/validate-selection",
        json={
            "provider_id": "nvidia",
            "model_id": "meta/llama-3.2-11b-vision-instruct",
            "required_capabilities": ["structured_output", "text_generation"]
        },
        headers={"Authorization": f"Bearer {owner_token}"}
    )
    assert valid_res.status_code == 200
    assert valid_res.json()["valid"] is True

    # Test unknown model produces valid=False or missing
    invalid_res = client.post(
        "/v1/llm/validate-selection",
        json={
            "provider_id": "nvidia",
            "model_id": "unknown-fictional-model-xyz",
            "required_capabilities": ["structured_output"]
        },
        headers={"Authorization": f"Bearer {owner_token}"}
    )
    assert invalid_res.status_code == 200
    assert invalid_res.json()["valid"] is False


def test_centralized_resolver_hierarchy():
    """Verifies the 5-tier resolution hierarchy and zero silent provider fallback."""
    # Tier 1: Run override takes highest precedence
    with patch.dict(os.environ, {"NVIDIA_API_KEY": "nvapi-fake-test-key-123456789"}):
        ctx = LLMResolver.resolve_model(
            workspace_id="ws_default",
            task_name="production",
            run_override={
                "provider_id": "nvidia",
                "model_id": "nvidia/llama-3.1-nemotron-70b-instruct",
                "temperature": 0.15
            },
            allow_none_if_unconfigured=False
        )
        assert ctx is not None
        assert ctx.provider_id == "nvidia"
        assert ctx.model_id == "nvidia/llama-3.1-nemotron-70b-instruct"
        assert ctx.temperature == 0.15
        assert ctx.resolution_source == "run_override"

    # Incompatible capability check raises explicit LLMResolutionError
    with pytest.raises(LLMResolutionError, match="ne supporte pas la capacité obligatoire"):
        with patch.object(
            provider_registry.get_adapter("nvidia"),
            "get_model",
            return_value=MagicMock(capabilities={"structured_output": False})
        ):
            LLMResolver.resolve_model(
                task_name="production",
                run_override={
                    "provider_id": "nvidia",
                    "model_id": "nvidia/llama-3.1-nemotron-70b-instruct"
                },
                required_capability="structured_output",
                allow_none_if_unconfigured=False
            )
