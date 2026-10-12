import re
from typing import Optional


class LLMError(Exception):
    """Base exception for normalized LLM provider errors."""
    def __init__(self, message: str, provider_id: str = "unknown", model_id: str = "unknown"):
        super().__init__(message)
        self.message = message
        self.provider_id = provider_id
        self.model_id = model_id


class LLMAuthenticationError(LLMError):
    """Raised when authentication against the LLM provider fails (HTTP 401/403)."""
    pass


class LLMModelNotFoundError(LLMError):
    """Raised when the requested LLM model is not available or not found (HTTP 404)."""
    pass


class LLMRateLimitError(LLMError):
    """Raised when client is rate limited by the LLM provider (HTTP 429)."""
    def __init__(
        self,
        message: str,
        provider_id: str = "unknown",
        model_id: str = "unknown",
        retry_after: Optional[float] = None
    ):
        super().__init__(message, provider_id=provider_id, model_id=model_id)
        self.retry_after = retry_after


class LLMTimeoutError(LLMError):
    """Raised when an LLM call exceeds the allowed latency deadline."""
    pass


class LLMProviderUnavailableError(LLMError):
    """Raised when provider returns 502/503/504 or connection failures."""
    pass


def normalize_llm_error(exc: Exception, provider_id: str = "unknown", model_id: str = "unknown") -> LLMError:
    """
    Normalizes diverse client and HTTP exceptions into a unified LLM error taxonomy.
    Extracts status codes and Retry-After values when available.
    """
    if isinstance(exc, LLMError):
        return exc

    err_str = str(exc).lower()

    # Detect Retry-After header or string
    retry_after: Optional[float] = None
    retry_match = re.search(r"retry[-_]after[:\s]+(\d+(?:\.\d+)?)", err_str)
    if retry_match:
        try:
            retry_after = float(retry_match.group(1))
        except (ValueError, TypeError):
            pass

    # HTTP Status-based or message-based classification
    if any(k in err_str for k in ["401", "unauthorized", "invalid_api_key", "bearer token", "forbidden", "403"]):
        return LLMAuthenticationError(
            f"Échec d'authentification pour le fournisseur '{provider_id}' ({exc})",
            provider_id=provider_id,
            model_id=model_id
        )

    if any(k in err_str for k in ["404", "model not found", "model_not_found", "does not exist", "unknown model"]):
        return LLMModelNotFoundError(
            f"Modèle '{model_id}' introuvable ou non déployé chez '{provider_id}' ({exc})",
            provider_id=provider_id,
            model_id=model_id
        )

    if any(k in err_str for k in ["429", "rate limit", "too many requests", "quota exceeded", "resourceexhausted"]):
        return LLMRateLimitError(
            f"Quota ou limite de débit dépassée chez '{provider_id}' pour le modèle '{model_id}'",
            provider_id=provider_id,
            model_id=model_id,
            retry_after=retry_after
        )

    if any(k in err_str for k in ["timeout", "timed out", "deadline exceeded", "readtimeout", "connecttimeout"]):
        return LLMTimeoutError(
            f"Délai d'attente dépassé (timeout) lors de l'appel à '{provider_id}:{model_id}'",
            provider_id=provider_id,
            model_id=model_id
        )

    if any(k in err_str for k in ["502", "503", "504", "bad gateway", "service unavailable", "gateway timeout"]):
        return LLMProviderUnavailableError(
            f"Service '{provider_id}' temporairement indisponible ({exc})",
            provider_id=provider_id,
            model_id=model_id
        )

    return LLMError(f"Erreur d'exécution LLM ({provider_id}:{model_id}) : {exc}", provider_id=provider_id, model_id=model_id)
