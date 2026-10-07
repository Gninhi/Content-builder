from fastapi import APIRouter, Depends, Body, HTTPException
from datetime import datetime, timezone
from typing import cast, Dict, Any
from langchain_core.runnables import RunnableConfig
from packages.contracts.schemas import StrategyInsightsResponse, StrategyInsight
from services.orchestration.graphs.strategy_insights import graph as strategy_insights_graph
from packages.observability.tracing import ObservabilityTracer
from infra.db.models import (
    MetricSnapshotModel,
    PublishedPostModel,
    PublicationJobModel,
    ContentVariantModel,
    ContentPackageModel,
    ContentBriefModel
)
from infra.db.repository import ContentOpsRepository
from apps.api.dependencies import get_repository, UserContext, require_roles

router = APIRouter(tags=["Strategy & Insights"])


@router.post("/v1/strategy/insights", response_model=StrategyInsightsResponse)
def generate_strategy_insights(
    workspace_id: str = Body("ws_default", embed=True),
    repo: ContentOpsRepository = Depends(get_repository),
    user: UserContext = Depends(require_roles("Owner", "Editor"))
):
    if workspace_id and workspace_id != user.workspace_id:
        raise HTTPException(status_code=403, detail="Cannot generate strategy insights for another workspace.")
    ws_id = user.workspace_id
    brand_profile = repo.get_latest_brand_profile(ws_id)
    pillars = brand_profile.pillars if brand_profile else ["IA générative", "Systèmes multi-agents"]

    # Gather recent snapshots strictly isolated by workspace
    snapshots_models = (
        repo.db.query(MetricSnapshotModel)
        .join(PublishedPostModel, MetricSnapshotModel.post_id == PublishedPostModel.id)
        .join(PublicationJobModel, PublishedPostModel.job_id == PublicationJobModel.id)
        .join(ContentVariantModel, PublicationJobModel.variant_id == ContentVariantModel.id)
        .join(ContentPackageModel, ContentVariantModel.package_id == ContentPackageModel.id)
        .join(ContentBriefModel, ContentPackageModel.brief_id == ContentBriefModel.id)
        .filter(ContentBriefModel.workspace_id == ws_id)
        .all()
    )
    snapshots = [
        {"impressions": s.impressions, "engagements": s.engagements}
        for s in snapshots_models
    ]

    initial_state: Dict[str, Any] = {
        "workspace_id": workspace_id,
        "pillars": pillars,
        "metric_snapshots": snapshots,
        "hypotheses": [],
        "recommendations": [],
        "confidence_levels": {},
        "status": "PENDING"
    }

    callback = ObservabilityTracer.get_callback_handler()
    config: RunnableConfig = cast(RunnableConfig, {"callbacks": [callback]} if callback else {})
    result = cast(Dict[str, Any], strategy_insights_graph.invoke(cast(Any, initial_state), config=config))


    insights = [
        StrategyInsight(
            pillar=h.get("pillar", "Général"),
            fact=h.get("fact", "Observation préliminaire"),
            hypothesis=h.get("hypothesis", "Hypothèse éditoriale"),
            confidence_level=h.get("confidence_level", 0.8),
            recommended_action=h.get("recommended_action", "Maintenir le cap")
        )
        for h in result.get("hypotheses", [])
    ]

    return StrategyInsightsResponse(
        workspace_id=workspace_id,
        generated_at=datetime.now(timezone.utc),
        insights=insights
    )
