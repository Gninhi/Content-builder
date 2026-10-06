import os
import logging
from typing import Dict, Any, List
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# ------------------------------------------------------------------------------
# Pydantic Output Schemas for Gemini Structured Outputs
# ------------------------------------------------------------------------------
class GeneratedIdeaEvidence(BaseModel):
    source_id: str = Field(..., description="ID ou URL de la source vérifiée")
    claim: str = Field(..., description="Fait ou donnée probante tirée de la source")


class GeneratedIdea(BaseModel):
    title: str = Field(..., description="Titre percutant de l'idée")
    angle: str = Field(..., description="Angle éditorial précis et positionnement")
    target_audience: str = Field(..., description="Segment d'audience ciblée")
    recommended_formats: List[str] = Field(default_factory=lambda: ["linkedin", "x"])
    evidence: List[GeneratedIdeaEvidence] = Field(default_factory=list)
    novelty_score: float = Field(..., ge=0.0, le=10.0, description="Nouveauté (0-10)")
    relevance_score: float = Field(..., ge=0.0, le=10.0, description="Alignement marque (0-10)")
    effort_score: float = Field(..., ge=0.0, le=10.0, description="Complexité de production (0-10)")
    priority: str = Field("high", description="'high', 'medium', ou 'low'")
    risks: List[str] = Field(default_factory=list, description="Risques identifiés")


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
# Model Factory
# ------------------------------------------------------------------------------
def is_gemini_available() -> bool:
    """Checks if a valid Google Gemini API key is configured."""
    key = os.getenv("GOOGLE_API_KEY", "")
    return bool(key and not key.startswith("your_") and len(key) > 10)


def get_gemini_model(model_type: str = "fast", temperature: float = 0.2):
    """
    Instantiates Google Gemini (gemini-3.8-flash) via langchain-google-genai.
    Allows configuring fast vs reasoning model via environment variables.
    """
    if not is_gemini_available():
        return None

    if model_type == "reasoning":
        model_name = os.getenv("GEMINI_REASONING_MODEL", os.getenv("GEMINI_MODEL", "gemini-3.8-flash"))
    else:
        model_name = os.getenv("GEMINI_FAST_MODEL", os.getenv("GEMINI_MODEL", "gemini-3.8-flash"))

    api_key = os.getenv("GOOGLE_API_KEY")

    try:
        from langchain_google_genai import ChatGoogleGenerativeAI
        return ChatGoogleGenerativeAI(
            model=model_name,
            google_api_key=api_key,
            temperature=temperature
        )
    except Exception as e:
        logger.warning(f"Failed to instantiate ChatGoogleGenerativeAI: {e}")
        return None
