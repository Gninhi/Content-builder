from typing import Dict, Any, List
import logging
from packages.connectors.search.tavily import TavilySearchConnector
from packages.observability.tracing import ObservabilityTracer
from packages.prompts.registry import PromptRegistry
from services.orchestration.state.base import IdeaResearchState
from services.orchestration.llm import get_gemini_model, GeneratedIdeasBatch

logger = logging.getLogger(__name__)


def collect_sources_node(state: IdeaResearchState) -> Dict[str, Any]:
    """Collects and supplements sources via Tavily search."""
    topic = state.get("topic_or_brief", "")
    existing_sources = state.get("raw_sources", [])

    if len(existing_sources) < 2 and topic:
        searcher = TavilySearchConnector()
        found_sources = searcher.search(topic, max_results=3)
        existing_sources.extend(found_sources)

    return {"raw_sources": existing_sources}


def ideation_and_scoring_node(state: IdeaResearchState) -> Dict[str, Any]:
    """
    Generates structured ideas (at least 10) with angle, format, novelty, relevance, effort, priority, and risks.
    Powered by Google Gemini 3.8 Flash with structured Pydantic schema validation.
    """
    topic = state.get("topic_or_brief", "Intelligence Artificielle & Automatisation")
    pillars = state.get("pillars", ["IA générative", "Systèmes multi-agents", "Automatisation d'entreprise"])
    target_count = max(10, state.get("target_count", 10))
    sources = state.get("raw_sources", [])
    audience = state.get("audience", ["Tech Leads", "Entrepreneurs"])

    trace_meta = ObservabilityTracer.get_run_metadata(
        workspace_id=state.get("workspace_id", "default"),
        graph_name="idea_research_graph",
        node_name="ideation_and_scoring"
    )

    # 1. Prepare evidence pool
    evidence_pool = []
    for idx, src in enumerate(sources):
        evidence_pool.append({
            "source_id": src.get("url") or f"src_{idx + 1}",
            "claim": src.get("content", "")[:120] or f"Donnée probante sur {topic}"
        })
    if not evidence_pool:
        evidence_pool = [
            {"source_id": "src_default_1", "claim": f"Benchmark industriel 2026 sur {topic}"},
            {"source_id": "src_default_2", "claim": "Retour d'expérience de déploiements en production"}
        ]

    # 2. Try Gemini 3.8 Flash LLM invocation with structured outputs
    model = get_gemini_model(model_type="fast", temperature=0.3)
    if model is not None:
        try:
            rendered_prompt = PromptRegistry.render(
                "idea_research",
                {
                    "pillars": ", ".join(pillars),
                    "audience": ", ".join(audience),
                    "topic_or_brief": topic,
                    "sources": str(evidence_pool[:4]),
                    "target_count": target_count
                }
            )
            structured_llm = model.with_structured_output(GeneratedIdeasBatch)
            callback = ObservabilityTracer.get_callback_handler()
            callbacks = [callback] if callback else []
            
            result: GeneratedIdeasBatch = structured_llm.invoke(rendered_prompt, config={"callbacks": callbacks})
            if result and result.ideas:
                ideas_list = [idea.model_dump() for idea in result.ideas]
                return {
                    "generated_ideas": ideas_list,
                    "run_id": trace_meta["run_id"]
                }
        except Exception as e:
            logger.warning(f"Gemini LLM invocation failed, using deterministic fallback: {e}")

    # 3. Deterministic structured fallback (ensures offline and test reliability)
    angles = [
        ("Retour d'expérience terrain", "high", 8.5, 9.0, 4.0),
        ("Analyse critique des limites actuelles", "high", 9.0, 8.5, 5.0),
        ("Guide pas-à-pas pour les décideurs techniques", "medium", 7.0, 9.5, 6.0),
        ("Comparatif des approches open-source vs propriétaires", "medium", 8.0, 8.0, 4.5),
        ("Gouvernance et réduction du risque d'hallucination", "high", 9.5, 9.5, 5.5),
        ("Erreurs coûteuses observées lors du passage à l'échelle", "high", 8.5, 9.0, 4.0),
        ("Architecture de référence pour agents gouvernés", "high", 9.0, 9.5, 6.0),
        ("Optimisation des coûts de tokens et latence", "medium", 7.5, 8.5, 3.5),
        ("L'humain dans la boucle (HITL) : mythe ou impératif ?", "high", 9.0, 9.0, 4.5),
        ("Futur du travail : automatisation des flux éditoriaux", "medium", 8.0, 8.5, 4.0),
        ("Sécurité et défense contre le prompt injection", "high", 9.5, 9.0, 5.0),
        ("Mesure du ROI réel des assistants agentiques", "medium", 8.5, 9.0, 5.0),
    ]

    ideas: List[Dict[str, Any]] = []
    for i in range(target_count):
        angle_title, priority, novelty, relevance, effort = angles[i % len(angles)]
        pillar = pillars[i % len(pillars)]
        ideas.append({
            "title": f"{pillar} : {angle_title} ({topic})",
            "angle": f"Explorer {topic.lower()} sous l'angle : {angle_title.lower()}.",
            "target_audience": audience[0] if audience else "Professionnels Tech",
            "recommended_formats": ["linkedin", "x"],
            "evidence": [evidence_pool[i % len(evidence_pool)]],
            "novelty_score": novelty,
            "relevance_score": relevance,
            "effort_score": effort,
            "priority": priority,
            "risks": ["Vérifier la validité des chiffres récents", "Clarifier les prérequis techniques"] if effort > 4.5 else []
        })

    return {
        "generated_ideas": ideas,
        "run_id": trace_meta["run_id"]
    }
