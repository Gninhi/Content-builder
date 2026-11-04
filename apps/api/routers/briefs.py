from fastapi import APIRouter, Depends, HTTPException
from packages.contracts.schemas import ContentBriefCreate
from apps.api.dependencies import get_repository, UserContext, require_roles
from infra.db.repository import ContentOpsRepository

router = APIRouter(tags=["Content Briefs"])


@router.post("/v1/briefs")
def create_brief(
    req: ContentBriefCreate,
    repo: ContentOpsRepository = Depends(get_repository),
    user: UserContext = Depends(require_roles("Owner", "Editor"))
):
    if req.workspace_id and req.workspace_id != user.workspace_id:
        raise HTTPException(status_code=403, detail="Cannot create brief for another workspace.")
    brief = repo.create_brief(
        workspace_id=user.workspace_id,
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


@router.get("/v1/briefs")
def list_briefs(
    limit: int = 50,
    repo: ContentOpsRepository = Depends(get_repository),
    user: UserContext = Depends(require_roles("Owner", "Editor", "Viewer"))
):
    """Lists briefs belonging strictly to the caller's workspace."""
    briefs = repo.list_briefs(workspace_id=user.workspace_id, limit=limit)
    return [
        {
            "id": b.id,
            "workspace_id": b.workspace_id,
            "idea_id": b.idea_id,
            "campaign_id": b.campaign_id,
            "objective": b.objective,
            "platform_targets": b.platform_targets,
            "requirements": b.requirements,
            "status": b.status,
            "created_at": b.created_at
        }
        for b in briefs
    ]


@router.get("/v1/briefs/{brief_id}")
def get_brief(
    brief_id: str,
    repo: ContentOpsRepository = Depends(get_repository),
    user: UserContext = Depends(require_roles("Owner", "Editor", "Viewer"))
):
    """Retrieves a specific brief by id within the caller's workspace."""
    brief = repo.get_brief(brief_id=brief_id, workspace_id=user.workspace_id)
    if not brief:
        raise HTTPException(status_code=404, detail="Brief not found.")
    return {
        "id": brief.id,
        "workspace_id": brief.workspace_id,
        "idea_id": brief.idea_id,
        "campaign_id": brief.campaign_id,
        "objective": brief.objective,
        "platform_targets": brief.platform_targets,
        "requirements": brief.requirements,
        "status": brief.status,
        "created_at": brief.created_at
    }
