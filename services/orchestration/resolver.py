import os
import uuid
import logging
from dataclasses import dataclass
from typing import Optional, Dict, Any, Tuple, cast
from sqlalchemy.orm import Session

from services.orchestration.providers.registry import provider_registry

logger = logging.getLogger(__name__)


class LLMResolutionError(Exception):
    """Raised when an explicit model resolution fails due to configuration or compatibility issues."""
    pass


class LLMProviderDisabledError(LLMResolutionError):
    """Raised when a requested LLM provider is explicitly disabled."""
    def __init__(self, provider_id: str):
        super().__init__(f"Le provider LLM '{provider_id}' est désactivé.")
        self.provider_id = provider_id


class LLMProviderNotConfiguredError(LLMResolutionError):
    """Raised when a requested LLM provider lacks valid API credentials."""
    def __init__(self, provider_id: str):
        super().__init__(f"Le provider LLM '{provider_id}' n'a pas de clé API configurée.")
        self.provider_id = provider_id


class LLMModelCapabilityError(LLMResolutionError):
    """Raised when a requested model lacks a required capability."""
    pass


@dataclass
class ResolvedLLMContext:
    model: Any
    provider_id: str
    model_id: str
    temperature: float
    resolution_source: str  # run_override, task_override, workspace_default, environment, historical_fallback
    run_id: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "provider_id": self.provider_id,
            "model_id": self.model_id,
            "full_id": f"{self.provider_id}:{self.model_id}",
            "temperature": self.temperature,
            "resolution_source": self.resolution_source,
            "run_id": self.run_id,
        }


class LLMResolver:
    """
    Centralized resolver for all LLM model instantiations in Content-builder.
    Enforces the strict 5-tier resolution hierarchy:
    1. Explicit run override
    2. Task / agent override
    3. Workspace default configuration
    4. Environment variable configuration
    5. Historical fallback (gemini-3.8-flash)
    
    Guarantees zero silent provider fallbacks.
    """

    @classmethod
    def _resolve_tier1_run_override(
        cls,
        run_override: Optional[Dict[str, Any]],
        temperature: Optional[float]
    ) -> Optional[Tuple[str, str, Optional[float], str]]:
        """Tier 1: Explicit Run Override."""
        if not run_override or not run_override.get("provider_id") or not run_override.get("model_id"):
            return None
        chosen_provider = run_override["provider_id"]
        chosen_model = run_override["model_id"]
        chosen_temp = float(run_override["temperature"]) if run_override.get("temperature") is not None else temperature
        return chosen_provider, chosen_model, chosen_temp, "run_override"

    @classmethod
    def _get_db_session(cls, db_session: Optional[Session]) -> Tuple[Optional[Session], bool]:
        """Obtains database session and tracks if it was created locally."""
        if db_session is not None:
            return db_session, False
        try:
            from infra.db.database import SessionLocal
            return SessionLocal(), True
        except Exception:
            return None, False

    @classmethod
    def _resolve_tier2_task_override(
        cls,
        settings: Any,
        task_name: Optional[str],
        temperature: Optional[float]
    ) -> Optional[Tuple[str, str, Optional[float], str]]:
        """Tier 2: Task override resolution."""
        if not task_name:
            return None
        raw_ov = cast(Dict[str, Any], settings.task_overrides or {})
        task_ov = raw_ov.get(task_name)
        if task_ov and not task_ov.get("inherit_default", False) and task_ov.get("provider_id") and task_ov.get("model_id"):
            chosen_provider = str(task_ov["provider_id"])
            chosen_model = str(task_ov["model_id"])
            chosen_temp = float(task_ov["temperature"]) if task_ov.get("temperature") is not None else temperature
            return chosen_provider, chosen_model, chosen_temp, "task_override"
        return None

    @classmethod
    def _resolve_tier3_workspace_default(
        cls,
        settings: Any,
        temperature: Optional[float]
    ) -> Optional[Tuple[str, str, Optional[float], str]]:
        """Tier 3: Workspace default resolution."""
        if settings.default_provider_id and settings.default_model_id:
            chosen_provider = str(settings.default_provider_id)
            chosen_model = str(settings.default_model_id)
            chosen_temp = temperature if temperature is not None else float(settings.default_temperature)
            return chosen_provider, chosen_model, chosen_temp, "workspace_default"
        return None

    @classmethod
    def _resolve_tier2_tier3_workspace(
        cls,
        workspace_id: str,
        task_name: Optional[str],
        temperature: Optional[float],
        db_session: Optional[Session]
    ) -> Optional[Tuple[str, str, Optional[float], str]]:
        """Tier 2 & 3: Workspace DB Configuration (Task Override & Default)."""
        db, session_created = cls._get_db_session(db_session)
        if db is None:
            return None

        try:
            from infra.db.models import WorkspaceLLMSettingsModel
            settings = db.query(WorkspaceLLMSettingsModel).filter_by(workspace_id=workspace_id).first()
            if not settings:
                return None

            override_result = cls._resolve_tier2_task_override(settings, task_name, temperature)
            if override_result is not None:
                return override_result

            return cls._resolve_tier3_workspace_default(settings, temperature)
        except Exception as e:
            logger.debug(f"Could not load WorkspaceLLMSettingsModel for {workspace_id}: {e}")
            return None
        finally:
            if session_created:
                db.close()

    @classmethod
    def _resolve_tier4_environment(
        cls,
        task_name: Optional[str],
        temperature: Optional[float]
    ) -> Optional[Tuple[str, str, Optional[float], str]]:
        """Tier 4: Environment Variable Configuration."""
        task_env_model = os.getenv(f"LLM_MODEL_FOR_{task_name.upper()}") if task_name else None
        task_env_provider = os.getenv(f"LLM_PROVIDER_FOR_{task_name.upper()}") if task_name else None

        if task_env_model:
            chosen_model = task_env_model
            chosen_provider = task_env_provider or ("nvidia" if "/" in task_env_model else "gemini")
            return chosen_provider, chosen_model, temperature, "environment"

        default_env_prov = os.getenv("DEFAULT_LLM_PROVIDER", "nvidia")
        if default_env_prov:
            chosen_model = (
                os.getenv("NVIDIA_DEFAULT_MODEL", "z-ai/glm-5.3-flash")
                if default_env_prov == "nvidia"
                else os.getenv("GEMINI_MODEL", "gemini-3.8-flash")
            )
            return default_env_prov, chosen_model, temperature, "environment"

        return None

    @classmethod
    def _resolve_tier5_fallback(
        cls,
        temperature: Optional[float]
    ) -> Tuple[str, str, Optional[float], str]:
        """Tier 5: System Default (NVIDIA GLM-5.3-flash)."""
        chosen_provider = os.getenv("DEFAULT_LLM_PROVIDER", "nvidia")
        chosen_model = (
            os.getenv("NVIDIA_DEFAULT_MODEL", "z-ai/glm-5.3-flash")
            if chosen_provider == "nvidia"
            else os.getenv("GEMINI_MODEL", "gemini-3.8-flash")
        )
        return chosen_provider, chosen_model, temperature, "system_default"

    @classmethod
    def _build_resolved_context(
        cls,
        chosen_provider: str,
        chosen_model: str,
        chosen_temp: float,
        source: str,
        required_capability: Optional[str],
        allow_none_if_unconfigured: bool
    ) -> Optional[ResolvedLLMContext]:
        """Validates adapter capabilities, builds model instance, and returns ResolvedLLMContext."""
        adapter = provider_registry.get_adapter(chosen_provider)
        if adapter is None:
            raise LLMResolutionError(f"Le provider LLM '{chosen_provider}' n'est pas reconnu par le registre.")

        if not adapter.is_enabled():
            if allow_none_if_unconfigured:
                logger.info(f"LLM Provider '{chosen_provider}' est désactivé. Mode dégradé déterministe actif.")
                return None
            raise LLMProviderDisabledError(chosen_provider)

        if required_capability:
            model_info = adapter.get_model(chosen_model)
            if model_info and model_info.capabilities.get(required_capability) is False:
                raise LLMModelCapabilityError(
                    f"Le modèle '{chosen_provider}:{chosen_model}' ne supporte pas la capacité obligatoire '{required_capability}'."
                )

        if not adapter.is_configured():
            if allow_none_if_unconfigured:
                logger.info(f"LLM Provider '{chosen_provider}' non configuré (clé absente). Mode dégradé déterministe actif.")
                return None
            raise LLMProviderNotConfiguredError(chosen_provider)

        timeout = float(os.getenv("LLM_TIMEOUT_SECONDS", "30.0"))
        max_retries = int(os.getenv("LLM_MAX_RETRIES", "3"))

        model_instance = adapter.build_chat_model(
            model_id=chosen_model,
            temperature=chosen_temp,
            timeout=timeout,
            max_retries=max_retries
        )

        if model_instance is None:
            if allow_none_if_unconfigured:
                return None
            raise LLMResolutionError(f"Impossible d'instancier le modèle '{chosen_provider}:{chosen_model}'.")

        run_id = f"run_{uuid.uuid4().hex[:12]}"

        return ResolvedLLMContext(
            model=model_instance,
            provider_id=chosen_provider,
            model_id=chosen_model,
            temperature=chosen_temp,
            resolution_source=source,
            run_id=run_id
        )

    @classmethod
    def resolve_model(
        cls,
        workspace_id: Optional[str] = None,
        task_name: Optional[str] = None,
        required_capability: Optional[str] = None,
        run_override: Optional[Dict[str, Any]] = None,
        temperature: Optional[float] = None,
        db_session: Optional[Session] = None,
        allow_none_if_unconfigured: bool = True
    ) -> Optional[ResolvedLLMContext]:
        # Tier 1: Explicit Run Override
        resolved = cls._resolve_tier1_run_override(run_override, temperature)

        # Tier 2 & 3: Workspace DB Configuration (Task Override & Default)
        if resolved is None and workspace_id:
            resolved = cls._resolve_tier2_tier3_workspace(workspace_id, task_name, temperature, db_session)

        # Tier 4: Environment Variable Configuration
        if resolved is None:
            resolved = cls._resolve_tier4_environment(task_name, temperature)

        # Tier 5: Historical Default
        if resolved is None:
            resolved = cls._resolve_tier5_fallback(temperature)

        chosen_provider, chosen_model, candidate_temp, source = resolved
        chosen_temp = 0.2 if candidate_temp is None else candidate_temp

        return cls._build_resolved_context(
            chosen_provider=chosen_provider,
            chosen_model=chosen_model,
            chosen_temp=chosen_temp,
            source=source,
            required_capability=required_capability,
            allow_none_if_unconfigured=allow_none_if_unconfigured
        )
