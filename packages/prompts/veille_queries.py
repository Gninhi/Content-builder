"""
Veille Technologique Query Bank & Qualification Rubric
Covers 3 strategic axes: IA, Frameworks & Outils, Évolution des Métiers (France & Europe).
"""

from typing import List, Dict, Any, Optional, Literal
import re
import time
from pydantic import BaseModel, Field

AXIS_IA = "ia"
AXIS_FRAMEWORKS = "frameworks"
AXIS_METIERS = "metiers"

SUPPORTED_AXES = [AXIS_IA, AXIS_FRAMEWORKS, AXIS_METIERS]


class SignalFactItem(BaseModel):
    claim: str = Field(..., min_length=15, max_length=280)
    quote: str = Field(..., min_length=12, max_length=240)
    source_url: str
    verified: bool = True


class SignalScoreBreakdown(BaseModel):
    trust_score: float = Field(..., ge=0.0, le=1.2)
    recency_score: float = Field(..., ge=0.0, le=0.8)
    fact_density_score: float = Field(..., ge=0.0, le=0.7)
    strategic_fit_score: float = Field(..., ge=0.0, le=1.3)
    executive_relevance_score: float = Field(..., ge=0.0, le=1.0)
    total_score: float = Field(..., ge=0.0, le=5.0)
    passed_gate: bool
    rejection_reason: Optional[str] = None


class SignalEnrichmentOutput(BaseModel):
    summary: str = Field(..., min_length=60, max_length=600)
    executive_takeaway: str = Field(..., min_length=40, max_length=320)
    facts: List[SignalFactItem] = Field(..., min_length=1, max_length=5)
    axis: Literal["ia", "frameworks", "metiers"]
    pillar_tags: List[str] = Field(default_factory=list)
    score_breakdown: SignalScoreBreakdown


def verify_quote_in_text(quote: str, source_text: str) -> bool:
    """
    Verifies whether a quote extracted by an LLM or extractor actually appears in the source text.
    Checks normalized substring match first, then falls back to high token overlap (>= 0.80)
    for minor whitespace/punctuation differences.
    """
    if not quote or not source_text:
        return False
    norm_quote = re.sub(r"\s+", " ", quote.strip().lower())
    norm_source = re.sub(r"\s+", " ", source_text.strip().lower())
    if len(norm_quote) < 10:
        return False
    if norm_quote in norm_source:
        return True
    # Strip punctuation and check substring or token overlap
    clean_quote = re.sub(r"[^\w\s]", " ", norm_quote)
    clean_source = re.sub(r"[^\w\s]", " ", norm_source)
    clean_quote = re.sub(r"\s+", " ", clean_quote).strip()
    clean_source = re.sub(r"\s+", " ", clean_source).strip()
    if clean_quote and clean_quote in clean_source:
        return True
    q_tokens = [t for t in clean_quote.split() if len(t) > 2]
    if len(q_tokens) < 3:
        return False
    s_token_set = set(clean_source.split())
    matched = sum(1 for t in q_tokens if t in s_token_set)
    return (matched / len(q_tokens)) >= 0.85


# Targeted Query Templates with site: filters and temporal grounding
VEILLE_QUERY_BANK: Dict[str, List[Dict[str, Any]]] = {
    AXIS_IA: [
        {
            "query": "EU AI Act compliance general purpose AI models requirements",
            "lang": "en",
            "focus": "Gouvernance & Régulation",
            "trust_target": "A",
        },
        {
            "query": "site:arxiv.org LLM reasoning latency cost trade-offs multi-agent",
            "lang": "en",
            "focus": "Recherche & Architectures de Raisonnement",
            "trust_target": "A",
        },
        {
            "query": "gouvernance IA générative entreprise sécurité prompt injection déploiement",
            "lang": "fr",
            "focus": "Sécurité & Déploiement en Production",
            "trust_target": "B",
        },
        {
            "query": "site:cnil.fr intelligence artificielle recommandations données personnelles",
            "lang": "fr",
            "focus": "Régulation & RGPD en France",
            "trust_target": "A",
        },
        {
            "query": "benchmarks enterprise LLMs multimodal reasoning production 2026",
            "lang": "en",
            "focus": "Performances & Modèles d'Entreprise",
            "trust_target": "B",
        },
    ],
    AXIS_FRAMEWORKS: [
        {
            "query": "LangGraph multi-agent architecture production patterns FastAPI async",
            "lang": "en",
            "focus": "Frameworks Agentiques & LangGraph",
            "trust_target": "A",
        },
        {
            "query": "vLLM inference optimization serving throughput latency benchmarks",
            "lang": "en",
            "focus": "Moteurs d'Inférence & Optimisation",
            "trust_target": "A",
        },
        {
            "query": "Playwright headless browser automation AI agents anti-blocking best practices",
            "lang": "en",
            "focus": "Automatisation & Web Scraping Éthique",
            "trust_target": "B",
        },
        {
            "query": "architectures logicielles systèmes multi-agents Python scalabilité production",
            "lang": "fr",
            "focus": "Ingénierie Logicielle & Agentic Systems",
            "trust_target": "B",
        },
        {
            "query": "open-source agent framework evaluation MCP protocol safety",
            "lang": "en",
            "focus": "Protocoles d'Agents & MCP",
            "trust_target": "A",
        },
    ],
    AXIS_METIERS: [
        {
            "query": "impact IA générative transformation métiers ingénierie logicielle France DARES",
            "lang": "fr",
            "focus": "Impact sur les Développeurs & Ingénieurs en France",
            "trust_target": "A",
        },
        {
            "query": "site:lesechos.fr intelligence artificielle productivité emploi cadres dirigeants",
            "lang": "fr",
            "focus": "Transformation Économique & Décideurs",
            "trust_target": "A",
        },
        {
            "query": "site:usine-digitale.fr IA compétences formation continue recrutement tech",
            "lang": "fr",
            "focus": "Compétences & Évolution RH Tech",
            "trust_target": "B",
        },
        {
            "query": "European commission future of work AI workforce automation statistics",
            "lang": "en",
            "focus": "Statistiques Emploi & Travail en Europe",
            "trust_target": "A",
        },
        {
            "query": "adoption IA juridique finance santé productivité études terrain Europe",
            "lang": "fr",
            "focus": "Secteurs Régulés : Juridique, Santé, Finance",
            "trust_target": "B",
        },
    ],
}


def get_queries_for_axis(axis: str, count: int = 2) -> List[Dict[str, Any]]:
    """Returns rotated queries for a specific axis."""
    axis_norm = axis.lower().strip()
    bank = VEILLE_QUERY_BANK.get(axis_norm, VEILLE_QUERY_BANK[AXIS_IA])
    # Deterministic rotation based on current minute to ensure variety across calls
    shift = int(time.time() / 300) % len(bank)
    rotated = bank[shift:] + bank[:shift]
    return rotated[:count]


def get_all_rotated_queries(count_per_axis: int = 1) -> List[Dict[str, Any]]:
    """Returns rotated queries across all 3 axes."""
    all_q: List[Dict[str, Any]] = []
    for axis in SUPPORTED_AXES:
        queries = get_queries_for_axis(axis, count=count_per_axis)
        for q in queries:
            item = dict(q)
            item["axis"] = axis
            all_q.append(item)
    return all_q


# ---------------- Qualification Rubric (0.0 to 5.0) ----------------
QUALIFICATION_RUBRIC = {
    "source_authority": {
        "max": 1.0,
        "description": "Niveau de fiabilité de la source (Niveau A=1.0, B=0.7, C=0.4).",
    },
    "temporal_freshness": {
        "max": 1.0,
        "description": "Fraîcheur temporelle (< 7 jours = 1.0, < 30 jours = 0.7, > 30 jours = 0.3).",
    },
    "fact_density": {
        "max": 1.0,
        "description": "Présence de chiffres concrets, benchmarks, citations d'auteurs ou méthodologies vérifiables.",
    },
    "strategic_impact": {
        "max": 1.0,
        "description": "Caractère structurant ou de rupture versus simple mise à jour incrémentale.",
    },
    "executive_relevance": {
        "max": 1.0,
        "description": "Pertinence directe pour les Tech Leads, DSI, et décideurs d'entreprises en France/Europe.",
    },
}


QUALIFICATION_THRESHOLD: float = 3.2

_STRATEGIC_KEYWORDS: Dict[str, List[str]] = {
    AXIS_IA: [
        "ai act", "gpai", "llm", "reasoning", "agent", "multi-agent", "gouvernance",
        "sécurité", "prompt injection", "benchmark", "inference", "rag", "cnil",
        "modèle", "model", "foundation", "safety", "hallucination", "evaluation",
    ],
    AXIS_FRAMEWORKS: [
        "langgraph", "langchain", "fastapi", "vllm", "playwright", "mcp", "sdk",
        "orchestration", "framework", "architecture", "observability", "opentelemetry",
        "sandbox", "sqlalchemy", "async", "latency", "throughput", "release",
    ],
    AXIS_METIERS: [
        "emploi", "compétences", "productivité", "transformation", "dsi", "cto",
        "ingénieur", "développeur", "organisation", "adoption", "roi", "gouvernance",
        "formation", "workforce", "enterprise", "métier", "juridique", "finance",
    ],
}

_EXEC_KEYWORDS: List[str] = [
    "production", "enterprise", "entreprise", "gouvernance", "compliance", "conformité",
    "architecture", "security", "sécurité", "cost", "coût", "latency", "latence",
    "roi", "audit", "risk", "risque", "benchmark", "scale", "scalabilité", "dsi", "cto",
    "deployment", "déploiement", "regulation", "régulation", "policy", "stratégie",
]


def evaluate_signal_text_features(
    title: str,
    text: str,
    axis: str = AXIS_IA,
    pillars: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Analyzes real extracted text and title to compute explainable sub-scores:
    - fact_density_score (0.0 .. 0.7)
    - strategic_fit_score (0.0 .. 1.3)
    - executive_relevance_score (0.0 .. 1.0)
    """
    combined = f"{title or ''}\n{text or ''}".strip()
    lower = combined.lower()
    char_len = len(combined)

    # 1. Fact density (max 0.7): numbers/metrics, percentages, dates/versions, text substance
    numbers_found = len(re.findall(r"\b\d+(?:[.,]\d+)?%?\b", combined))
    sentences_found = len([s for s in re.split(r"[.!?;\n]", combined) if len(s.strip()) > 30])
    fact_density = 0.15
    if char_len >= 120:
        fact_density += 0.15
    if char_len >= 350:
        fact_density += 0.15
    if numbers_found >= 1:
        fact_density += 0.15
    if numbers_found >= 3 or sentences_found >= 3:
        fact_density += 0.10
    fact_density_score = round(min(0.7, fact_density), 2)

    # 2. Strategic fit (max 1.3): axis keywords + workspace pillars
    axis_norm = (axis or AXIS_IA).lower().strip()
    kw_list = list(_STRATEGIC_KEYWORDS.get(axis_norm, _STRATEGIC_KEYWORDS[AXIS_IA]))
    for other_kws in _STRATEGIC_KEYWORDS.values():
        for k in other_kws:
            if k not in kw_list:
                kw_list.append(k)
    if pillars:
        for p in pillars:
            for tok in re.split(r"\W+", p.lower()):
                if len(tok) > 2 and tok not in kw_list:
                    kw_list.append(tok)

    matched_strategic = sum(1 for kw in kw_list if kw in lower)
    if matched_strategic >= 4:
        strategic_fit_score = 1.3
    elif matched_strategic == 3:
        strategic_fit_score = 1.1
    elif matched_strategic == 2:
        strategic_fit_score = 0.9
    elif matched_strategic == 1:
        strategic_fit_score = 0.65
    else:
        strategic_fit_score = 0.25

    # 3. Executive relevance (max 1.0): decision, production, governance, risk, ROI signals
    matched_exec = sum(1 for kw in _EXEC_KEYWORDS if kw in lower)
    if matched_exec >= 3:
        exec_score = 1.0
    elif matched_exec == 2:
        exec_score = 0.85
    elif matched_exec == 1:
        exec_score = 0.65
    else:
        exec_score = 0.3

    return {
        "fact_density_score": round(fact_density_score, 2),
        "strategic_fit_score": round(strategic_fit_score, 2),
        "executive_relevance_score": round(exec_score, 2),
        "has_concrete_facts": fact_density_score >= 0.45,
        "is_strategic": strategic_fit_score >= 0.8,
        "is_exec_relevant": exec_score >= 0.65,
        "matched_strategic_keywords": matched_strategic,
        "matched_exec_keywords": matched_exec,
        "char_length": char_len,
    }


def compute_qualification_score(
    trust_level: str,
    days_old: Optional[int],
    has_concrete_facts: Optional[bool] = None,
    is_strategic: Optional[bool] = None,
    is_exec_relevant: Optional[bool] = None,
    attribution_verified: bool = True,
    *,
    title: Optional[str] = None,
    text: Optional[str] = None,
    axis: str = AXIS_IA,
    pillars: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Computes an explainable qualification breakdown on a 0.0 - 5.0 scale (threshold: 3.2).
    When `text` or `title` is provided, derives fact_density_score (max 0.7),
    strategic_fit_score (max 1.3), and executive_relevance_score (max 1.0) from real content,
    and penalizes missing publication dates (days_old is None -> 0.25 instead of max 0.8).
    """
    tl = (trust_level or "B").upper().strip()

    if text is not None or title is not None:
        trust_score = 1.2 if tl == "A" else (0.85 if tl == "B" else 0.45)
        if days_old is None:
            recency_score = 0.25  # Missing publication date is penalized, never rewarded
        elif days_old <= 7:
            recency_score = 0.8
        elif days_old <= 30:
            recency_score = 0.6
        elif days_old <= 90:
            recency_score = 0.35
        else:
            recency_score = 0.1

        feats = evaluate_signal_text_features(title or "", text or "", axis=axis, pillars=pillars)
        fact_score = feats["fact_density_score"] if attribution_verified else round(feats["fact_density_score"] * 0.3, 2)
        impact_score = feats["strategic_fit_score"]
        exec_score = feats["executive_relevance_score"]
        authority_compat = 1.0 if tl == "A" else (0.7 if tl == "B" else 0.4)
    else:
        # Backward-compatible mode for direct boolean rubric calls
        trust_score = 1.0 if tl == "A" else (0.7 if tl == "B" else 0.4)
        authority_compat = trust_score
        if days_old is None:
            recency_score = 0.3
        elif days_old <= 7:
            recency_score = 1.0
        elif days_old <= 30:
            recency_score = 0.7
        else:
            recency_score = 0.3
        fact_score = (1.0 if attribution_verified else 0.2) if bool(has_concrete_facts) else 0.4
        impact_score = 1.0 if bool(is_strategic) else 0.5
        exec_score = 1.0 if bool(is_exec_relevant) else 0.5

    total = round(min(5.0, max(0.0, trust_score + recency_score + fact_score + impact_score + exec_score)), 2)
    is_qualified = total >= QUALIFICATION_THRESHOLD and attribution_verified
    rejection_reason = None
    if not attribution_verified:
        rejection_reason = "Source ou citation non vérifiable dans le texte extrait."
    elif not is_qualified:
        rejection_reason = f"Score de qualification insuffisant ({total} < {QUALIFICATION_THRESHOLD})."

    return {
        "score": total,
        "is_qualified": is_qualified,
        "passed_gate": is_qualified,
        "rejection_reason": rejection_reason,
        "breakdown": {
            "trust_score": round(trust_score, 2),
            "recency_score": round(recency_score, 2),
            "fact_density_score": round(fact_score, 2),
            "strategic_fit_score": round(impact_score, 2),
            "executive_relevance_score": round(exec_score, 2),
            "total_score": total,
            "passed_gate": is_qualified,
            "rejection_reason": rejection_reason,
            # Legacy keys preserved for API/UI compatibility
            "authority": authority_compat,
            "freshness": round(recency_score, 2),
            "fact_density": round(fact_score, 2),
            "strategic_impact": round(impact_score, 2),
            "executive_relevance": round(exec_score, 2),
            "attribution_verified": attribution_verified,
            "date_missing_penalized": days_old is None,
            "requires_confirmation": not attribution_verified,
        },
    }
