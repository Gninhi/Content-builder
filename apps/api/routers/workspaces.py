from fastapi import APIRouter, Depends, HTTPException
from packages.contracts.schemas import (
    WorkspaceCreate,
    WorkspaceResponse,
    BrandProfileCreate,
    BrandProfileResponse,
)
from apps.api.dependencies import get_repository, UserContext, require_roles
from infra.db.repository import ContentOpsRepository

router = APIRouter(tags=["Workspaces & Brand Profiles"])


@router.post("/v1/workspaces", response_model=WorkspaceResponse)
def create_workspace(
    req: WorkspaceCreate,
    repo: ContentOpsRepository = Depends(get_repository),
    user: UserContext = Depends(require_roles("Owner"))
):
    ws = repo.create_workspace(name=req.name, timezone=req.timezone, owner_id=req.owner_id)
    return WorkspaceResponse(
        id=ws.id,
        name=ws.name,
        timezone=ws.timezone,
        owner_id=ws.owner_id,
        created_at=ws.created_at
    )


@router.post("/v1/brand-profiles", response_model=BrandProfileResponse)
def create_or_update_brand_profile(
    req: BrandProfileCreate,
    repo: ContentOpsRepository = Depends(get_repository),
    user: UserContext = Depends(require_roles("Owner", "Editor"))
):
    if req.workspace_id and req.workspace_id != user.workspace_id:
        raise HTTPException(status_code=403, detail="Cannot create or update brand profile for another workspace.")
    bp = repo.create_or_version_brand_profile(
        workspace_id=user.workspace_id,
        audience=req.audience,
        voice=req.voice,
        pillars=req.pillars,
        prohibited_topics=req.prohibited_topics,
        cta_policy=req.cta_policy
    )
    return BrandProfileResponse(
        id=bp.id,
        workspace_id=bp.workspace_id,
        version=bp.version,
        audience=bp.audience,
        voice=bp.voice,
        pillars=bp.pillars,
        prohibited_topics=bp.prohibited_topics,
        cta_policy=bp.cta_policy,
        created_at=bp.created_at
    )


@router.get("/v1/brand-profiles/{workspace_id}", response_model=BrandProfileResponse)
def get_brand_profile(
    workspace_id: str,
    repo: ContentOpsRepository = Depends(get_repository),
    user: UserContext = Depends(require_roles("Owner", "Editor", "Viewer", "ServiceAgent"))
):
    if user.workspace_id != workspace_id:
        raise HTTPException(status_code=403, detail="Access to other workspace's brand profile is forbidden.")
    bp = repo.get_latest_brand_profile(workspace_id)
    if not bp:
        raise HTTPException(status_code=404, detail="Brand profile not found for workspace.")
    return BrandProfileResponse(
        id=bp.id,
        workspace_id=bp.workspace_id,
        version=bp.version,
        audience=bp.audience,
        voice=bp.voice,
        pillars=bp.pillars,
        prohibited_topics=bp.prohibited_topics,
        cta_policy=bp.cta_policy,
        created_at=bp.created_at
    )
