import time
import os
import threading
from typing import Optional, Dict, Tuple
from fastapi import HTTPException, Depends, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from infra.db.database import get_db, set_db_workspace_context
from infra.db.repository import ContentOpsRepository
from packages.security.auth import decode_access_token

security = HTTPBearer(auto_error=False)


class AuthSessionCache:
    """
    Thread-safe in-memory TTL cache for session validation and RBAC role checks (PERF-01 / Lot 2).
    Eliminates redundant sequential database hits (3 to 4 per request) during authenticated API traffic.
    """
    _lock = threading.Lock()
    _user_status_cache: Dict[str, Tuple[bool, Optional[float], float]] = {}  # user_id -> (is_active, tokens_valid_after, expires_at)
    _session_revoked_cache: Dict[str, Tuple[bool, float]] = {}  # jti -> (is_revoked, expires_at)
    _member_role_cache: Dict[Tuple[str, str], Tuple[Optional[str], float]] = {}  # (ws_id, user_id) -> (role_or_none, expires_at)

    DEFAULT_TTL: float = float(os.getenv("AUTH_CACHE_TTL_SECONDS", "60.0"))

    @classmethod
    def get_user_status(cls, user_id: str) -> Optional[Tuple[bool, Optional[float]]]:
        now = time.monotonic()
        with cls._lock:
            entry = cls._user_status_cache.get(user_id)
            if entry and entry[2] > now:
                return entry[0], entry[1]
            if entry:
                cls._user_status_cache.pop(user_id, None)
            return None

    @classmethod
    def set_user_status(cls, user_id: str, is_active: bool, tokens_valid_after: Optional[float] = None, ttl: Optional[float] = None) -> None:
        expires_at = time.monotonic() + (ttl if ttl is not None else cls.DEFAULT_TTL)
        with cls._lock:
            cls._user_status_cache[user_id] = (is_active, tokens_valid_after, expires_at)

    @classmethod
    def is_session_revoked(cls, jti: str) -> Optional[bool]:
        now = time.monotonic()
        with cls._lock:
            entry = cls._session_revoked_cache.get(jti)
            if entry and entry[1] > now:
                return entry[0]
            if entry:
                cls._session_revoked_cache.pop(jti, None)
            return None

    @classmethod
    def set_session_revoked(cls, jti: str, is_revoked: bool, ttl: Optional[float] = None) -> None:
        expires_at = time.monotonic() + (ttl if ttl is not None else cls.DEFAULT_TTL)
        with cls._lock:
            cls._session_revoked_cache[jti] = (is_revoked, expires_at)

    @classmethod
    def get_member_role(cls, workspace_id: str, user_id: str) -> Optional[str]:
        now = time.monotonic()
        key = (workspace_id, user_id)
        with cls._lock:
            entry = cls._member_role_cache.get(key)
            if entry and entry[1] > now:
                return entry[0]
            if entry:
                cls._member_role_cache.pop(key, None)
            return None

    @classmethod
    def set_member_role(cls, workspace_id: str, user_id: str, role: Optional[str], ttl: Optional[float] = None) -> None:
        expires_at = time.monotonic() + (ttl if ttl is not None else cls.DEFAULT_TTL)
        key = (workspace_id, user_id)
        with cls._lock:
            cls._member_role_cache[key] = (role, expires_at)

    @classmethod
    def invalidate_user(cls, user_id: str) -> None:
        with cls._lock:
            cls._user_status_cache.pop(user_id, None)
            keys_to_del = [k for k in cls._member_role_cache if k[1] == user_id]
            for k in keys_to_del:
                cls._member_role_cache.pop(k, None)

    @classmethod
    def invalidate_session(cls, jti: str) -> None:
        with cls._lock:
            cls._session_revoked_cache[jti] = (True, time.monotonic() + cls.DEFAULT_TTL)

    @classmethod
    def invalidate_member_role(cls, workspace_id: str, user_id: str) -> None:
        with cls._lock:
            cls._member_role_cache.pop((workspace_id, user_id), None)

    @classmethod
    def clear_all(cls) -> None:
        with cls._lock:
            cls._user_status_cache.clear()
            cls._session_revoked_cache.clear()
            cls._member_role_cache.clear()


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
    Enforces user active status and session revocation against the database with high-performance caching (PERF-01).
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

    # Check user active status and global invalidation (cached - PERF-01)
    cached_status = AuthSessionCache.get_user_status(user_id)
    if cached_status is not None:
        is_active, tokens_valid_after = cached_status
    else:
        from infra.db.models import UserModel
        user_record = db.query(UserModel).filter(UserModel.id == user_id).first()
        if user_record and not user_record.is_active:
            AuthSessionCache.set_user_status(user_id, False, None)
            raise HTTPException(
                status_code=401,
                detail="Compte utilisateur désactivé. Accès refusé.",
                headers={"WWW-Authenticate": "Bearer"}
            )
        is_active = user_record.is_active if user_record else True
        tokens_valid_after = None
        if user_record and isinstance(user_record.ui_preferences, dict):
            tva = user_record.ui_preferences.get("_tokens_valid_after")
            if tva is not None:
                try:
                    tokens_valid_after = float(tva)
                except (TypeError, ValueError):
                    pass
        AuthSessionCache.set_user_status(user_id, is_active, tokens_valid_after)

    if not is_active:
        raise HTTPException(
            status_code=401,
            detail="Compte utilisateur désactivé. Accès refusé.",
            headers={"WWW-Authenticate": "Bearer"}
        )

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

    # If token contains a session jti, check if the session has been revoked (cached - PERF-01)
    if jti:
        cached_revoked = AuthSessionCache.is_session_revoked(jti)
        if cached_revoked is not None:
            is_revoked = cached_revoked
        else:
            from infra.db.models import UserSessionModel
            sess_record = db.query(UserSessionModel).filter(UserSessionModel.token_jti == jti).first()
            is_revoked = bool(sess_record and sess_record.is_revoked)
            AuthSessionCache.set_session_revoked(jti, is_revoked)

        if is_revoked:
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
    Uses cached membership role resolution (PERF-01) backed by the database.
    """
    def role_checker(
        user: UserContext = Depends(get_current_user),
        db: Session = Depends(get_db),
    ) -> UserContext:
        if user.role.lower() != "serviceagent":
            cached_role = AuthSessionCache.get_member_role(user.workspace_id, user.user_id)
            if cached_role is not None:
                if cached_role == "__FORBIDDEN__":
                    raise HTTPException(
                        status_code=403,
                        detail="Vous n'êtes pas membre de ce workspace.",
                    )
                user.role = cached_role
            else:
                from infra.db.models import WorkspaceMemberModel, WorkspaceModel
                member = db.query(WorkspaceMemberModel).filter(
                    WorkspaceMemberModel.workspace_id == user.workspace_id,
                    WorkspaceMemberModel.user_id == user.user_id,
                ).first()
                if member:
                    user.role = member.role
                    AuthSessionCache.set_member_role(user.workspace_id, user.user_id, member.role)
                else:
                    ws = db.query(WorkspaceModel).filter(WorkspaceModel.id == user.workspace_id).first()
                    if ws and str(ws.owner_id) == user.user_id:
                        user.role = "Owner"
                        AuthSessionCache.set_member_role(user.workspace_id, user.user_id, "Owner")
                    elif ws:
                        AuthSessionCache.set_member_role(user.workspace_id, user.user_id, "__FORBIDDEN__")
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
