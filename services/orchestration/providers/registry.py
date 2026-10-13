from typing import Dict, List, Optional, Any
from packages.contracts.llm import LLMProviderInfo, LLMModelInfo
from services.orchestration.providers.base import BaseLLMAdapter
from services.orchestration.providers.gemini import GeminiProviderAdapter
from services.orchestration.providers.nvidia import NVIDIAProviderAdapter


class LLMProviderRegistry:
    """
    Central registry managing all LLM provider adapters.
    Provides extensible registration without modifying workflows or graphs.
    Callable both as class methods and via the provider_registry singleton.
    """
    _adapters: Dict[str, BaseLLMAdapter] = {}

    def __init__(self):
        if not self._adapters:
            self._init_defaults()

    @classmethod
    def _init_defaults(cls):
        if not cls._adapters:
            cls.register_adapter(GeminiProviderAdapter())
            cls.register_adapter(NVIDIAProviderAdapter())

    @classmethod
    def register_adapter(cls, adapter: BaseLLMAdapter) -> None:
        """Registers a provider adapter."""
        cls._adapters[adapter.provider_id] = adapter

    @classmethod
    def get_adapter(cls, provider_id: str) -> Optional[BaseLLMAdapter]:
        """Retrieves adapter by provider_id."""
        cls._init_defaults()
        return cls._adapters.get(provider_id)

    @classmethod
    def list_providers(cls) -> List[LLMProviderInfo]:
        """Lists metadata and configuration status for all registered providers."""
        cls._init_defaults()
        return [adapter.get_provider_info() for adapter in cls._adapters.values()]

    @classmethod
    def list_models(cls, provider_id: Optional[str] = None, force_refresh: bool = False, **kwargs: Any) -> List[LLMModelInfo]:
        """Lists available models across all providers or for a specific provider."""
        force_refresh = force_refresh or kwargs.get("refresh", False)
        cls._init_defaults()
        if provider_id:
            adapter = cls.get_adapter(provider_id)
            return adapter.list_models(force_refresh=force_refresh) if adapter else []

        all_models: List[LLMModelInfo] = []
        for adapter in cls._adapters.values():
            all_models.extend(adapter.list_models(force_refresh=force_refresh))
        return all_models

    @classmethod
    def get_all_models(cls, force_refresh: bool = False, **kwargs: Any) -> List[LLMModelInfo]:
        """Alias for list_models across all providers."""
        return cls.list_models(force_refresh=force_refresh, **kwargs)

    @classmethod
    def get_model(cls, provider_id: str, model_id: str) -> Optional[LLMModelInfo]:
        """Finds a specific model by provider and model_id."""
        cls._init_defaults()
        adapter = cls.get_adapter(provider_id)
        if adapter:
            return adapter.get_model(model_id)
        return None

    @classmethod
    def get_all_provider_info(cls) -> List[LLMProviderInfo]:
        return cls.list_providers()


# Global singleton instance
provider_registry = LLMProviderRegistry()
provider_registry._init_defaults()
