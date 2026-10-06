from fastapi import APIRouter, Depends
from typing import Dict, Any
from infra.db.repository import ContentOpsRepository
from infra.db.models import PublicationJobModel, PublishedPostModel
from apps.api.dependencies import get_repository

router = APIRouter(tags=["Editorial Calendar"])


@router.get("/v1/calendar")
def get_editorial_calendar(
    repo: ContentOpsRepository = Depends(get_repository)
) -> Dict[str, Any]:
    scheduled_jobs = (
        repo.db.query(PublicationJobModel)
        .order_by(PublicationJobModel.scheduled_at.asc())
        .all()
    )

    published_posts = (
        repo.db.query(PublishedPostModel)
        .order_by(PublishedPostModel.published_at.desc())
        .all()
    )

    return {
        "scheduled": [
            {
                "job_id": j.id,
                "variant_id": j.variant_id,
                "platform": j.platform,
                "scheduled_at": j.scheduled_at,
                "status": j.status,
                "body_snippet": j.variant.body[:80] + "..." if j.variant else ""
            }
            for j in scheduled_jobs
        ],
        "published": [
            {
                "post_id": p.id,
                "platform": p.platform,
                "external_id": p.external_post_id,
                "published_at": p.published_at,
                "permalink": p.permalink,
                "body_snippet": p.final_payload.get("body", "")[:80] + "..."
            }
            for p in published_posts
        ]
    }
