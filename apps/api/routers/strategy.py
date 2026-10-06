from fastapi import APIRouter, Depends, Body
from typing import Dict, Any
from datetime import datetime
from packages.contracts.schemas import StrategyInsightsResponse, StrategyInsight
from services.orchestration.graphs.strategy_insights import graph as strategy_insights_graph
from packages.observability.tracing import ObservabilityTracer
from infra.db.models import MetricSnapshotModel
from infra.db.repository import ContentOpsRepository
from apps.api.dependencies import get_repository, get_current_user, UserContext, require_roles

router = APIRouter(tags=["Strategy & Insights"])


@router.post("/v1/strategy/insights", response_model=StrategyInsightsResponse)
def generate_strategy_insights(
    workspace_id: str = Body("ws_default", embed=True),
    repo: ContentOpsRepository = Depends(get_repository),
    user: UserContext = Depends(require_roles("Owner", "Analyst"))
):
    brand_profile = repo.get_latest_brand_profile(workspace_id)
    pillars = brand_profile.pillars if brand_profile else ["IA générative", "Systèmes multi-agents"]

    # Gather recent snapshots
    snapshots_models = repo.db.query(MetricSnapshotModel).all()
    snapshots = [
        {"impressions": s.impressions, "engagements": s.engagements}
        for s in snapshots_models
    ]

    initial_state = {
        "workspace_id": workspace_id,
        "pillars": pillars,
        "metric_snapshots": snapshots,
        "hypotheses": [],
        "recommendations": [],
        "confidence_levels": {},
        "status": "PENDING"
    }

    callback = ObservabilityTracer.get_callback_handler()
    config = {"callbacks": [callback]} if callback else {}
    result = strategy_insights_graph.invoke(initial_state, config=config)

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
        generated_at=datetime.utcnow(),
        insights=insights
    )
