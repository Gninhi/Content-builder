from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, Any
from packages.contracts.schemas import MetricSnapshotCreate
from infra.db.repository import ContentOpsRepository
from infra.db.models import MetricSnapshotModel, PublishedPostModel
from apps.api.dependencies import get_repository, UserContext, require_roles

router = APIRouter(tags=["Analytics & Metrics"])


@router.post("/v1/analytics/snapshots")
def record_metric(
    req: MetricSnapshotCreate,
    repo: ContentOpsRepository = Depends(get_repository),
    user: UserContext = Depends(require_roles("Owner", "Editor", "ServiceAgent"))
):
    post = repo.db.query(PublishedPostModel).filter(PublishedPostModel.id == req.post_id).first()
    if not post or post.workspace_id != user.workspace_id:
        raise HTTPException(status_code=403, detail="Post not found or access denied for this workspace.")
    snapshot = repo.record_metric_snapshot(
        post_id=req.post_id,
        impressions=req.impressions,
        engagements=req.engagements,
        clicks=req.clicks,
        comments=req.comments,
        shares=req.shares,
        raw_payload=req.raw_payload
    )
    return {"id": snapshot.id, "post_id": snapshot.post_id, "observed_at": snapshot.observed_at}


@router.get("/v1/analytics/overview")
def get_analytics_overview(
    repo: ContentOpsRepository = Depends(get_repository),
    user: UserContext = Depends(require_roles("Owner", "Editor", "Viewer", "ServiceAgent"))
) -> Dict[str, Any]:
    posts = repo.db.query(PublishedPostModel).filter(PublishedPostModel.workspace_id == user.workspace_id).all()
    post_ids = [p.id for p in posts]
    snapshots = (
        repo.db.query(MetricSnapshotModel)
        .filter(MetricSnapshotModel.post_id.in_(post_ids))
        .all()
        if post_ids else []
    )

    total_impressions = sum(s.impressions for s in snapshots)
    total_engagements = sum(s.engagements for s in snapshots)
    total_clicks = sum(s.clicks for s in snapshots)
    total_comments = sum(s.comments for s in snapshots)
    total_shares = sum(s.shares for s in snapshots)

    avg_engagement_rate = (
        round((total_engagements / max(1, total_impressions)) * 100, 2)
        if total_impressions > 0 else 0.0
    )

    return {
        "published_posts_count": len(posts),
        "total_impressions": total_impressions,
        "total_engagements": total_engagements,
        "total_clicks": total_clicks,
        "total_comments": total_comments,
        "total_shares": total_shares,
        "average_engagement_rate": avg_engagement_rate,
        "platform_breakdown": {
            "linkedin": {"posts": len([p for p in posts if p.platform == "linkedin"]), "weight": 0.65},
            "x": {"posts": len([p for p in posts if p.platform == "x"]), "weight": 0.35}
        }
    }
