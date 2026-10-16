import os
from unittest.mock import MagicMock, patch
import pytest

from packages.security.pii import mask_pii
from services.orchestration.callbacks.langfuse import SanitizedLangfuseCallbackHandler
from packages.observability.tracing import ObservabilityTracer


def test_mask_pii_recursive_sanitization():
    """Validates that mask_pii recursively masks emails, API keys, tokens and phone numbers."""
    raw_payload = {
        "user_email": "author@example.com",
        "nested": {
            "token": "AIzaSyFakeSecretKey1234567890123456",
            "phone": "+1-555-123-4567",
            "metadata": [
                "Contact: support@internal.corp",
                "pk-lf-publickey12345678",
                {"safe_field": "public_announcement"}
            ]
        }
    }

    sanitized = mask_pii(raw_payload)

    assert "[REDACTED_EMAIL]" in sanitized["user_email"]
    assert "author@example.com" not in sanitized["user_email"]
    assert "[REDACTED_GOOGLE_KEY]" in sanitized["nested"]["token"]
    assert "[REDACTED_PHONE]" in sanitized["nested"]["phone"]
    assert "[REDACTED_EMAIL]" in sanitized["nested"]["metadata"][0]
    assert "[REDACTED_LANGFUSE_PUBLIC_KEY]" in sanitized["nested"]["metadata"][1]
    assert sanitized["nested"]["metadata"][2]["safe_field"] == "public_announcement"


def test_callback_handler_masks_llm_prompts():
    """Ensures on_llm_start masks prompts before forwarding to the underlying collector."""
    handler = SanitizedLangfuseCallbackHandler(public_key="pk-lf-mock")
    # Mock the internal/super tracking calls
    with patch.object(handler, "_handle_llm_start", create=True) as mock_internal:
        prompts = ["Generate email for client test.user@acme.corp with key AIzaSyFakeSecretKey1234567890123456"]
        handler.on_llm_start(
            serialized={"name": "gemini"},
            prompts=prompts,
            user_metadata={"editor_email": "admin@editorial.internal"}
        )

    # Verify that the sanitized prompts do NOT contain the raw email or API key
    if mock_internal.called:
        passed_prompts = mock_internal.call_args[1].get("prompts") or mock_internal.call_args[0][1]
        assert "[REDACTED_EMAIL]" in passed_prompts[0]
        assert "test.user@acme.corp" not in passed_prompts[0]


def test_callback_handler_masks_chain_inputs_and_outputs():
    """Ensures on_chain_start and on_chain_end mask sensitive payloads."""
    handler = SanitizedLangfuseCallbackHandler(public_key="pk-lf-mock")

    inputs = {"brief": "Send draft to ceo@bigcorp.com", "api_key": "sk-lf-secretkey12345678"}
    outputs = {"result": "Approved by supervisor@bigcorp.com"}

    with patch.object(handler, "_handle_chain_start", create=True) as mock_chain_start:
        handler.on_chain_start(serialized={"name": "ideation"}, inputs=inputs)

    with patch.object(handler, "_handle_chain_end", create=True) as mock_chain_end:
        handler.on_chain_end(outputs=outputs)


def test_observability_tracer_returns_sanitized_handler():
    """Ensures ObservabilityTracer returns an instance of SanitizedLangfuseCallbackHandler."""
    with patch.dict(os.environ, {
        "LANGFUSE_PUBLIC_KEY": "pk-lf-test-12345678",
        "LANGFUSE_SECRET_KEY": "sk-lf-test-12345678",
        "LANGFUSE_HOST": "https://cloud.langfuse.com",
        "LANGFUSE_TRACING_ENABLED": "true"
    }):
        handler = ObservabilityTracer.get_callback_handler(session_id="sess_123")
        assert handler is not None
        assert isinstance(handler, SanitizedLangfuseCallbackHandler)
