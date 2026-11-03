import os
import logging
import re
from typing import Dict, Any, List, Optional, Literal
from pydantic import BaseModel, Field
from packages.security.env import is_production
from packages.observability.tracing import ObservabilityTracer
from packages.prompts.registry import PromptRegistry
from packages.cache.factory import (
    get_llm_cache,
    compute_cache_key,  # noqa: F401
    build_llm_cache_key,
    is_cacheable_llm_output,
)
from packages.tools.web_search import WebSearchTool
from packages.tools.registry import AgentToolRegistry
from services.orchestration.state.base import IdeaResearchState
from services.orchestration.structured_output import invoke_structured_output
from services.orchestration.llm import resolve_and_get_llm, GeneratedIdeasBatch
from packages.resilience.circuit_breaker import resolve_cycle_budget, BudgetExceededException, CycleBudget

logger = logging.getLogger(__name__)


class EnrichmentDecision(BaseModel):
    sufficient_evidence: bool = Field(
        description="True if existing sources already contain enough concrete facts to ground the requested ideas."
    )
    missing_aspects: List[str] = Field(
        default_factory=list,
        description="Specific factual gaps or missing perspectives that require documentary enrichment.",
    )
    recommended_action: Literal["proceed", "search_web", "browse_url"] = Field(
        default="proceed",
        description="Next bounded action: 'proceed' to ideation, 'search_web' for missing facts, or 'browse_url' to extract full page text.",
    )
    query_or_url: Optional[str] = Field(
        default=None,
        description="Targeted search query (for 'search_web') or public URL (for 'browse_url').",
    )
    rationale: str = Field(
        default="Preuves suffisantes.",
        description="Concise justification for the decision.",
    )


def evidence_enrichment_node(state: IdeaResearchState) -> Dict[str, Any]:
    """
    Bounded agentic evidence enrichment node (Section 8.2 & D-04).
    Evaluates whether the current evidence pool is sufficient and, if needed,
    executes at most 2 governed tool calls via AgentToolRegistry ('web_search' or 'safe_browse').
    """
    budget = resolve_cycle_budget(state)
    budget.check_budget()

    workspace_id = str(state.get("workspace_id") or "default")
    topic = str(state.get("topic_or_brief") or "").strip()
    sources = list(state.get("raw_sources") or [])
    enrichment_count = int(state.get("enrichment_count") or 0)
    enrichment_history = list(state.get("enrichment_history") or [])
    max_calls = 2

    if enrichment_count >= max_calls:
        return {
            "raw_sources": sources,
            "enrichment_count": enrichment_count,
            "enrichment_history": enrichment_history,
            "cycle_budget": budget,
        }

    # Evaluate if enrichment should be triggered:
    # Either explicitly enabled (`enable_agentic_enrichment=True`) or sources have sparse content (< 40 chars)
    enable_agentic = bool(state.get("enable_agentic_enrichment", False))
    sparse_sources = [
        s for s in sources
        if len(str(s.get("content") or "").strip()) < 40 and str(s.get("url") or "").startswith("http")
    ]
    if not enable_agentic and sources and not sparse_sources:
        return {
            "raw_sources": sources,
            "enrichment_count": enrichment_count,
            "enrichment_history": enrichment_history,
            "cycle_budget": budget,
        }

    registry = AgentToolRegistry(
        workspace_id=workspace_id,
        caller_role="ServiceAgent",
        max_total_calls=max(0, max_calls - enrichment_count),
    )

    # Attempt structured LLM decision when enable_agentic is True, else deterministic decision
    decision: Optional[EnrichmentDecision] = None
    if enable_agentic:
        try:
            model, _ = resolve_and_get_llm(
                task_name="research_enrichment",
                workspace_id=workspace_id,
                temperature=0.1,
                allow_none_if_unconfigured=True,
            )
            if model is not None:
                src_summary = "\n".join(
                    f"- {s.get('title', 'Source')} ({s.get('url', 'N/A')}): {str(s.get('content', ''))[:200]}"
                    for s in sources[:5]
                )
                prompt = (
                    f"Sujet de recherche : {topic}\n"
                    f"Sources actuelles ({len(sources)}) :\n{src_summary or 'Aucune source'}\n\n"
                    "Évalue si ces sources contiennent suffisamment de faits vérifiables ou si une action "
                    "documentaire bornée ('search_web' ou 'browse_url') est nécessaire."
                )
                decision = invoke_structured_output(
                    model=model,
                    schema_cls=EnrichmentDecision,
                    prompt=prompt,
                )
                budget.add_tokens(250)
        except Exception as exc:
            logger.warning(f"EnrichmentDecision LLM evaluation failed, falling back to deterministic check: {exc}")

    if decision is None:
        if sparse_sources:
            target_url = str(sparse_sources[0].get("url"))
            decision = EnrichmentDecision(
                sufficient_evidence=False,
                missing_aspects=["Contenu intégral manquant sur la source primaire"],
                recommended_action="browse_url",
                query_or_url=target_url,
                rationale="Source existante trop courte (< 40 caractères), extraction de la page requise.",
            )
        elif len(sources) < 2 and topic:
            decision = EnrichmentDecision(
                sufficient_evidence=False,
                missing_aspects=["Couverture documentaire insuffisante (< 2 sources)"],
                recommended_action="search_web",
                query_or_url=topic,
                rationale="Moins de 2 sources qualifiées pour le sujet demandé.",
            )
        else:
            decision = EnrichmentDecision(
                sufficient_evidence=True,
                missing_aspects=[],
                recommended_action="proceed",
                query_or_url=None,
                rationale="Corpus documentaire suffisant pour l'idéation.",
            )

    if decision.sufficient_evidence or decision.recommended_action == "proceed" or not decision.query_or_url:
        enrichment_history.append(
            {
                "step": enrichment_count + 1,
                "action": "proceed",
                "rationale": decision.rationale,
            }
        )
        return {
            "raw_sources": sources,
            "enrichment_count": enrichment_count,
            "enrichment_history": enrichment_history,
            "cycle_budget": budget,
        }

    # Execute bounded tool call via AgentToolRegistry
    if decision.recommended_action == "browse_url":
        tool_res = registry.execute("safe_browse", {"url": decision.query_or_url, "max_chars": 3000})
        enrichment_count += 1
        if tool_res.status == "SUCCESS" and isinstance(tool_res.data, dict):
            browsed = tool_res.data
            updated = False
            for s in sources:
                if s.get("url") == decision.query_or_url:
                    s["content"] = browsed.get("content") or s.get("content")
                    s["title"] = browsed.get("title") or s.get("title")
                    updated = True
                    break
            if not updated:
                sources.append(browsed)
    elif decision.recommended_action == "search_web":
        tool_res = registry.execute("web_search", {"query": decision.query_or_url, "limit": 2})
        enrichment_count += 1
        if tool_res.status == "SUCCESS" and isinstance(tool_res.data, list):
            existing_urls = {s.get("url") for s in sources}
            for item in tool_res.data:
                if isinstance(item, dict) and item.get("url") not in existing_urls:
                    sources.append(item)
                    existing_urls.add(item.get("url"))
    else:
        tool_res = None

    enrichment_history.append(
        {
            "step": enrichment_count,
            "action": decision.recommended_action,
            "query_or_url": decision.query_or_url,
            "rationale": decision.rationale,
            "tool_status": tool_res.status if tool_res else "SKIPPED",
            "tool_error": tool_res.error if tool_res else None,
        }
    )

    return {
        "raw_sources": sources,
        "enrichment_count": enrichment_count,
        "enrichment_history": enrichment_history,
        "cycle_budget": budget,
    }


def collect_sources_node(state: IdeaResearchState) -> Dict[str, Any]:
    """
    Collects and grounds research sources using verified workspace signals or WebSearchTool.
    Never fabricates sources if web queries fail.
    """
    budget = resolve_cycle_budget(state)
    budget.check_budget()

    topic = state.get("topic_or_brief", "")
    existing_sources = list(state.get("raw_sources", []))
    workspace_id = state.get("workspace_id", "default")

    if len(existing_sources) < 2 and topic and not state.get("enable_agentic_enrichment"):
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

    return {"raw_sources": existing_sources, "cycle_budget": budget}


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

    # Enforce FinOps cycle budget (N3)
    budget = resolve_cycle_budget(state)
    budget.check_budget()

    # 1. Build verified evidence pool from signals / sources (FND-02)
    evidence_pool = []
    for idx, src in enumerate(sources):
        src_url = src.get("url") or f"src_{idx + 1}"
        claim_text = src.get("content") or src.get("title") or f"Signal vérifié sur {topic}"
        evidence_pool.append({
            "source_id": src_url,
            "claim": claim_text[:280],
        })

    # Strict grounding check: NEVER fabricate fake default sources and NEVER cache NO_DATA (FND-02)
    if not evidence_pool:
        logger.info(f"No grounded evidence available for topic '{topic}'. Returning NO_DATA.")
        return {
            "status": "NO_DATA",
            "reason": "Aucun signal ou source exploitable trouvé pour étayer la recherche d'idées.",
            "generated_ideas": [],
            "run_id": trace_meta["run_id"],
            "resolved_llm": None,
            "cycle_budget": budget,
            "cached": False,
        }

    # 2. Resolve LLM configuration (NVIDIA GLM-5 / Gemini, no silent cache pollution)
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

    # Isolated demo mode handler (strictly segregated, labeled, and NEVER cached)
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
            budget=budget,
        )

    provider_id = (
        resolved_ctx.provider_id
        if resolved_ctx
        else (frozen_llm.get("provider_id") if isinstance(frozen_llm, dict) else "unconfigured")
    )
    model_id = (
        resolved_ctx.model_id
        if resolved_ctx
        else (frozen_llm.get("model_id") if isinstance(frozen_llm, dict) else "unconfigured")
    )

    # 3. Check deterministic, versioned, tenant-scoped LLM cache
    cache = get_llm_cache()
    cache_key = build_llm_cache_key(
        node="idea_research",
        workspace_id=workspace_id,
        provider_id=str(provider_id or "unconfigured"),
        model_id=str(model_id or "unconfigured"),
        prompt_version="idea_research_v2",
        schema_version="GeneratedIdeasBatch_v2",
        params={
            "topic": topic.strip().lower(),
            "pillars": sorted([p.strip().lower() for p in pillars]),
            "audience": sorted([a.strip().lower() for a in audience]),
            "target_count": target_count,
        },
        sources_fingerprint=evidence_pool[:6],
    )
    cached_result = cache.get(cache_key)
    if cached_result is not None and is_cacheable_llm_output(cached_result):
        logger.info(f"LLM Cache Hit for topic '{topic}' (key: {cache_key})")
        ObservabilityTracer.tag_trace(trace_meta["run_id"], ["cache_hit"])
        res_data = dict(cached_result)
        res_data["run_id"] = trace_meta["run_id"]
        res_data["cached"] = True
        res_data["cycle_budget"] = budget
        tokens_delivered = max(100, len(res_data.get("generated_ideas", [])) * 50)
        budget.add_tokens(tokens_delivered)
        return res_data

    is_test_env = os.environ.get("CONTENTOPS_TEST_MODE") == "1" or "PYTEST_CURRENT_TEST" in os.environ
    is_demo_mode = bool(state.get("demo")) or is_test_env or not is_production()
    if model is None:
        if is_demo_mode:
            logger.info("Demo / test mode active: using clearly labeled synthetic demo ideas (never cached).")
            return _build_demo_ideas(
                topic=topic,
                pillars=pillars,
                audience=audience,
                evidence_pool=evidence_pool,
                target_count=target_count,
                trace_meta=trace_meta,
                resolved_ctx=resolved_ctx,
                frozen_llm=frozen_llm,
                budget=budget,
            )
        logger.error(f"No configured LLM provider available for workspace '{workspace_id}' and demo mode is not enabled.")
        return {
            "status": "LLM_PROVIDERS_DOWN",
            "error_code": "LLM_PROVIDERS_DOWN",
            "reason": "Aucun fournisseur LLM actif n'est disponible pour générer les idées.",
            "generated_ideas": [],
            "run_id": trace_meta["run_id"],
            "resolved_llm": None,
            "cycle_budget": budget,
            "cached": False,
        }

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

            tokens_used = max(300, len(ideas_list) * 200)
            budget.add_tokens(tokens_used)

            res = {
                "status": "SUCCESS",
                "generated_ideas": ideas_list,
                "run_id": trace_meta["run_id"],
                "resolved_llm": resolved_ctx.to_dict() if resolved_ctx else (frozen_llm if isinstance(frozen_llm, dict) else None),
                "cycle_budget": budget,
                "cached": False,
            }
            cache.set(cache_key, {k: v for k, v in res.items() if k != "cycle_budget"})
            ObservabilityTracer.tag_trace(trace_meta["run_id"], ["cache_miss"])
            return res
        else:
            if is_demo_mode:
                logger.warning("Structured output returned no ideas. Demo mode active: using demo ideas (never cached).")
                return _build_demo_ideas(
                    topic=topic,
                    pillars=pillars,
                    audience=audience,
                    evidence_pool=evidence_pool,
                    target_count=target_count,
                    trace_meta=trace_meta,
                    resolved_ctx=resolved_ctx,
                    frozen_llm=frozen_llm,
                    budget=budget,
                )
            return {
                "status": "LLM_PROVIDERS_DOWN",
                "error_code": "LLM_PROVIDERS_DOWN",
                "reason": "Le fournisseur LLM n'a retourné aucune idée structurée valide.",
                "generated_ideas": [],
                "run_id": trace_meta["run_id"],
                "resolved_llm": resolved_ctx.to_dict() if resolved_ctx else None,
                "cycle_budget": budget,
                "cached": False,
            }
    except BudgetExceededException:
        raise
    except Exception as e:
        if is_demo_mode:
            logger.warning(f"LLM ideation invocation failed: {e}. Demo mode active: using demo ideas (never cached).")
            return _build_demo_ideas(
                topic=topic,
                pillars=pillars,
                audience=audience,
                evidence_pool=evidence_pool,
                target_count=target_count,
                trace_meta=trace_meta,
                resolved_ctx=resolved_ctx,
                frozen_llm=frozen_llm,
                budget=budget,
            )
        logger.error(f"LLM ideation invocation failed: {e}")
        return {
            "status": "LLM_PROVIDERS_DOWN",
            "error_code": "LLM_PROVIDERS_DOWN",
            "reason": f"Échec des fournisseurs LLM lors de l'idéation : {e}",
            "generated_ideas": [],
            "run_id": trace_meta["run_id"],
            "resolved_llm": resolved_ctx.to_dict() if resolved_ctx else None,
            "cycle_budget": budget,
            "cached": False,
        }


def _build_demo_ideas(
    topic: str,
    pillars: List[str],
    audience: List[str],
    evidence_pool: List[Dict[str, Any]],
    target_count: int,
    trace_meta: Dict[str, Any],
    resolved_ctx: Any,
    frozen_llm: Any,
    cache: Any = None,
    cache_key: str = "",
    budget: Optional[CycleBudget] = None,
) -> Dict[str, Any]:
    """Isolated, clearly labeled synthetic demo fixtures for offline demonstration and tests. Never cached."""
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

    tokens_used = max(200, len(ideas) * 150)
    if budget is not None:
        budget.add_tokens(tokens_used)

    return {
        "status": "DEMO",
        "is_demo": True,
        "generated_ideas": ideas,
        "run_id": trace_meta["run_id"],
        "resolved_llm": resolved_ctx.to_dict() if resolved_ctx else frozen_llm,
        "cycle_budget": budget,
        "cached": False,
    }

