"""
Veille Technologique Query Bank & Qualification Rubric
Covers 3 strategic axes: IA, Frameworks & Outils, Évolution des Métiers (France & Europe).
"""

from typing import List, Dict, Any
import random
import time

AXIS_IA = "ia"
AXIS_FRAMEWORKS = "frameworks"
AXIS_METIERS = "metiers"

SUPPORTED_AXES = [AXIS_IA, AXIS_FRAMEWORKS, AXIS_METIERS]

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


def compute_qualification_score(
    trust_level: str,
    days_old: int,
    has_concrete_facts: bool,
    is_strategic: bool,
    is_exec_relevant: bool,
    attribution_verified: bool = True,
) -> Dict[str, Any]:
    """Computes transparent qualification breakdown on a 0.0 - 5.0 scale (harmonized threshold: 3.2)."""
    trust_score = 1.0 if trust_level == "A" else (0.7 if trust_level == "B" else 0.4)
    freshness_score = 1.0 if days_old <= 7 else (0.7 if days_old <= 30 else 0.3)
    fact_score = (1.0 if attribution_verified else 0.2) if has_concrete_facts else 0.4
    impact_score = 1.0 if is_strategic else 0.5
    exec_score = 1.0 if is_exec_relevant else 0.5

    total = round(trust_score + freshness_score + fact_score + impact_score + exec_score, 2)
    is_qualified = total >= QUALIFICATION_THRESHOLD and attribution_verified

    return {
        "score": total,
        "is_qualified": is_qualified,
        "breakdown": {
            "authority": trust_score,
            "freshness": freshness_score,
            "fact_density": fact_score,
            "strategic_impact": impact_score,
            "executive_relevance": exec_score,
            "attribution_verified": attribution_verified,
            "requires_confirmation": not attribution_verified,
        },
    }
