import os
import logging
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from packages.resilience.circuit_breaker import CircuitBreaker

logger = logging.getLogger(__name__)


# ------------------------------------------------------------------------------
# Pydantic Output Schemas for Gemini Structured Outputs
# ------------------------------------------------------------------------------
class GeneratedIdeaEvidence(BaseModel):
    source_id: str = Field(..., description="ID ou URL de la source vérifiée")
    claim: str = Field(..., description="Fait ou donnée probante tirée de la source")


class GeneratedIdea(BaseModel):
    title: str = Field(..., description="Titre éditorial percutant (sans préfixe de catégorie)")
    angle: str = Field(..., description="Angle éditorial précis et positionnement")
    target_audience: str = Field(..., description="Segment d'audience ciblée")
    recommended_formats: List[str] = Field(default_factory=lambda: ["linkedin", "x"])
    evidence: List[GeneratedIdeaEvidence] = Field(default_factory=list)
    novelty_score: float = Field(..., ge=0.0, le=100.0, description="Nouveauté (0-100)")
    relevance_score: float = Field(..., ge=0.0, le=100.0, description="Alignement marque (0-100)")
    effort_score: float = Field(..., ge=0.0, le=100.0, description="Complexité de production (0-100)")
    priority: str = Field("high", description="'high', 'medium', ou 'low'")
    risks: List[str] = Field(default_factory=list, description="Risques identifiés")
    signal_id: Optional[str] = None


class GeneratedIdeasBatch(BaseModel):
    ideas: List[GeneratedIdea]


class GeneratedClaim(BaseModel):
    claim: str
    source_id: str
    verified: bool = True
    confidence_score: float = 1.0


class GeneratedVariant(BaseModel):
    platform: str = Field(..., description="Plateforme cible: 'linkedin' ou 'x'")
    hook: str = Field(..., description="Accroche immédiate / hook")
    body: str = Field(..., description="Corps complet du post")
    cta: str = Field(..., description="Appel à l'action")
    hashtags: List[str] = Field(default_factory=list)
    media_spec: Dict[str, Any] = Field(default_factory=dict)
    claims: List[GeneratedClaim] = Field(default_factory=list)


class GeneratedVariantsBatch(BaseModel):
    variants: List[GeneratedVariant]


class GeneratedStrategyHypothesis(BaseModel):
    pillar: str
    fact: str
    hypothesis: str
    confidence_level: float = Field(..., ge=0.0, le=1.0)
    recommended_action: str


class GeneratedRecommendation(BaseModel):
    id: str
    title: str
    expected_impact: str
    status: str = "PROPOSED_FOR_HUMAN_APPROVAL"


class GeneratedStrategyBatch(BaseModel):
    hypotheses: List[GeneratedStrategyHypothesis]
    recommendations: List[GeneratedRecommendation]


# ------------------------------------------------------------------------------
# Model Factory & Multi-Provider Resolution
# ------------------------------------------------------------------------------
def is_gemini_available() -> bool:
    """Checks if a valid Google Gemini API key is configured."""
    key = os.getenv("GOOGLE_API_KEY", "")
    return bool(key and not key.startswith("your_") and len(key) > 10)


def is_nvidia_available() -> bool:
    """Checks if a valid NVIDIA API key is configured."""
    key = os.getenv("NVIDIA_API_KEY", "")
    return bool(key and not key.startswith("your_") and len(key) > 10)


def resolve_and_get_llm(
    task_name: Optional[str] = None,
    workspace_id: Optional[str] = None,
    run_override: Optional[Dict[str, Any]] = None,
    temperature: Optional[float] = None,
    required_capability: Optional[str] = None,
    allow_none_if_unconfigured: bool = True
):
    """
    Central resolution entrypoint for all pipeline tasks and agents.
    Dispatches to LLMResolver to resolve provider and model according to the 5-tier hierarchy.
    Freezes and returns the run context tuple (model_instance, resolved_context).
    """
    from services.orchestration.resolver import LLMResolver
    ctx = LLMResolver.resolve_model(
        workspace_id=workspace_id,
        task_name=task_name,
        required_capability=required_capability,
        run_override=run_override,
        temperature=temperature,
        allow_none_if_unconfigured=allow_none_if_unconfigured
    )
    if ctx is None:
        return None, None
    return ctx.model, ctx


def get_gemini_model(
    model_type: str = "fast",
    temperature: float = 0.2,
    workspace_id: Optional[str] = None,
    task_name: Optional[str] = None,
    run_override: Optional[Dict[str, Any]] = None
):
    """
    Instantiates an LLM chat model.
    Prioritizes the multi-provider resolver if custom workspace/task/run settings exist,
    while maintaining 100% backward compatibility for direct Gemini callers.
    """
    # If run override or workspace is specified, route via resolver
    if workspace_id or run_override:
        model, _ = resolve_and_get_llm(
            task_name=task_name or ("production" if model_type == "reasoning" else "ideation"),
            workspace_id=workspace_id,
            run_override=run_override,
            temperature=temperature,
            allow_none_if_unconfigured=True
        )
        if model is not None:
            return model

    if not is_gemini_available():
        return None

    if model_type == "reasoning":
        model_name = os.getenv("GEMINI_REASONING_MODEL", os.getenv("GEMINI_MODEL", "gemini-3.8-flash"))
    else:
        model_name = os.getenv("GEMINI_FAST_MODEL", os.getenv("GEMINI_MODEL", "gemini-3.8-flash"))

    api_key = os.getenv("GOOGLE_API_KEY")

    try:
        from langchain_google_genai import ChatGoogleGenerativeAI
        timeout = float(os.getenv("LLM_TIMEOUT_SECONDS", "30.0"))
        max_retries = int(os.getenv("LLM_MAX_RETRIES", "3"))
        return ChatGoogleGenerativeAI(
            model=model_name,
            google_api_key=api_key,
            temperature=temperature,
            timeout=timeout,
            max_retries=max_retries
        )
    except Exception as e:
        logger.warning(f"Failed to instantiate ChatGoogleGenerativeAI: {e}")
        return None


def get_gemini_model_for_task(
    task_name: str,
    temperature: Optional[float] = None,
    workspace_id: Optional[str] = None,
    run_override: Optional[Dict[str, Any]] = None
):
    """
    Returns configured model for a specific pipeline task:
    - 'ideation'
    - 'production'
    - 'qa_judge'
    - 'strategy'
    - 'rewrite'
    Routes through LLMResolver to honor workspace overrides, task overrides, and NVIDIA provider.
    """
    temp = temperature if temperature is not None else 0.2
    model, _ = resolve_and_get_llm(
        task_name=task_name,
        workspace_id=workspace_id,
        run_override=run_override,
        temperature=temp,
        allow_none_if_unconfigured=True
    )
    if model is not None:
        return model

    # Fallback to direct Gemini task instantiation if available
    env_var_key = f"LLM_MODEL_FOR_{task_name.upper()}"
    model_name = os.getenv(env_var_key, os.getenv("GEMINI_MODEL", "gemini-3.8-flash"))

    if not is_gemini_available():
        return None

    api_key = os.getenv("GOOGLE_API_KEY")
    try:
        from langchain_google_genai import ChatGoogleGenerativeAI
        timeout = float(os.getenv("LLM_TIMEOUT_SECONDS", "30.0"))
        max_retries = int(os.getenv("LLM_MAX_RETRIES", "3"))
        return ChatGoogleGenerativeAI(
            model=model_name,
            google_api_key=api_key,
            temperature=temp,
            timeout=timeout,
            max_retries=max_retries
        )
    except Exception as e:
        logger.warning(f"Failed to instantiate ChatGoogleGenerativeAI for task {task_name}: {e}")
        return None


# Global resilient circuit breaker for LLM invocations
llm_circuit_breaker = CircuitBreaker(
    failure_threshold=int(os.getenv("LLM_CIRCUIT_BREAKER_THRESHOLD", "3")),
    recovery_timeout=float(os.getenv("LLM_CIRCUIT_BREAKER_RECOVERY", "30.0")),
    name="gemini_llm_circuit_breaker"
)

