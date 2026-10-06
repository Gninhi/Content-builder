from fastapi import APIRouter, Depends, HTTPException
from typing import List
from packages.contracts.schemas import (
    IdeaResearchRequest,
    IdeaResearchResponse,
    IdeaItem,
    EvidenceItem,
)
from services.orchestration.graphs.idea_research import graph as idea_research_graph
from apps.api.dependencies import get_repository, get_current_user, UserContext, require_roles
from infra.db.repository import ContentOpsRepository

router = APIRouter(tags=["Ideation & Research"])


@router.post("/v1/ideas/research", response_model=IdeaResearchResponse)
def research_ideas(
    req: IdeaResearchRequest,
    repo: ContentOpsRepository = Depends(get_repository),
    user: UserContext = Depends(require_roles("Owner", "Editor", "ServiceAgent"))
):
    brand_profile = repo.get_latest_brand_profile(req.workspace_id)
    pillars = req.pillars or (brand_profile.pillars if brand_profile else ["IA générative", "Automatisation"])
    audience = brand_profile.audience if brand_profile else ["Tech Leaders"]

    # Retrieve existing sources in workspace
    sources = repo.list_sources(req.workspace_id)
    raw_sources = [
        {"url": s.canonical_url, "content": " ".join([f["claim"] for f in s.extracted_facts])}
        for s in sources
    ]

    initial_state = {
        "workspace_id": req.workspace_id,
        "topic_or_brief": req.topic_or_brief,
        "pillars": pillars,
        "audience": audience,
        "target_count": req.target_count,
        "raw_sources": raw_sources,
        "generated_ideas": [],
        "run_id": "",
        "errors": []
    }

    # Run LangGraph idea_research workflow
    result = idea_research_graph.invoke(initial_state)

    generated = result.get("generated_ideas", [])
    run_id = result.get("run_id", "run_local")

    # Persist generated ideas in DB
    persisted_ideas = []
    for idea in generated:
        model = repo.save_idea(
            workspace_id=req.workspace_id,
            title=idea["title"],
            angle=idea["angle"],
            pillar=idea["title"].split(":")[0].strip() if ":" in idea["title"] else "General",
            audience=idea["target_audience"],
            evidence_refs=idea["evidence"],
            novelty_score=idea["novelty_score"],
            relevance_score=idea["relevance_score"],
            effort_score=idea["effort_score"],
            priority=idea["priority"],
            risks=idea["risks"]
        )
        persisted_ideas.append(
            IdeaItem(
                title=idea["title"],
                angle=idea["angle"],
                target_audience=idea["target_audience"],
                recommended_formats=idea["recommended_formats"],
                evidence=[EvidenceItem(**e) for e in idea["evidence"]],
                novelty_score=idea["novelty_score"],
                relevance_score=idea["relevance_score"],
                effort_score=idea["effort_score"],
                priority=idea["priority"],
                risks=idea["risks"]
            )
        )

    # Log agent run for full auditability (PRD FR-10)
    repo.log_agent_run(
        workspace_id=req.workspace_id,
        graph="idea_research_graph",
        node="ideate_and_score",
        trace_id=run_id,
        prompt_version="1.0.0",
        model="deterministic-llm-orchestrator",
        cost=0.001
    )

    return IdeaResearchResponse(
        ideas=persisted_ideas,
        sources_used=[s.get("url") for s in raw_sources if s.get("url")],
        run_id=run_id
    )


@router.get("/v1/ideas")
def list_ideas(
    workspace_id: str = "ws_default",
    repo: ContentOpsRepository = Depends(get_repository)
):
    ideas = repo.list_ideas(workspace_id)
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
            "status": i.status
        }
        for i in ideas
    ]
