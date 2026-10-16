import os
from unittest.mock import MagicMock, patch
import pytest

from services.orchestration.nodes.production import generate_variants_node
from services.orchestration.providers.nvidia import NVIDIAProviderAdapter


def test_production_node_does_not_silently_fallback_to_gemini(monkeypatch):
    """
    H14: When resolved LLM is None (e.g. sovereign model offline/unconfigured),
    generate_variants must NOT silently fallback to Gemini without explicit consent.
    """
    monkeypatch.setenv("ALLOW_CROSS_PROVIDER_FALLBACK", "false")

    state = {
        "workspace_id": "ws_sovereign_eu",
        "brand_voice": "Professional",
        "audience": ["Tech"],
        "target_platforms": ["linkedin"],
        "resolved_llm": {"provider_id": "ollama", "model_id": "mistral-7b"},
    }

    mock_gemini = MagicMock()
    with patch("services.orchestration.nodes.production.get_gemini_model", mock_gemini):
        with patch("services.orchestration.nodes.production.resolve_and_get_llm", return_value=(None, None)):
            result = generate_variants_node(state)

    # Gemini must NOT have been called
    mock_gemini.assert_not_called()
    assert "generated_variants" in result
    # Fallback variant generated deterministically without data leak to Gemini
    assert len(result["generated_variants"]) >= 1


def test_nvidia_build_chat_model_honors_custom_base_url(monkeypatch):
    """
    H14: NVIDIAAdapter.build_chat_model must honor custom base_url parameter.
    """
    monkeypatch.setenv("NVIDIA_API_KEY", "nvapi-test-valid-dummy-key-32chars!")
    adapter = NVIDIAProviderAdapter()

    custom_url = "https://custom-nim.enterprise.corp/v1"
    with patch("langchain_nvidia_ai_endpoints.ChatNVIDIA") as mock_chat_class:
        mock_instance = MagicMock()
        mock_chat_class.return_value = mock_instance
        adapter.build_chat_model(
            model_id="z-ai/glm-5.3-flash",
            base_url=custom_url
        )

        assert mock_chat_class.called
        call_kwargs = mock_chat_class.call_args[1]
        assert call_kwargs.get("base_url") == custom_url
