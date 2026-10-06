from fastapi import Header, HTTPException, Depends
from sqlalchemy.orm import Session
from infra.db.database import get_db
from infra.db.repository import ContentOpsRepository


class UserContext:
    def __init__(self, user_id: str, role: str, workspace_id: str):
        self.user_id = user_id
        self.role = role  # Owner, Editor, Analyst, ServiceAgent
        self.workspace_id = workspace_id


def get_current_user(
    x_user_id: str = Header("user_owner", alias="X-User-Id"),
    x_user_role: str = Header("Owner", alias="X-User-Role"),
    x_workspace_id: str = Header("ws_default", alias="X-Workspace-Id"),
) -> UserContext:
    """Extracts user and workspace tenant context from headers."""
    valid_roles = ["Owner", "Editor", "Analyst", "ServiceAgent"]
    if x_user_role not in valid_roles:
        raise HTTPException(status_code=403, detail=f"Invalid user role. Allowed: {valid_roles}")
    return UserContext(user_id=x_user_id, role=x_user_role, workspace_id=x_workspace_id)


def require_roles(*allowed_roles: str):
    """RBAC Guard decorator/dependency ensuring minimum role privileges."""
    def role_checker(user: UserContext = Depends(get_current_user)):
        if user.role not in allowed_roles and "Owner" not in user.role:
            raise HTTPException(
                status_code=403,
                detail=f"Action forbidden for role '{user.role}'. Required: {allowed_roles}"
            )
        return user
    return role_checker


def get_repository(db: Session = Depends(get_db)) -> ContentOpsRepository:
    return ContentOpsRepository(db)
