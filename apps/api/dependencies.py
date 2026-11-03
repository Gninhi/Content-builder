from typing import Optional
from fastapi import HTTPException, Depends, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from infra.db.database import get_db, set_db_workspace_context
from infra.db.repository import ContentOpsRepository
from packages.security.auth import decode_access_token

security = HTTPBearer(auto_error=False)


class UserContext:
    def __init__(self, user_id: str, role: str, workspace_id: str, jti: Optional[str] = None):
        self.user_id = user_id
        self.role = role  # Owner, Editor, Viewer, ServiceAgent
        self.workspace_id = workspace_id
        self.jti = jti


ROLE_HIERARCHY = {
    "owner": {"owner", "editor", "viewer"},
    "editor": {"editor", "viewer"},
    "viewer": {"viewer"},
    "serviceagent": {"serviceagent"},
}


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security),
    db: Session = Depends(get_db),
) -> UserContext:
    """
    Extracts and cryptographically validates user, role, and workspace_id strictly from JWT token.
    Enforces user active status and session revocation against the database.
    """
    if credentials is None or not credentials.credentials:
        raise HTTPException(
            status_code=401,
            detail="Authentication credentials were not provided",
            headers={"WWW-Authenticate": "Bearer"}
        )
    try:
        claims = decode_access_token(credentials.credentials)
    except Exception:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired authentication token.",
            headers={"WWW-Authenticate": "Bearer"}
        )

    user_id = claims.get("sub")
    role = claims.get("role")
    workspace_id = claims.get("workspace_id")
    jti = claims.get("jti")

    if not user_id or not role or not workspace_id:
        raise HTTPException(
            status_code=401,
            detail="Token claims are incomplete",
            headers={"WWW-Authenticate": "Bearer"}
        )

    # Check database for user status (fail-closed if deactivated)
    from infra.db.models import UserModel
    user_record = db.query(UserModel).filter(UserModel.id == user_id).first()
    if user_record and not user_record.is_active:
        raise HTTPException(
            status_code=401,
            detail="Compte utilisateur désactivé. Accès refusé.",
            headers={"WWW-Authenticate": "Bearer"}
        )

    # Check global token invalidation timestamp (e.g. after password reset)
    if user_record and isinstance(user_record.ui_preferences, dict):
        tokens_valid_after = user_record.ui_preferences.get("_tokens_valid_after")
        iat = claims.get("iat")
        if tokens_valid_after is not None and iat is not None:
            try:
                if float(iat) < float(tokens_valid_after):
                    raise HTTPException(
                        status_code=401,
                        detail="Session révoquée. Veuillez vous reconnecter.",
                        headers={"WWW-Authenticate": "Bearer"}
                    )
            except (TypeError, ValueError):
                pass

    # If token contains a session jti, check if the session has been revoked
    if jti:
        from infra.db.models import UserSessionModel
        sess_record = db.query(UserSessionModel).filter(UserSessionModel.token_jti == jti).first()
        if sess_record and sess_record.is_revoked:
            raise HTTPException(
                status_code=401,
                detail="Session révoquée. Veuillez vous reconnecter.",
                headers={"WWW-Authenticate": "Bearer"}
            )


    # Bind workspace context for multi-tenant isolation & PostgreSQL RLS
    set_db_workspace_context(db, workspace_id)

    return UserContext(user_id=user_id, role=role, workspace_id=workspace_id, jti=jti)


def require_roles(*allowed_roles: str):
    """
    RBAC Guard dependency ensuring minimum role privileges.
    Uses the database as the authoritative source of truth for workspace roles,
    and segregates ServiceAgent roles from human Owner roles.
    """
    def role_checker(
        user: UserContext = Depends(get_current_user),
        db: Session = Depends(get_db),
    ) -> UserContext:
        if user.role.lower() != "serviceagent":
            from infra.db.models import WorkspaceMemberModel, WorkspaceModel
            member = db.query(WorkspaceMemberModel).filter(
                WorkspaceMemberModel.workspace_id == user.workspace_id,
                WorkspaceMemberModel.user_id == user.user_id,
            ).first()
            if member:
                user.role = member.role
            else:
                ws = db.query(WorkspaceModel).filter(WorkspaceModel.id == user.workspace_id).first()
                if ws and str(ws.owner_id) == user.user_id:
                    user.role = "Owner"
                elif ws:
                    raise HTTPException(
                        status_code=403,
                        detail="Vous n'êtes pas membre de ce workspace.",
                    )

        normalized_user_role = user.role.lower()
        effective_roles = ROLE_HIERARCHY.get(normalized_user_role, {normalized_user_role})
        normalized_allowed = {r.lower() for r in allowed_roles}
        if not (effective_roles & normalized_allowed):
            raise HTTPException(
                status_code=403,
                detail=f"Action forbidden for role '{user.role}'. Required: {allowed_roles}"
            )
        set_db_workspace_context(db, user.workspace_id)
        return user
    return role_checker


def get_repository(db: Session = Depends(get_db)) -> ContentOpsRepository:
    return ContentOpsRepository(db)
