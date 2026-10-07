from typing import cast
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Body
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
        id=str(ws.id),
        name=str(ws.name),
        timezone=str(ws.timezone),
        owner_id=str(ws.owner_id),
        created_at=cast(datetime, ws.created_at)
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
        id=str(bp.id),
        workspace_id=str(bp.workspace_id),
        version=int(bp.version),
        audience=list(bp.audience),
        voice=str(bp.voice),
        pillars=list(bp.pillars),
        prohibited_topics=list(bp.prohibited_topics),
        cta_policy=dict(bp.cta_policy),
        created_at=cast(datetime, bp.created_at)
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
        id=str(bp.id),
        workspace_id=str(bp.workspace_id),
        version=int(bp.version),
        audience=list(bp.audience),
        voice=str(bp.voice),
        pillars=list(bp.pillars),
        prohibited_topics=list(bp.prohibited_topics),
        cta_policy=dict(bp.cta_policy),
        created_at=cast(datetime, bp.created_at)
    )


@router.get("/v1/brand-profiles/{workspace_id}/versions")
def get_brand_profile_versions(
    workspace_id: str,
    repo: ContentOpsRepository = Depends(get_repository),
    user: UserContext = Depends(require_roles("Owner", "Editor", "Viewer", "ServiceAgent"))
):
    from infra.db.models import BrandProfileModel
    if user.workspace_id != workspace_id:
        raise HTTPException(status_code=403, detail="Access to other workspace's brand profile is forbidden.")
    versions = (
        repo.db.query(BrandProfileModel)
        .filter(BrandProfileModel.workspace_id == workspace_id)
        .order_by(BrandProfileModel.version.desc())
        .all()
    )
    return [
        {
            "id": str(bp.id),
            "workspace_id": str(bp.workspace_id),
            "version": int(bp.version),
            "audience": list(bp.audience),
            "voice": str(bp.voice),
            "pillars": list(bp.pillars),
            "prohibited_topics": list(bp.prohibited_topics),
            "cta_policy": dict(bp.cta_policy),
            "created_at": bp.created_at.isoformat() if bp.created_at else None
        }
        for bp in versions
    ]


@router.get("/v1/workspaces/{workspace_id}")
def get_workspace_details(
    workspace_id: str,
    repo: ContentOpsRepository = Depends(get_repository),
    user: UserContext = Depends(require_roles("Owner", "Editor", "Viewer", "ServiceAgent"))
):
    if user.workspace_id != workspace_id:
        raise HTTPException(status_code=403, detail="Access to other workspace is forbidden.")
    ws = repo.get_workspace(workspace_id)
    if not ws:
        raise HTTPException(status_code=404, detail="Workspace not found.")
    return {
        "id": ws.id,
        "name": ws.name,
        "timezone": ws.timezone,
        "owner_id": ws.owner_id,
        "kill_switch_enabled": bool(ws.kill_switch_enabled),
        "created_at": ws.created_at.isoformat() if ws.created_at else None
    }


@router.post("/v1/workspaces/{workspace_id}/kill-switch")
def toggle_workspace_kill_switch(
    workspace_id: str,
    enabled: bool = Body(..., embed=True),
    repo: ContentOpsRepository = Depends(get_repository),
    user: UserContext = Depends(require_roles("Owner"))
):
    if user.workspace_id != workspace_id:
        raise HTTPException(status_code=403, detail="Cannot configure kill switch for another workspace.")
    ws = repo.get_workspace(workspace_id)
    if not ws:
        raise HTTPException(status_code=404, detail="Workspace not found.")
    ws.kill_switch_enabled = enabled
    repo.db.commit()
    return {
        "workspace_id": ws.id,
        "kill_switch_enabled": ws.kill_switch_enabled,
        "status": "UPDATED"
    }

