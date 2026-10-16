from typing import Dict, Any, List
import logging
import re
from packages.observability.tracing import ObservabilityTracer
from packages.prompts.registry import PromptRegistry
from packages.cache.factory import get_llm_cache, compute_cache_key
from packages.tools.web_search import WebSearchTool
from services.orchestration.state.base import IdeaResearchState
from services.orchestration.structured_output import invoke_structured_output
from services.orchestration.llm import resolve_and_get_llm, GeneratedIdeasBatch

logger = logging.getLogger(__name__)


def collect_sources_node(state: IdeaResearchState) -> Dict[str, Any]:
    """
    Collects and grounds research sources using verified workspace signals or WebSearchTool.
    Never fabricates sources if web queries fail.
    """
    topic = state.get("topic_or_brief", "")
    existing_sources = state.get("raw_sources", [])
    workspace_id = state.get("workspace_id", "default")

    if len(existing_sources) < 2 and topic:
        try:
            searcher = WebSearchTool()
            search_res = searcher.search(query=topic, max_results=3, workspace_id=workspace_id)
            for item in search_res.results:
                existing_sources.append({
                    "url": item.url,
                    "content": item.snippet or item.title,
                    "title": item.title,
                })
        except Exception as e:
            logger.warning(f"Web search collection failed for topic '{topic}': {e}")

    return {"raw_sources": existing_sources}


def _clean_title(title: str, pillars: List[str]) -> str:
    """Strips any category/pillar prefixes (e.g. 'IA générative : ...') from idea titles."""
    clean = title.strip()
    for p in pillars:
        prefix_pattern = re.compile(rf"^{re.escape(p)}\s*:\s*", re.IGNORECASE)
        clean = prefix_pattern.sub("", clean).strip()
    return clean


def _normalize_score_100(val: Any, default: float = 50.0) -> float:
    """Normalizes score to a strict 0.0 - 100.0 scale."""
    try:
        num = float(val)
    except (TypeError, ValueError):
        return default
    # If score is on 0-10 scale (<= 10.0 and positive), multiply by 10
    if 0.0 < num <= 10.0:
        num = num * 10.0
    return round(min(100.0, max(0.0, num)), 1)


def ideation_and_scoring_node(state: IdeaResearchState) -> Dict[str, Any]:
    """
    Generates structured ideas strictly grounded on monitoring signals and sources.
    - No category prefixes in titles.
    - Explicit 0 to 100 scoring (Novelty, Relevance, Effort, Total).
    - Backed by LLM cache and multi-provider resolver (NVIDIA GLM-5.3-flash / Gemini).
    """
    topic = state.get("topic_or_brief", "Agents IA et automatisation en entreprise")
    pillars = state.get("pillars", ["IA générative", "Systèmes multi-agents", "Automatisation"])
    target_count = max(1, min(10, int(state.get("target_count") or 5)))
    sources = state.get("raw_sources", [])
    audience = state.get("audience", ["Tech Leads", "DSI", "Architectes Logiciels"])
    workspace_id = state.get("workspace_id", "default")

    trace_meta = ObservabilityTracer.get_run_metadata(
        workspace_id=workspace_id,
        graph_name="idea_research_graph",
        node_name="ideation_and_scoring"
    )

    # 1. Check deterministic LLM cache
    cache = get_llm_cache()
    cache_payload = {
        "workspace_id": workspace_id,
        "topic": topic.strip().lower(),
        "pillars": sorted([p.strip().lower() for p in pillars]),
        "audience": sorted([a.strip().lower() for a in audience]),
        "target_count": target_count
    }
    cache_key = compute_cache_key("idea_research", cache_payload)
    cached_result = cache.get(cache_key)
    if cached_result is not None:
        logger.info(f"LLM Cache Hit for topic '{topic}' (key: {cache_key})")
        ObservabilityTracer.tag_trace(trace_meta["run_id"], ["cache_hit"])
        res_data = dict(cached_result)
        res_data["run_id"] = trace_meta["run_id"]
        res_data["cached"] = True
        return res_data


    # 2. Build verified evidence pool from signals / sources (FND-02)
    evidence_pool = []
    for idx, src in enumerate(sources):
        src_url = src.get("url") or f"src_{idx + 1}"
        claim_text = src.get("content") or src.get("title") or f"Signal vérifié sur {topic}"
        evidence_pool.append({
            "source_id": src_url,
            "claim": claim_text[:140],
        })

    # Strict grounding check: NEVER fabricate fake default sources (FND-02)
    if not evidence_pool:
        logger.info(f"No grounded evidence available for topic '{topic}'. Returning NO_DATA.")
        no_data_res = {
            "status": "NO_DATA",
            "reason": "Aucun signal ou source exploitable trouvé pour étayer la recherche d'idées.",
            "generated_ideas": [],
            "run_id": trace_meta["run_id"],
            "resolved_llm": None,
        }
        cache.set(cache_key, no_data_res)
        return no_data_res

    # 3. Resolve LLM configuration (NVIDIA GLM-5.3-flash default, no silent fallback - FND-08)
    frozen_llm = state.get("resolved_llm")
    if isinstance(frozen_llm, dict):
        run_override = {
            "provider_id": frozen_llm.get("provider_id"),
            "model_id": frozen_llm.get("model_id"),
            "temperature": frozen_llm.get("temperature", 0.3),
        }
        model, resolved_ctx = resolve_and_get_llm(
            task_name="ideation",
            workspace_id=workspace_id,
            run_override=run_override,
            temperature=0.3,
            allow_none_if_unconfigured=True
        )
    else:
        raw_ov = state.get("llm_override")
        override_dict = raw_ov if isinstance(raw_ov, dict) else None
        try:
            model, resolved_ctx = resolve_and_get_llm(
                task_name="ideation",
                workspace_id=workspace_id,
                run_override=override_dict,
                temperature=0.3,
                allow_none_if_unconfigured=True
            )
        except Exception as err:
            logger.warning(f"LLM resolution failed for ideation node: {err}. Falling back to deterministic mode.")
            model, resolved_ctx = None, None

    # Isolated demo mode handler (strictly segregated and labeled)
    if state.get("demo") is True:
        return _build_demo_ideas(
            topic=topic,
            pillars=pillars,
            audience=audience,
            evidence_pool=evidence_pool,
            target_count=target_count,
            trace_meta=trace_meta,
            resolved_ctx=resolved_ctx,
            frozen_llm=frozen_llm,
            cache=cache,
            cache_key=cache_key
        )


    if model is None:
        logger.warning(f"No configured LLM provider available for workspace '{workspace_id}'. Using deterministic fallback for test/offline environment.")
        return _build_demo_ideas(
            topic=topic,
            pillars=pillars,
            audience=audience,
            evidence_pool=evidence_pool,
            target_count=target_count,
            trace_meta=trace_meta,
            resolved_ctx=resolved_ctx,
            frozen_llm=frozen_llm,
            cache=cache,
            cache_key=cache_key
        )


    try:
        rendered_prompt = PromptRegistry.render(
            "idea_research",
            {
                "pillars": ", ".join(pillars),
                "audience": ", ".join(audience),
                "topic_or_brief": topic,
                "sources": str(evidence_pool[:6]),
                "target_count": target_count
            }
        )
        callback = ObservabilityTracer.get_callback_handler()
        callbacks = [callback] if callback else []

        result = invoke_structured_output(
            model=model,
            schema_cls=GeneratedIdeasBatch,
            prompt=rendered_prompt,
            callbacks=callbacks
        )
        if result and result.ideas:
            ideas_list = []
            for item in result.ideas:
                dump = item.model_dump()
                # Strip any accidental category prefix
                dump["title"] = _clean_title(dump["title"], pillars)
                # Normalize scores to 0-100 scale
                dump["novelty_score"] = _normalize_score_100(dump["novelty_score"])
                dump["relevance_score"] = _normalize_score_100(dump["relevance_score"])
                dump["effort_score"] = _normalize_score_100(dump["effort_score"])
                ideas_list.append(dump)

            res = {
                "status": "SUCCESS",
                "generated_ideas": ideas_list,
                "run_id": trace_meta["run_id"],
                "resolved_llm": resolved_ctx.to_dict() if resolved_ctx else (frozen_llm if isinstance(frozen_llm, dict) else None)
            }
            cache.set(cache_key, res)
            ObservabilityTracer.tag_trace(trace_meta["run_id"], ["cache_miss"])
            return res
        else:
            logger.warning("Structured output returned no ideas. Falling back to deterministic demo ideas for resilience.")
            return _build_demo_ideas(
                topic=topic,
                pillars=pillars,
                audience=audience,
                evidence_pool=evidence_pool,
                target_count=target_count,
                trace_meta=trace_meta,
                resolved_ctx=resolved_ctx,
                frozen_llm=frozen_llm,
                cache=cache,
                cache_key=cache_key
            )
    except Exception as e:
        logger.warning(f"LLM ideation invocation failed: {e}. Falling back to deterministic demo ideas for resilience.")
        return _build_demo_ideas(
            topic=topic,
            pillars=pillars,
            audience=audience,
            evidence_pool=evidence_pool,
            target_count=target_count,
            trace_meta=trace_meta,
            resolved_ctx=resolved_ctx,
            frozen_llm=frozen_llm,
            cache=cache,
            cache_key=cache_key
        )



def _build_demo_ideas(
    topic: str,
    pillars: List[str],
    audience: List[str],
    evidence_pool: List[Dict[str, Any]],
    target_count: int,
    trace_meta: Dict[str, Any],
    resolved_ctx: Any,
    frozen_llm: Any,
    cache: Any,
    cache_key: str,
) -> Dict[str, Any]:
    """Isolated, clearly labeled synthetic demo fixtures for offline demonstration and tests."""
    demo_angles = [
        ("Gouvernance et réduction du risque d'hallucination en production", "high", 95.0, 92.0, 50.0),
        ("Architecture de référence pour agents gouvernés en environnement critique", "high", 90.0, 95.0, 55.0),
        ("Audit de conformité EU AI Act : Ce que les DSI doivent anticiper", "high", 88.0, 94.0, 40.0),
    ]
    ideas: List[Dict[str, Any]] = []
    count = min(target_count, len(demo_angles))
    for i in range(count):
        angle_title, priority, novelty, relevance, effort = demo_angles[i % len(demo_angles)]
        title = f"{angle_title} ({topic})"
        ideas.append({
            "title": title,
            "angle": f"Analyser les enjeux concrets de {topic.lower()} à travers l'axe : {angle_title.lower()}.",
            "target_audience": audience[0] if audience else "Professionnels Tech",
            "recommended_formats": ["linkedin", "x"],
            "evidence": [evidence_pool[i % len(evidence_pool)]] if evidence_pool else [],
            "novelty_score": novelty,
            "relevance_score": relevance,
            "effort_score": effort,
            "priority": priority,
            "risks": ["Vérifier la validité des chiffres récents"] if effort > 45.0 else [],
            "is_synthetic": True,
            "is_demo": True,
        })
    res = {
        "status": "DEMO",
        "generated_ideas": ideas,
        "run_id": trace_meta["run_id"],
        "resolved_llm": resolved_ctx.to_dict() if resolved_ctx else frozen_llm,
    }
    cache.set(cache_key, res)
    return res

