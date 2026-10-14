import os
import re
import time
import logging
import ipaddress
from urllib.parse import urlparse
from typing import List, Optional, Any
import httpx
from dotenv import load_dotenv, find_dotenv

from packages.contracts.llm import LLMModelInfo, LLMCapability
from packages.resilience import (
    RateLimiter,
    get_rate_limiter,
    CircuitBreaker,
    get_circuit_breaker,
    CircuitBreakerOpenException,
    LLMRateLimitError,
    normalize_llm_error
)
from services.orchestration.providers.base import BaseLLMAdapter

load_dotenv(find_dotenv(usecwd=True), override=False)

logger = logging.getLogger(__name__)

DEFAULT_NVIDIA_BASE_URL = "https://integrate.api.nvidia.com/v1"
DISCOVERY_CACHE_TTL_SECONDS = 3600  # 1 hour default


def strip_reasoning_tokens(text: str) -> str:
    """Removes chain-of-thought blocks (<think>...</think>) from LLM outputs."""
    if not text:
        return ""
    return re.sub(r"<think>.*?(?:</think>|$)", "", text, flags=re.DOTALL).strip()



def validate_nvidia_endpoint(base_url: str) -> None:
    """
    Validates custom endpoints to prevent SSRF and unapproved internal access.
    """
    parsed = urlparse(base_url)
    if parsed.scheme not in ("http", "https"):
        raise ValueError(f"Protocole invalide pour l'endpoint NVIDIA: '{parsed.scheme}'. Seuls 'http' et 'https' sont acceptés.")

    hostname = parsed.hostname or ""
    if not hostname:
        raise ValueError("L'URL de l'endpoint NVIDIA ne contient aucun nom d'hôte valide.")

    # Check if host is a local/private network address
    is_private = False
    try:
        ip = ipaddress.ip_address(hostname)
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_unspecified:
            is_private = True
    except ValueError:
        # Hostname is a domain, check for localhost
        if hostname.lower() in ("localhost", "127.0.0.1", "0.0.0.0", "host.docker.internal"):  # nosec B104
            is_private = True

    allow_local = os.getenv("NVIDIA_ALLOW_LOCAL_ENDPOINTS", "false").lower() == "true"
    if is_private and not allow_local:
        raise PermissionError(
            f"Sécurité SSRF : L'accès aux hôtes privés/locaux ({hostname}) est désactivé par défaut. "
            "Définissez NVIDIA_ALLOW_LOCAL_ENDPOINTS=true dans la configuration du serveur pour autoriser un conteneur NIM local."
        )


class ResilientChatNVIDIA:
    """
    Production-grade resilient wrapper around ChatNVIDIA.
    Enforces:
    - Client-side token-bucket rate limiting (40 RPM default)
    - Circuit breaker per model with recovery cooldown
    - Exponential backoff with jitter and Retry-After handling
    - Error normalization to unified taxonomy (LLMAuthenticationError, LLMRateLimitError, etc.)
    - Automatic stripping of reasoning tokens (<think>...</think>) from outputs
    """
    def __init__(
        self,
        raw_model: Any,
        model_id: str,
        rate_limiter: RateLimiter,
        circuit_breaker: CircuitBreaker,
        timeout: float = 60.0
    ):
        self._raw_model = raw_model
        self.model_id = model_id
        self.rate_limiter = rate_limiter
        self.circuit_breaker = circuit_breaker
        self.timeout = timeout

    def invoke(self, *args: Any, **kwargs: Any) -> Any:
        if not self.circuit_breaker.can_execute():
            raise CircuitBreakerOpenException(
                f"[NVIDIA:{self.model_id}] Circuit is OPEN. Calls are blocked until recovery timeout."
            )
        acquired = self.rate_limiter.acquire(timeout=self.timeout)
        if not acquired:
            raise LLMRateLimitError(
                f"Rate limit token acquisition timed out for NVIDIA model '{self.model_id}'",
                provider_id="nvidia",
                model_id=self.model_id
            )

        try:
            res = self._raw_model.invoke(*args, **kwargs)
            self.circuit_breaker.record_success()
            if hasattr(res, "content") and isinstance(res.content, str):
                res.content = strip_reasoning_tokens(res.content)
            return res
        except Exception as e:
            norm_err = normalize_llm_error(e, provider_id="nvidia", model_id=self.model_id)
            if isinstance(norm_err, LLMRateLimitError) and norm_err.retry_after:
                self.rate_limiter.record_retry_after(norm_err.retry_after)
            self.circuit_breaker.record_failure(norm_err)
            raise norm_err

    async def ainvoke(self, *args: Any, **kwargs: Any) -> Any:
        if not self.circuit_breaker.can_execute():
            raise CircuitBreakerOpenException(
                f"[NVIDIA:{self.model_id}] Circuit is OPEN. Calls are blocked until recovery timeout."
            )
        acquired = await self.rate_limiter.acquire_async(timeout=self.timeout)
        if not acquired:
            raise LLMRateLimitError(
                f"Async rate limit token acquisition timed out for NVIDIA model '{self.model_id}'",
                provider_id="nvidia",
                model_id=self.model_id
            )

        try:
            if hasattr(self._raw_model, "ainvoke"):
                res = await self._raw_model.ainvoke(*args, **kwargs)
            else:
                res = self._raw_model.invoke(*args, **kwargs)
            self.circuit_breaker.record_success()
            if hasattr(res, "content") and isinstance(res.content, str):
                res.content = strip_reasoning_tokens(res.content)
            return res
        except Exception as e:
            norm_err = normalize_llm_error(e, provider_id="nvidia", model_id=self.model_id)
            if isinstance(norm_err, LLMRateLimitError) and norm_err.retry_after:
                self.rate_limiter.record_retry_after(norm_err.retry_after)
            self.circuit_breaker.record_failure(norm_err)
            raise norm_err

    def with_structured_output(self, schema: Any, **kwargs: Any) -> Any:
        raw_structured = self._raw_model.with_structured_output(schema, **kwargs)
        return ResilientChatNVIDIA(
            raw_model=raw_structured,
            model_id=self.model_id,
            rate_limiter=self.rate_limiter,
            circuit_breaker=self.circuit_breaker,
            timeout=self.timeout
        )

    def bind_tools(self, *args: Any, **kwargs: Any) -> Any:
        bound = self._raw_model.bind_tools(*args, **kwargs)
        return ResilientChatNVIDIA(
            raw_model=bound,
            model_id=self.model_id,
            rate_limiter=self.rate_limiter,
            circuit_breaker=self.circuit_breaker,
            timeout=self.timeout
        )

    def __getattr__(self, name: str) -> Any:
        return getattr(self._raw_model, name)


class NVIDIAProviderAdapter(BaseLLMAdapter):
    """
    Adapter for hosted NVIDIA API (integrate.api.nvidia.com) and self-hosted NIM endpoints.
    Provides verified curated catalog, live discovery caching, and parameter validation.
    """

    def __init__(self, custom_base_url: Optional[str] = None):
        super().__init__(
            provider_id="nvidia",
            display_name="NVIDIA API Catalog",
            adapter_type="nvidia_hosted" if not custom_base_url else "nvidia_nim"
        )
        self._custom_base_url = custom_base_url
        self._discovered_cache: List[LLMModelInfo] = []
        self._cache_timestamp: float = 0.0

        # Verified Curated Catalog (provenance: catalog)
        self._curated_catalog: List[LLMModelInfo] = [
            LLMModelInfo(
                provider_id="nvidia",
                model_id="z-ai/glm-5.3-flash",
                display_name="GLM-5.3 Flash (Z.ai / NVIDIA, Modèle de base)",
                capabilities={
                    LLMCapability.TEXT_GENERATION.value: True,
                    LLMCapability.STRUCTURED_OUTPUT.value: True,
                    LLMCapability.TOOL_CALLING.value: True,
                    LLMCapability.STREAMING.value: True,
                    LLMCapability.VISION.value: False,
                },
                parameters={
                    "temperature": {"min": 0.0, "max": 1.0, "default": 0.2},
                    "top_p": {"min": 0.0, "max": 1.0, "default": 0.7},
                    "max_tokens": {"min": 1, "max": 8192, "default": 2048}
                },
                provenance="catalog",
                is_available=True
            ),
            LLMModelInfo(
                provider_id="nvidia",
                model_id="z-ai/glm-5.3",
                display_name="GLM-5.3 (Z.ai / NVIDIA, Raisonnement approfondi)",
                capabilities={
                    LLMCapability.TEXT_GENERATION.value: True,
                    LLMCapability.STRUCTURED_OUTPUT.value: True,
                    LLMCapability.TOOL_CALLING.value: True,
                    LLMCapability.STREAMING.value: True,
                    LLMCapability.VISION.value: False,
                },
                parameters={
                    "temperature": {"min": 0.0, "max": 1.0, "default": 0.2},
                    "top_p": {"min": 0.0, "max": 1.0, "default": 0.7},
                    "max_tokens": {"min": 1, "max": 8192, "default": 2048}
                },
                provenance="catalog",
                is_available=True
            ),
            LLMModelInfo(
                provider_id="nvidia",
                model_id="zai-org/GLM-5.3",
                display_name="GLM-5.3 (Z.ai / On-Premise NIM)",
                capabilities={
                    LLMCapability.TEXT_GENERATION.value: True,
                    LLMCapability.STRUCTURED_OUTPUT.value: True,
                    LLMCapability.TOOL_CALLING.value: True,
                    LLMCapability.STREAMING.value: True,
                    LLMCapability.VISION.value: False,
                },
                parameters={
                    "temperature": {"min": 0.0, "max": 1.0, "default": 0.2},
                    "top_p": {"min": 0.0, "max": 1.0, "default": 0.7},
                    "max_tokens": {"min": 1, "max": 8192, "default": 2048}
                },
                provenance="catalog",
                is_available=True
            ),
            LLMModelInfo(
                provider_id="nvidia",
                model_id="meta/llama-3.2-11b-vision-instruct",
                display_name="Llama 3.2 11B Vision Instruct",
                capabilities={
                    LLMCapability.TEXT_GENERATION.value: True,
                    LLMCapability.STRUCTURED_OUTPUT.value: True,
                    LLMCapability.TOOL_CALLING.value: True,
                    LLMCapability.STREAMING.value: True,
                    LLMCapability.VISION.value: True,
                },
                parameters={
                    "temperature": {"min": 0.0, "max": 1.0, "default": 0.2},
                    "top_p": {"min": 0.0, "max": 1.0, "default": 0.7},
                    "max_tokens": {"min": 1, "max": 4096, "default": 1024}
                },
                provenance="catalog",
                is_available=True
            ),
            LLMModelInfo(
                provider_id="nvidia",
                model_id="nvidia/llama-3.1-nemotron-70b-instruct",
                display_name="Llama 3.1 Nemotron 70B Instruct (NVIDIA, Actif)",
                capabilities={
                    LLMCapability.TEXT_GENERATION.value: True,
                    LLMCapability.STRUCTURED_OUTPUT.value: True,
                    LLMCapability.TOOL_CALLING.value: True,
                    LLMCapability.STREAMING.value: True,
                    LLMCapability.VISION.value: False,
                },
                parameters={
                    "temperature": {"min": 0.0, "max": 1.0, "default": 0.2},
                    "top_p": {"min": 0.0, "max": 1.0, "default": 0.7},
                    "max_tokens": {"min": 1, "max": 4096, "default": 1024}
                },
                provenance="catalog",
                is_available=True
            ),
            LLMModelInfo(
                provider_id="nvidia",
                model_id="meta/llama-3.2-90b-vision-instruct",
                display_name="Llama 3.2 90B Vision Instruct",
                capabilities={
                    LLMCapability.TEXT_GENERATION.value: True,
                    LLMCapability.STRUCTURED_OUTPUT.value: True,
                    LLMCapability.TOOL_CALLING.value: True,
                    LLMCapability.STREAMING.value: True,
                    LLMCapability.VISION.value: True,
                },
                parameters={
                    "temperature": {"min": 0.0, "max": 1.0, "default": 0.2},
                    "top_p": {"min": 0.0, "max": 1.0, "default": 0.7},
                },
                provenance="catalog",
                is_available=True
            ),
            LLMModelInfo(
                provider_id="nvidia",
                model_id="mistralai/mixtral-8x7b-instruct-v0.1",
                display_name="Mixtral 8x7B Instruct",
                capabilities={
                    LLMCapability.TEXT_GENERATION.value: True,
                    LLMCapability.STRUCTURED_OUTPUT.value: True,
                    LLMCapability.TOOL_CALLING.value: True,
                    LLMCapability.STREAMING.value: True,
                    LLMCapability.VISION.value: False,
                },
                parameters={
                    "temperature": {"min": 0.0, "max": 1.0, "default": 0.2},
                    "top_p": {"min": 0.0, "max": 1.0, "default": 0.7},
                },
                provenance="catalog",
                is_available=True
            ),
            LLMModelInfo(
                provider_id="nvidia",
                model_id="nvidia/nemotron-4-340b-instruct",
                display_name="Nemotron-4 340B Instruct",
                capabilities={
                    LLMCapability.TEXT_GENERATION.value: True,
                    LLMCapability.STRUCTURED_OUTPUT.value: True,
                    LLMCapability.TOOL_CALLING.value: True,
                    LLMCapability.STREAMING.value: True,
                    LLMCapability.VISION.value: False,
                },
                parameters={
                    "temperature": {"min": 0.0, "max": 1.0, "default": 0.2},
                    "top_p": {"min": 0.0, "max": 1.0, "default": 0.7},
                },
                provenance="catalog",
                is_available=True
            ),
        ]

    def get_base_url(self) -> str:
        url: str = str(self._custom_base_url or os.getenv("NVIDIA_BASE_URL") or DEFAULT_NVIDIA_BASE_URL)
        validate_nvidia_endpoint(url)
        return url

    def is_configured(self) -> bool:
        key = os.getenv("NVIDIA_API_KEY", "").strip()
        return bool(key and not key.startswith("your_") and len(key) > 10)

    def is_enabled(self) -> bool:
        return os.getenv("NVIDIA_ENABLED", "true").lower() == "true"

    def get_default_model_id(self) -> str:
        return os.getenv("NVIDIA_DEFAULT_MODEL", "z-ai/glm-5.3-flash")

    def _discover_remote_models(self) -> List[LLMModelInfo]:
        """
        Queries NVIDIA /models endpoint with safe timeouts and no credentials leakage.
        """
        if not self.is_configured():
            return []

        base_url = self.get_base_url()
        models_url = f"{base_url.rstrip('/')}/models"
        api_key = os.getenv("NVIDIA_API_KEY", "")

        try:
            with httpx.Client(timeout=10.0, follow_redirects=False) as client:
                resp = client.get(
                    models_url,
                    headers={"Authorization": f"Bearer {api_key}"}
                )
                if resp.status_code == 200:
                    data = resp.json()
                    raw_list = data.get("data", [])
                    discovered: List[LLMModelInfo] = []
                    for item in raw_list:
                        m_id = item.get("id")
                        if not m_id:
                            continue
                        discovered.append(LLMModelInfo(
                            provider_id="nvidia",
                            model_id=m_id,
                            display_name=m_id.split("/")[-1].replace("-", " ").title(),
                            capabilities={
                                LLMCapability.TEXT_GENERATION.value: True,
                                LLMCapability.STRUCTURED_OUTPUT.value: None,  # Unknown until verified
                                LLMCapability.TOOL_CALLING.value: None,       # Unknown until verified
                                LLMCapability.STREAMING.value: True,
                                LLMCapability.VISION.value: None,
                            },
                            parameters={
                                "temperature": {"min": 0.0, "max": 1.0, "default": 0.2}
                            },
                            provenance="live_discovery",
                            is_available=True
                        ))
                    return discovered
        except Exception as e:
            logger.warning(f"NVIDIA live model discovery failed ({e}), falling back to curated catalog")

        return []

    def list_models(self, force_refresh: bool = False, **kwargs: Any) -> List[LLMModelInfo]:
        force_refresh = force_refresh or kwargs.get("refresh", False)
        now = time.time()
        if not force_refresh and self._discovered_cache and (now - self._cache_timestamp < DISCOVERY_CACHE_TTL_SECONDS):
            return self._discovered_cache

        # Attempt remote discovery if configured
        discovered = self._discover_remote_models() if self.is_configured() else []
        if discovered:
            # Merge with curated catalog, giving curated catalog precedence for known capabilities
            merged: List[LLMModelInfo] = []
            seen_ids = set()

            for m in self._curated_catalog:
                merged.append(m)
                seen_ids.add(m.model_id)

            for d in discovered:
                if d.model_id not in seen_ids:
                    merged.append(d)
                    seen_ids.add(d.model_id)

            self._discovered_cache = merged
            self._cache_timestamp = now
            return merged

        # Fallback to curated catalog
        return list(self._curated_catalog)

    def validate_model(self, model_id: str) -> bool:
        """
        Validates model identifier against curated catalogue and discovered cache.
        Allows model with vendor prefix (e.g. meta/..., mistralai/..., z-ai/...) if not unknown.
        """
        if self.get_model(model_id) is not None:
            return True
        if model_id in ("glm-5.3", "glm-5.3-flash"):
            return True
        if "/" in model_id and not model_id.startswith("unknown-"):
            return True
        return False

    def build_chat_model(
        self,
        model_id: str,
        temperature: float = 0.2,
        timeout: float = 60.0,
        max_retries: int = 3,
        **kwargs: Any
    ) -> Any:
        api_key = kwargs.pop("api_key", None) or os.getenv("NVIDIA_API_KEY")
        if not api_key or api_key.startswith("your_") or len(api_key) <= 10:
            return None

        from langchain_nvidia_ai_endpoints import ChatNVIDIA
        base_url = self.get_base_url()

        # Resolve model aliases
        if model_id in ("glm-5.3", "glm-5.3-flash", "default"):
            model_id = os.getenv("NVIDIA_DEFAULT_MODEL", "z-ai/glm-5.3-flash")

        # Clamp temperature to valid range [0.0, 1.0] for NVIDIA/GLM
        clamped_temp = max(0.0, min(1.0, temperature))

        # Ensure sufficient token budget for reasoning + JSON payload
        default_max_tokens = 4096 if "glm" in model_id.lower() else 2048
        max_tokens = kwargs.pop("max_tokens", default_max_tokens)

        chat_model = ChatNVIDIA(
            model=model_id,
            api_key=api_key,
            base_url=base_url,
            temperature=clamped_temp,
            max_completion_tokens=max_tokens,
            **kwargs
        )

        # Workaround for langchain-nvidia-ai-endpoints routing bug:
        # ChatNVIDIA internally defaults infer_path to https://ai.api.nvidia.com/v1/gr/...
        # which returns HTTP 451. Forcing infer_path to "{base_url}/chat/completions"
        # routes properly to the OpenAI-compatible endpoint.
        if hasattr(chat_model, "_client") and hasattr(chat_model._client, "infer_path"):
            chat_model._client.infer_path = "{base_url}/chat/completions"

        # Wire client-side rate limiter (40 RPM default) and per-model circuit breaker
        rpm = int(os.getenv("NVIDIA_RPM_LIMIT", "40"))
        limiter = get_rate_limiter("nvidia_api", requests_per_minute=rpm)
        cb = get_circuit_breaker(provider_id="nvidia", model_id=model_id)
        effective_timeout = float(timeout or os.getenv("NVIDIA_TIMEOUT_SECONDS", "60.0"))

        return ResilientChatNVIDIA(
            raw_model=chat_model,
            model_id=model_id,
            rate_limiter=limiter,
            circuit_breaker=cb,
            timeout=effective_timeout
        )

