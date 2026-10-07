import os
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from packages.security.auth import create_access_token, Role

router = APIRouter(prefix="/v1/auth", tags=["Authentication"])


class DevTokenRequest(BaseModel):
    user_id: str = Field("dev_user", description="ID de l'utilisateur")
    role: str = Field(Role.EDITOR.value, description="Rôle RBAC (Owner, Editor, Viewer, ServiceAgent)")
    workspace_id: str = Field("ws_default", description="ID du workspace tenant")


@router.post("/dev-token")
def issue_dev_token(req: DevTokenRequest):
    """
    Issues signed JWT access tokens strictly in local development environment (ENV=dev).
    Blocked in production.
    """
    env = (os.getenv("ENV") or "production").strip().lower()
    if env not in ("dev", "development", "local", "test"):
        raise HTTPException(
            status_code=403,
            detail="Dev token generation is strictly disabled in non-dev environments."
        )
    token = create_access_token(
        user_id=req.user_id,
        role=req.role,
        workspace_id=req.workspace_id
    )
    return {
        "access_token": token,
        "token_type": "bearer",
        "role": req.role,
        "workspace_id": req.workspace_id
    }
