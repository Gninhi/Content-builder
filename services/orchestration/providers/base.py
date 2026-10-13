import abc
import time
from typing import List, Optional, Any
from packages.contracts.llm import (
    LLMModelInfo,
    LLMProviderInfo,
    LLMConnectionTestResponse,
)


class BaseLLMAdapter(abc.ABC):
    """
    Abstract contract for LLM provider adapters.
    Guarantees consistent instantiation, capability checking, model cataloging,
    and safe connection diagnostics without leaking credentials.
    """

    def __init__(self, provider_id: str, display_name: str, adapter_type: str):
        self.provider_id = provider_id
        self.display_name = display_name
        self.adapter_type = adapter_type
        self._last_test_status: Optional[str] = None
        self._last_test_at: Optional[Any] = None
        self._last_test_message: Optional[str] = None

    @abc.abstractmethod
    def is_configured(self) -> bool:
        """Checks if the required server-side credentials/keys exist and are non-empty."""
        pass

    @abc.abstractmethod
    def is_enabled(self) -> bool:
        """Checks whether this provider is administratively enabled."""
        pass

    @abc.abstractmethod
    def get_default_model_id(self) -> str:
        """Returns the default recommended model ID for this provider."""
        pass

    @abc.abstractmethod
    def list_models(self, force_refresh: bool = False) -> List[LLMModelInfo]:
        """Returns the list of available models with metadata and capabilities."""
        pass

    def get_model(self, model_id: str) -> Optional[LLMModelInfo]:
        """Finds a model by ID."""
        for m in self.list_models():
            if m.model_id == model_id:
                return m
        return None

    def validate_model(self, model_id: str) -> bool:
        """Checks if a model ID is recognized and supported by this provider."""
        return self.get_model(model_id) is not None

    @abc.abstractmethod
    def build_chat_model(
        self,
        model_id: str,
        temperature: float = 0.2,
        timeout: float = 30.0,
        max_retries: int = 3,
        **kwargs: Any
    ) -> Any:
        """Instantiates and returns the LangChain chat model."""
        pass

    def test_connection(
        self,
        model_id: Optional[str] = None,
        custom_base_url: Optional[str] = None
    ) -> LLMConnectionTestResponse:
        """
        Executes a minimal test generation query to verify credentials and connectivity.
        Does not publish any content and returns execution latency.
        """
        target_model = model_id or self.get_default_model_id()
        start = time.perf_counter()
        if not self.is_configured():
            return LLMConnectionTestResponse(
                success=False,
                provider_id=self.provider_id,
                model_id=target_model,
                latency_ms=0.0,
                message="Erreur : Clé API absente ou non configurée sur le serveur."
            )

        try:
            model = self.build_chat_model(
                model_id=target_model,
                temperature=0.1,
                timeout=12.0,
                max_retries=2
            )
            if model is None:
                raise RuntimeError("L'adaptateur n'a pas pu instancier le modèle.")

            # Minimal ping message with transient retry
            from langchain_core.messages import HumanMessage
            response = None
            last_err = None
            for attempt in range(2):
                try:
                    response = model.invoke([HumanMessage(content="Hello, test connection")])
                    break
                except Exception as ex:
                    last_err = ex
                    time.sleep(0.5)

            if response is None:
                raise last_err or RuntimeError("Aucune réponse reçue du modèle.")

            latency = (time.perf_counter() - start) * 1000.0

            _ = str(getattr(response, "content", ""))
            self._last_test_status = "SUCCESS"
            self._last_test_at = time.time()
            self._last_test_message = "Connexion validée avec succès."

            return LLMConnectionTestResponse(
                success=True,
                provider_id=self.provider_id,
                model_id=target_model,
                latency_ms=round(latency, 1),
                message=f"Connexion réussie en {round(latency, 1)}ms (réponse reçue)."
            )
        except Exception as e:
            latency = (time.perf_counter() - start) * 1000.0
            error_msg = str(e)
            # Redact any accidental key in exception message
            if "key" in error_msg.lower() or "bearer" in error_msg.lower() or "token" in error_msg.lower():
                error_msg = "Erreur d'authentification ou clé invalide."

            self._last_test_status = "ERROR"
            self._last_test_at = time.time()
            self._last_test_message = error_msg

            return LLMConnectionTestResponse(
                success=False,
                provider_id=self.provider_id,
                model_id=target_model,
                latency_ms=round(latency, 1),
                message=f"Échec de connexion : {error_msg}"
            )

    def get_provider_info(self) -> LLMProviderInfo:
        return LLMProviderInfo(
            provider_id=self.provider_id,
            display_name=self.display_name,
            adapter_type=self.adapter_type,
            is_configured=self.is_configured(),
            is_enabled=self.is_enabled(),
            default_model=self.get_default_model_id(),
            last_test_status=self._last_test_status,
            last_test_at=None,
            last_test_message=self._last_test_message
        )
