import os
import pytest
from unittest.mock import patch, MagicMock
from services.orchestration.resolver import (
    LLMResolver,
    LLMResolutionError,
    LLMProviderDisabledError,
    LLMProviderNotConfiguredError,
    LLMModelCapabilityError,
)
from services.orchestration.providers.registry import provider_registry


def test_resolver_active_and_configured():
    """Combinaison 1: Fournisseur actif et correctement configuré."""
    with patch.dict(os.environ, {"NVIDIA_API_KEY": "nvapi-fake-test-key-123456789", "NVIDIA_ENABLED": "true"}):
        ctx = LLMResolver.resolve_model(
            workspace_id="ws_default",
            task_name="production",
            run_override={
                "provider_id": "nvidia",
                "model_id": "z-ai/glm-5.3-flash",
                "temperature": 0.2
            },
            allow_none_if_unconfigured=False
        )
        assert ctx is not None
        assert ctx.provider_id == "nvidia"
        assert ctx.model_id == "z-ai/glm-5.3-flash"
        assert ctx.resolution_source == "run_override"


def test_resolver_provider_disabled_strict():
    """Combinaison 2: Fournisseur explicitement désactivé avec allow_none_if_unconfigured=False."""
    with patch.dict(os.environ, {"NVIDIA_ENABLED": "false"}):
        with pytest.raises(LLMProviderDisabledError, match="désactivé"):
            LLMResolver.resolve_model(
                task_name="production",
                run_override={
                    "provider_id": "nvidia",
                    "model_id": "z-ai/glm-5.3-flash"
                },
                allow_none_if_unconfigured=False
            )


def test_resolver_provider_disabled_graceful():
    """Combinaison 2b: Fournisseur explicitement désactivé avec allow_none_if_unconfigured=True."""
    with patch.dict(os.environ, {"NVIDIA_ENABLED": "false"}):
        ctx = LLMResolver.resolve_model(
            task_name="production",
            run_override={
                "provider_id": "nvidia",
                "model_id": "z-ai/glm-5.3-flash"
            },
            allow_none_if_unconfigured=True
        )
        assert ctx is None


def test_resolver_missing_api_key_strict():
    """Combinaison 3: Clé API absente avec allow_none_if_unconfigured=False."""
    with patch.dict(os.environ, {"NVIDIA_API_KEY": "", "NVIDIA_ENABLED": "true"}):
        with pytest.raises(LLMProviderNotConfiguredError, match="n'a pas de clé API"):
            LLMResolver.resolve_model(
                task_name="production",
                run_override={
                    "provider_id": "nvidia",
                    "model_id": "z-ai/glm-5.3-flash"
                },
                allow_none_if_unconfigured=False
            )


def test_resolver_missing_api_key_graceful():
    """Combinaison 3b: Clé API absente avec allow_none_if_unconfigured=True."""
    with patch.dict(os.environ, {"NVIDIA_API_KEY": "", "NVIDIA_ENABLED": "true"}):
        ctx = LLMResolver.resolve_model(
            task_name="production",
            run_override={
                "provider_id": "nvidia",
                "model_id": "z-ai/glm-5.3-flash"
            },
            allow_none_if_unconfigured=True
        )
        assert ctx is None


def test_resolver_unknown_provider_rejected():
    """Combinaison 4: Fournisseur inexistant dans le registre."""
    with pytest.raises(LLMResolutionError, match="n'est pas reconnu"):
        LLMResolver.resolve_model(
            task_name="production",
            run_override={
                "provider_id": "unknown_ai_vendor_xyz",
                "model_id": "super-model"
            },
            allow_none_if_unconfigured=False
        )


def test_resolver_incompatible_capability_rejected():
    """Combinaison 5: Modèle ne supportant pas la capacité obligatoire demandée."""
    with patch.dict(os.environ, {"NVIDIA_API_KEY": "nvapi-test-key-12345678", "NVIDIA_ENABLED": "true"}):
        with patch.object(
            provider_registry.get_adapter("nvidia"),
            "get_model",
            return_value=MagicMock(capabilities={"structured_output": False})
        ):
            with pytest.raises(LLMModelCapabilityError, match="ne supporte pas la capacité obligatoire"):
                LLMResolver.resolve_model(
                    task_name="production",
                    run_override={
                        "provider_id": "nvidia",
                        "model_id": "nvidia/llama-3.1-nemotron-70b-instruct"
                    },
                    required_capability="structured_output",
                    allow_none_if_unconfigured=False
                )
