from fastapi import APIRouter, Depends, HTTPException
from packages.contracts.schemas import ContentBriefCreate
from apps.api.dependencies import get_repository, get_current_user, UserContext, require_roles
from infra.db.repository import ContentOpsRepository

router = APIRouter(tags=["Content Briefs"])


@router.post("/v1/briefs")
def create_brief(
    req: ContentBriefCreate,
    repo: ContentOpsRepository = Depends(get_repository),
    user: UserContext = Depends(require_roles("Owner", "Editor"))
):
    brief = repo.create_brief(
        workspace_id=req.workspace_id,
        objective=req.objective,
        idea_id=req.idea_id,
        campaign_id=req.campaign_id,
        platform_targets=req.platform_targets,
        requirements=req.requirements
    )
    return {
        "id": brief.id,
        "workspace_id": brief.workspace_id,
        "idea_id": brief.idea_id,
        "objective": brief.objective,
        "platform_targets": brief.platform_targets,
        "status": brief.status,
        "created_at": brief.created_at
    }
