from typing import Optional
from fastapi import HTTPException, Depends, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from infra.db.database import get_db
from infra.db.repository import ContentOpsRepository
from packages.security.auth import decode_access_token

security = HTTPBearer(auto_error=False)


class UserContext:
    def __init__(self, user_id: str, role: str, workspace_id: str):
        self.user_id = user_id
        self.role = role  # Owner, Editor, Viewer, ServiceAgent
        self.workspace_id = workspace_id


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security)
) -> UserContext:
    """
    Extracts and cryptographically validates user, role, and workspace_id strictly from JWT token.
    Any reliance on unverified X-User-Role / X-Workspace-Id headers is completely eliminated.
    """
    if credentials is None or not credentials.credentials:
        raise HTTPException(
            status_code=401,
            detail="Authentication credentials were not provided",
            headers={"WWW-Authenticate": "Bearer"}
        )
    try:
        claims = decode_access_token(credentials.credentials)
    except Exception as e:
        raise HTTPException(
            status_code=401,
            detail=f"Invalid or expired authentication token: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"}
        )

    user_id = claims.get("sub")
    role = claims.get("role")
    workspace_id = claims.get("workspace_id")

    if not user_id or not role or not workspace_id:
        raise HTTPException(
            status_code=401,
            detail="Token claims are incomplete",
            headers={"WWW-Authenticate": "Bearer"}
        )

    return UserContext(user_id=user_id, role=role, workspace_id=workspace_id)


def require_roles(*allowed_roles: str):
    """RBAC Guard dependency ensuring minimum role privileges."""
    def role_checker(user: UserContext = Depends(get_current_user)) -> UserContext:
        normalized_user_role = user.role.lower()
        normalized_allowed = [r.lower() for r in allowed_roles]
        if normalized_user_role not in normalized_allowed and "owner" != normalized_user_role:
            raise HTTPException(
                status_code=403,
                detail=f"Action forbidden for role '{user.role}'. Required: {allowed_roles}"
            )
        return user
    return role_checker


def get_repository(db: Session = Depends(get_db)) -> ContentOpsRepository:
    return ContentOpsRepository(db)
