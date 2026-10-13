import os
import logging
from typing import List, Any
from packages.contracts.llm import LLMModelInfo, LLMCapability
from services.orchestration.providers.base import BaseLLMAdapter

logger = logging.getLogger(__name__)


class GeminiProviderAdapter(BaseLLMAdapter):
    """
    Adapter for Google Gemini models via langchain-google-genai.
    """

    def __init__(self):
        super().__init__(
            provider_id="gemini",
            display_name="Google Gemini",
            adapter_type="google_genai"
        )
        self._catalog: List[LLMModelInfo] = [
            LLMModelInfo(
                provider_id="gemini",
                model_id="gemini-3.8-flash",
                display_name="Gemini 3.8 Flash (Recommandé)",
                capabilities={
                    LLMCapability.TEXT_GENERATION.value: True,
                    LLMCapability.STRUCTURED_OUTPUT.value: True,
                    LLMCapability.TOOL_CALLING.value: True,
                    LLMCapability.STREAMING.value: True,
                    LLMCapability.VISION.value: True,
                },
                parameters={"temperature": {"min": 0.0, "max": 2.0, "default": 0.2}},
                provenance="catalog",
                is_available=True
            ),
            LLMModelInfo(
                provider_id="gemini",
                model_id="gemini-1.5-flash",
                display_name="Gemini 1.5 Flash",
                capabilities={
                    LLMCapability.TEXT_GENERATION.value: True,
                    LLMCapability.STRUCTURED_OUTPUT.value: True,
                    LLMCapability.TOOL_CALLING.value: True,
                    LLMCapability.STREAMING.value: True,
                    LLMCapability.VISION.value: True,
                },
                parameters={"temperature": {"min": 0.0, "max": 2.0, "default": 0.2}},
                provenance="catalog",
                is_available=True
            ),
            LLMModelInfo(
                provider_id="gemini",
                model_id="gemini-1.5-pro",
                display_name="Gemini 1.5 Pro (Raisonnement avancé)",
                capabilities={
                    LLMCapability.TEXT_GENERATION.value: True,
                    LLMCapability.STRUCTURED_OUTPUT.value: True,
                    LLMCapability.TOOL_CALLING.value: True,
                    LLMCapability.STREAMING.value: True,
                    LLMCapability.VISION.value: True,
                },
                parameters={"temperature": {"min": 0.0, "max": 2.0, "default": 0.2}},
                provenance="catalog",
                is_available=True
            ),
        ]

    def is_configured(self) -> bool:
        key = os.getenv("GOOGLE_API_KEY", "").strip()
        return bool(key and not key.startswith("your_") and len(key) > 10)

    def is_enabled(self) -> bool:
        return os.getenv("GEMINI_ENABLED", "true").lower() == "true"

    def get_default_model_id(self) -> str:
        return os.getenv("GEMINI_MODEL", "gemini-3.8-flash")

    def list_models(self, force_refresh: bool = False, **kwargs: Any) -> List[LLMModelInfo]:
        return list(self._catalog)

    def build_chat_model(
        self,
        model_id: str,
        temperature: float = 0.2,
        timeout: float = 30.0,
        max_retries: int = 3,
        **kwargs: Any
    ) -> Any:
        if not self.is_configured():
            return None

        from langchain_google_genai import ChatGoogleGenerativeAI
        api_key = os.getenv("GOOGLE_API_KEY")
        return ChatGoogleGenerativeAI(
            model=model_id,
            google_api_key=api_key,
            temperature=temperature,
            timeout=timeout,
            max_retries=max_retries,
            **kwargs
        )
