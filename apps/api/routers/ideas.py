from typing import cast, Dict, Any, Optional
from langchain_core.runnables import RunnableConfig
from fastapi import APIRouter, Depends, HTTPException
from packages.contracts.schemas import (
    IdeaResearchRequest,
    IdeaResearchResponse,
    IdeaItem,
    EvidenceItem,
)
from services.orchestration.graphs.idea_research import graph as idea_research_graph
from packages.observability.tracing import ObservabilityTracer
from packages.prompts.registry import PROMPTS_V1
from apps.api.dependencies import get_repository, UserContext, require_roles
from infra.db.repository import ContentOpsRepository

router = APIRouter(tags=["Ideation & Research"])


@router.post("/v1/ideas/research", response_model=IdeaResearchResponse)
def research_ideas(
    req: IdeaResearchRequest,
    repo: ContentOpsRepository = Depends(get_repository),
    user: UserContext = Depends(require_roles("Owner", "Editor", "ServiceAgent"))
):
    if req.workspace_id and req.workspace_id != user.workspace_id:
        raise HTTPException(status_code=403, detail="Cannot research ideas for another workspace.")
    ws_id = user.workspace_id
    brand_profile = repo.get_latest_brand_profile(ws_id)
    pillars = req.pillars or (brand_profile.pillars if brand_profile else ["IA générative", "Automatisation"])
    audience = req.audience or (brand_profile.audience if brand_profile else ["Tech Leaders"])

    # 1. Retrieve qualified monitoring signals and content sources in workspace
    raw_sources = []

    # Priority 1: Verified Veille Signals
    signals = repo.list_signals(ws_id, status="QUALIFIED")
    for sig in signals:
        facts = list(sig.facts) if sig.facts else []
        content_str = " ".join([str(f.get("fact", "")) for f in facts if isinstance(f, dict)])
        if not content_str:
            content_str = f"{sig.summary} {sig.executive_takeaway}"
        raw_sources.append({
            "url": str(sig.canonical_url) if sig.canonical_url else f"signal://{sig.id}",
            "content": content_str,
            "title": sig.title,
            "signal_id": sig.id
        })

    # Priority 2: Ingested Content Sources
    sources = repo.list_sources(ws_id)
    for s in sources:
        facts = list(s.extracted_facts) if s.extracted_facts else []
        content_str = " ".join([str(f.get("claim", "")) for f in facts if isinstance(f, dict)])
        raw_sources.append({
            "url": str(s.canonical_url) if s.canonical_url else "",
            "content": content_str,
            "title": s.canonical_url or "Source",
        })

    initial_state = {
        "workspace_id": ws_id,
        "topic_or_brief": req.topic_or_brief,
        "pillars": pillars,
        "audience": audience,
        "target_count": req.target_count,
        "raw_sources": raw_sources,
        "generated_ideas": [],
        "llm_override": req.llm_override,
        "run_id": "",
        "errors": []
    }

    # Run LangGraph idea_research workflow with Langfuse tracing
    callback = ObservabilityTracer.get_callback_handler()
    config: RunnableConfig = cast(RunnableConfig, {"callbacks": [callback]} if callback else {})
    result = cast(Dict[str, Any], idea_research_graph.invoke(cast(Any, initial_state), config=config))

    generated = result.get("generated_ideas", [])
    run_id = result.get("run_id", "run_local")

    # Persist generated ideas in DB with deduplication and signal grounding
    persisted_ideas = []
    for idx, idea in enumerate(generated):
        # Extract signal_id if present in evidence
        sig_id = idea.get("signal_id")
        if not sig_id and idea.get("evidence"):
            for ev in idea["evidence"]:
                if isinstance(ev, dict) and ev.get("source_id", "").startswith("signal://"):
                    sig_id = ev["source_id"].replace("signal://", "")
                    break

        pillar = pillars[idx % len(pillars)] if pillars else "Stratégie IA"

        saved = repo.save_idea(
            workspace_id=ws_id,
            title=idea["title"],
            angle=idea["angle"],
            pillar=pillar,
            audience=idea["target_audience"],
            evidence_refs=idea["evidence"],
            novelty_score=idea["novelty_score"],
            relevance_score=idea["relevance_score"],
            effort_score=idea["effort_score"],
            priority=idea["priority"],
            risks=idea["risks"],
            signal_id=sig_id
        )

        persisted_ideas.append(
            IdeaItem(
                id=saved.id,
                title=saved.title,
                angle=saved.angle,
                target_audience=saved.audience,
                recommended_formats=idea.get("recommended_formats", ["linkedin", "x"]),
                evidence=[EvidenceItem(**e) for e in idea["evidence"] if isinstance(e, dict) and "source_id" in e and "claim" in e],
                novelty_score=saved.novelty_score,
                relevance_score=saved.relevance_score,
                effort_score=saved.effort_score,
                total_score=saved.total_score,
                priority=saved.priority,
                risks=saved.risks,
                signal_id=saved.signal_id
            )
        )

    # Log agent run with true resolved execution metadata (PRD FR-10)
    prompt_version = PROMPTS_V1.get("idea_research", {}).get("version", "1.1.0")
    is_cached = bool(result.get("cached", False))
    resolved_llm_info = result.get("resolved_llm")

    if is_cached:
        cached_model = resolved_llm_info.get("model_id") if isinstance(resolved_llm_info, dict) else "memory"
        logged_model = f"cache:{cached_model}"
        logged_cost = 0.0
    elif isinstance(resolved_llm_info, dict):
        provider = resolved_llm_info.get("provider_id", "unknown")
        model_id = resolved_llm_info.get("model_id", "unknown")
        logged_model = f"{provider}/{model_id}"
        tokens = resolved_llm_info.get("total_tokens")
        logged_cost = float(tokens) * 0.000002 if tokens else 0.0
    elif result.get("status") == "FALLBACK":
        logged_model = "fallback:deterministic_demo"
        logged_cost = 0.0
    else:
        logged_model = "system:deterministic"
        logged_cost = 0.0

    repo.log_agent_run(
        workspace_id=ws_id,
        graph="idea_research_graph",
        node="ideate_and_score",
        trace_id=run_id,
        prompt_version=prompt_version,
        model=logged_model,
        cost=logged_cost
    )

    return IdeaResearchResponse(
        ideas=persisted_ideas,
        sources_used=[str(s["url"]) for s in raw_sources if s.get("url")],
        run_id=str(run_id)
    )


@router.get("/v1/ideas")
def list_ideas(
    workspace_id: Optional[str] = None,
    repo: ContentOpsRepository = Depends(get_repository),
    user: UserContext = Depends(require_roles("Owner", "Editor", "Viewer", "ServiceAgent"))
):
    if workspace_id and workspace_id != user.workspace_id:
        raise HTTPException(status_code=403, detail="Access to other workspace ideas is forbidden.")
    ideas = repo.list_ideas(user.workspace_id)
    return [
        {
            "id": i.id,
            "title": i.title,
            "angle": i.angle,
            "pillar": i.pillar,
            "audience": i.audience,
            "evidence_refs": i.evidence_refs,
            "total_score": i.total_score,
            "novelty_score": i.novelty_score,
            "relevance_score": i.relevance_score,
            "effort_score": i.effort_score,
            "priority": i.priority,
            "risks": i.risks,
            "status": i.status,
            "signal_id": i.signal_id
        }
        for i in ideas
    ]
