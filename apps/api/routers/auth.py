import os
import uuid
from typing import Optional, List, Any, cast
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, Depends, Request, Response
from pydantic import BaseModel, Field, EmailStr, ConfigDict
from packages.security.auth import create_access_token, decode_access_token, Role
from packages.security.passwords import hash_password, verify_password, validate_password_strength
from packages.security.tokens import generate_crypto_token, hash_crypto_token, generate_refresh_token
from packages.security.email_service import get_email_service
from packages.security.limiter import limiter, get_client_ip
from apps.api.dependencies import get_repository, get_current_user, UserContext
from infra.db.repository import ContentOpsRepository
from infra.db.models import utc_now, ensure_utc

router = APIRouter(prefix="/v1/auth", tags=["Authentication"])

REFRESH_COOKIE_NAME = "refresh_token"
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "15"))


def _is_cookie_secure(request: Request) -> bool:
    env = (os.getenv("ENV") or "dev").strip().lower()
    if env in ("production", "prod"):
        return True
    if os.getenv("COOKIE_SECURE", "false").lower() in ("true", "1", "yes"):
        return True
    return request.url.scheme == "https"


def _set_refresh_cookie(response: Response, raw_token: str, request: Request) -> None:
    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=raw_token,
        httponly=True,
        secure=_is_cookie_secure(request),
        samesite="lax",
        path="/v1/auth",
        max_age=REFRESH_TOKEN_EXPIRE_DAYS * 24 * 3600,
    )


def _clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(
        key=REFRESH_COOKIE_NAME,
        path="/v1/auth",
    )


# ==============================================================================
# Pydantic Schemas
# ==============================================================================

class RegisterRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: EmailStr = Field(..., description="Adresse email professionnelle")
    password: str = Field(..., description="Mot de passe robuste (min 10 caractères)")
    full_name: str = Field(..., min_length=2, max_length=120, description="Nom complet")
    workspace_name: Optional[str] = Field(None, max_length=120, description="Nom de l'organisation ou workspace")
    invitation_code: Optional[str] = Field(None, description="Code d'invitation optionnel")
    cgu_accepted: bool = Field(False, description="Acceptation des CGU")
    privacy_accepted: bool = Field(False, description="Acceptation de la Politique de Confidentialité")
    language: str = Field("fr", max_length=8)
    theme: str = Field("dark", max_length=16)


class VerifyEmailRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    token: str = Field(..., description="Jeton de vérification reçu par email")


class ResendVerificationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: EmailStr = Field(..., description="Adresse email du compte")


class ForgotPasswordRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: EmailStr = Field(..., description="Adresse email du compte")


class ResetPasswordRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    token: str = Field(..., description="Jeton de réinitialisation reçu par email")
    new_password: str = Field(..., description="Nouveau mot de passe")


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: EmailStr = Field(..., description="Adresse email de l'utilisateur")
    password: str = Field(..., description="Mot de passe du compte")
    workspace_id: Optional[str] = Field(None, description="Workspace cible optionnel")


class RefreshRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    refresh_token: Optional[str] = Field(None, description="Jeton de rafraîchissement optionnel si hors cookie")


class SwitchWorkspaceRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    workspace_id: str = Field(..., description="Identifiant du workspace cible")


class DevTokenRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    user_id: str = Field("dev_user", description="ID de l'utilisateur")
    role: str = Field(Role.EDITOR.value, description="Rôle RBAC (Owner, Editor, Viewer, ServiceAgent)")
    workspace_id: str = Field("ws_default", description="ID du workspace tenant")


class UserSummary(BaseModel):
    id: str
    email: str
    full_name: str
    display_name: Optional[str] = None
    avatar_url: Optional[str] = None
    email_verified: bool = False
    language: str = "fr"
    theme: str = "dark"


def _build_user_summary(user: Any) -> UserSummary:
    return UserSummary(
        id=str(user.id),
        email=str(user.email),
        full_name=str(user.full_name or ""),
        display_name=str(user.display_name) if user.display_name else None,
        avatar_url=str(user.avatar_url) if user.avatar_url else None,
        email_verified=bool(user.email_verified),
        language=str(user.language or "fr"),
        theme=str(user.theme or "dark"),
    )


class WorkspaceMembershipSummary(BaseModel):
    workspace_id: str
    name: str
    role: str
    timezone: str
    is_owner: bool
    is_demo: bool = False


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    role: str
    workspace_id: str
    user: UserSummary
    workspaces: List[WorkspaceMembershipSummary] = Field(default_factory=list)
    is_demo: bool = False
    expires_at: Optional[str] = None


# ==============================================================================
# Auth Endpoints
# ==============================================================================

@router.post("/register", status_code=201)
@limiter.limit("10/minute")
def register(
    req: RegisterRequest,
    request: Request,
    repo: ContentOpsRepository = Depends(get_repository),
):
    """
    Registers a new user, checks password security standards,
    provisions their initial workspace or processes an invitation,
    and dispatches a secure verification email.
    """
    is_valid, err_msg = validate_password_strength(req.password)
    if not is_valid:
        raise HTTPException(status_code=422, detail=err_msg or "Mot de passe non conforme aux exigences.")

    if not req.cgu_accepted or not req.privacy_accepted:
        raise HTTPException(
            status_code=400,
            detail="Vous devez accepter les conditions d'utilisation et la politique de confidentialité.",
        )

    email_clean = req.email.strip().lower()
    existing_user = repo.get_user_by_email(email_clean)
    email_svc = get_email_service()

    if existing_user:
        # OWASP anti-enumeration: return timing-safe identical success response
        if not existing_user.email_verified:
            raw_token = generate_crypto_token(32)
            token_hash = hash_crypto_token(raw_token)
            repo.set_email_verification_token(str(existing_user.id), token_hash, utc_now() + timedelta(hours=24))
            email_svc.send_verification_email(
                to_email=str(existing_user.email),
                token=raw_token,
                user_name=str(existing_user.full_name or "Utilisateur"),
            )
        return {
            "message": "Si l'adresse est valide, un email de confirmation a été envoyé pour activer le compte.",
            "email": email_clean,
            "requires_verification": True,
        }

    pwd_hash = hash_password(req.password)
    invitation_code_hash = hash_crypto_token(req.invitation_code) if req.invitation_code else None

    require_verification = os.getenv("REQUIRE_EMAIL_VERIFICATION", "false").lower() in ("true", "1")
    email_verified = not require_verification

    try:
        user, ws, role = repo.register_user_atomic(
            email=email_clean,
            password_hash=pwd_hash,
            full_name=req.full_name,
            workspace_name=req.workspace_name,
            invitation_code_hash=invitation_code_hash,
            cgu_version="2026-v1",
            privacy_version="2026-v1",
            language=req.language,
            theme=req.theme,
            email_verified=email_verified,
        )
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))

    raw_token = generate_crypto_token(32)
    token_hash = hash_crypto_token(raw_token)
    repo.set_email_verification_token(str(user.id), token_hash, utc_now() + timedelta(hours=24))
    email_svc.send_verification_email(
        to_email=str(user.email),
        token=raw_token,
        user_name=str(user.full_name or req.full_name),
    )

    return {
        "message": "Compte créé avec succès. Un email de confirmation a été envoyé pour activer votre accès.",
        "user_id": str(user.id),
        "email": str(user.email),
        "workspace_id": str(ws.id),
        "requires_verification": require_verification,
    }


@router.post("/verify-email")
def verify_email(
    req: VerifyEmailRequest,
    repo: ContentOpsRepository = Depends(get_repository),
):
    """Verifies a user's email address using the one-time cryptographic token."""
    token_hash = hash_crypto_token(req.token)
    user = repo.get_user_by_verification_token_hash(token_hash)
    if not user:
        raise HTTPException(
            status_code=400,
            detail="Jeton de vérification invalide ou expiré.",
        )
    repo.verify_user_email(str(user.id))
    repo.record_audit_log(
        user_id=str(user.id),
        event_type="email_verified",
        severity="INFO",
    )
    return {"message": "Adresse email vérifiée avec succès. Vous pouvez maintenant vous connecter."}


@router.post("/resend-verification")
@limiter.limit("5/minute")
def resend_verification(
    req: ResendVerificationRequest,
    request: Request,
    repo: ContentOpsRepository = Depends(get_repository),
):
    """Dispatches a new verification token if an unverified account exists."""
    email_clean = req.email.strip().lower()
    user = repo.get_user_by_email(email_clean)
    if user and not user.email_verified:
        raw_token = generate_crypto_token(32)
        token_hash = hash_crypto_token(raw_token)
        repo.set_email_verification_token(str(user.id), token_hash, utc_now() + timedelta(hours=24))
        email_svc = get_email_service()
        email_svc.send_verification_email(
            to_email=str(user.email),
            token=raw_token,
            user_name=str(user.full_name or "Utilisateur"),
        )
    return {"message": "Si un compte non vérifié existe pour cet email, un lien de confirmation a été envoyé."}


@router.post("/forgot-password")
@limiter.limit("5/minute")
def forgot_password(
    req: ForgotPasswordRequest,
    request: Request,
    repo: ContentOpsRepository = Depends(get_repository),
):
    """Sends a password reset token without revealing whether the email exists."""
    email_clean = req.email.strip().lower()
    user = repo.get_user_by_email(email_clean)
    if user and user.is_active:
        raw_token = generate_crypto_token(32)
        token_hash = hash_crypto_token(raw_token)
        repo.set_password_reset_token(str(user.id), token_hash, utc_now() + timedelta(hours=1))
        email_svc = get_email_service()
        email_svc.send_password_reset_email(
            to_email=str(user.email),
            token=raw_token,
            user_name=str(user.full_name or "Utilisateur"),
        )
    return {"message": "Si l'adresse est associée à un compte actif, des instructions de réinitialisation ont été envoyées."}


@router.post("/reset-password")
@limiter.limit("5/minute")
def reset_password(
    req: ResetPasswordRequest,
    request: Request,
    repo: ContentOpsRepository = Depends(get_repository),
):
    """Resets the account password and invalidates all existing sessions & tokens."""
    is_valid, err_msg = validate_password_strength(req.new_password)
    if not is_valid:
        raise HTTPException(status_code=422, detail=err_msg or "Mot de passe non conforme.")

    token_hash = hash_crypto_token(req.token)
    user = repo.get_user_by_password_reset_token_hash(token_hash)
    if not user:
        raise HTTPException(
            status_code=400,
            detail="Jeton de réinitialisation invalide ou expiré.",
        )

    new_hash = hash_password(req.new_password)
    repo.reset_password_with_token(str(user.id), new_hash)
    repo.record_audit_log(
        user_id=str(user.id),
        event_type="password_reset_success",
        severity="INFO",
        ip_address=get_client_ip(request),
    )
    return {"message": "Votre mot de passe a été réinitialisé avec succès. Vous pouvez maintenant vous connecter."}


@router.post("/login", response_model=LoginResponse)
@limiter.limit("10/minute")
def login_with_password(
    req: LoginRequest,
    request: Request,
    response: Response,
    repo: ContentOpsRepository = Depends(get_repository),
):
    """
    Authenticates a user with email and password (Argon2id).
    Enforces account lockout, issues short-lived JWT access token,
    and sets an httpOnly rotated refresh cookie.
    """
    email_clean = req.email.strip().lower()
    user = repo.get_user_by_email(email_clean)

    if not user or not user.is_active or not user.password_hash:
        # Timing attack countermeasure
        verify_password("dummy_password_for_timing_safety_2026", "$argon2id$v=19$m=65536,t=2,p=1$c29tZXNhbHQ$dummyhashfortimingprotection")
        raise HTTPException(
            status_code=401,
            detail="Email ou mot de passe invalide.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = str(user.id)
    if user.locked_until:
        locked_dt = ensure_utc(cast(Optional[datetime], user.locked_until))
        if locked_dt and locked_dt > utc_now():
            raise HTTPException(
                status_code=423,
                detail="Compte temporairement verrouillé suite à plusieurs tentatives infructueuses. Veuillez réessayer plus tard.",
            )
        else:
            repo.reset_failed_logins(user_id)

    if not verify_password(req.password, str(user.password_hash or "")):
        attempts, locked = repo.record_failed_login(user_id)
        if locked:
            raise HTTPException(
                status_code=423,
                detail="Compte temporairement verrouillé suite à plusieurs tentatives infructueuses. Veuillez réessayer plus tard.",
            )
        raise HTTPException(
            status_code=401,
            detail="Email ou mot de passe invalide.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    repo.reset_failed_logins(user_id)

    require_verification = os.getenv("REQUIRE_EMAIL_VERIFICATION", "false").lower() in ("true", "1")
    if require_verification and not user.email_verified:
        raise HTTPException(
            status_code=403,
            detail="Veuillez confirmer votre adresse email avant de vous connecter.",
        )

    workspaces = repo.get_user_workspaces(user_id)
    target_ws = "ws_default"
    target_role = Role.VIEWER.value

    if req.workspace_id:
        matched = next((w for w in workspaces if w.get("workspace_id") == req.workspace_id), None)
        if not matched:
            raise HTTPException(
                status_code=403,
                detail=f"Vous n'êtes pas membre du workspace '{req.workspace_id}'.",
            )
        target_ws = matched["workspace_id"]
        target_role = matched["role"]
    elif workspaces:
        target_ws = workspaces[0]["workspace_id"]
        target_role = workspaces[0]["role"]

    session_jti = uuid.uuid4().hex
    access_token = create_access_token(
        user_id=user_id,
        role=target_role,
        workspace_id=target_ws,
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
        jti=session_jti,
    )

    raw_refresh, refresh_hash, family_id = generate_refresh_token()
    refresh_expires_at = utc_now() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    repo.create_refresh_token(
        user_id=user_id,
        token_hash=refresh_hash,
        family_id=family_id,
        expires_at=refresh_expires_at,
    )
    _set_refresh_cookie(response, raw_refresh, request)

    client_ip = get_client_ip(request)
    user_agent = request.headers.get("user-agent") or "ContentOps Client"
    try:
        repo.create_session(
            user_id=user_id,
            token_jti=session_jti,
            expires_at=utc_now() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
            user_agent=user_agent,
            ip_address=client_ip,
        )
    except Exception:
        pass

    repo.record_audit_log(
        user_id=user_id,
        workspace_id=target_ws,
        event_type="login_success",
        severity="INFO",
        ip_address=client_ip,
        user_agent=user_agent,
    )

    ws_list = [
        WorkspaceMembershipSummary(
            workspace_id=w["workspace_id"],
            name=w["name"],
            role=w["role"],
            timezone=w.get("timezone", "UTC"),
            is_owner=w.get("is_owner", False),
            is_demo=False,
        )
        for w in workspaces
    ]

    return LoginResponse(
        access_token=access_token,
        token_type="bearer",
        user_id=user_id,
        role=target_role,
        workspace_id=target_ws,
        user=_build_user_summary(user),
        workspaces=ws_list,
        is_demo=False,
    )


@router.post("/refresh", response_model=LoginResponse)
@limiter.limit("60/minute")
def refresh_session(
    request: Request,
    response: Response,
    req_body: Optional[RefreshRequest] = None,
    repo: ContentOpsRepository = Depends(get_repository),
):
    """
    Refreshes session, detects reuse with automatic family invalidation,
    and returns a new access token and rotated refresh token cookie.
    """
    raw_token = request.cookies.get(REFRESH_COOKIE_NAME)
    if not raw_token and req_body and req_body.refresh_token:
        raw_token = req_body.refresh_token

    if not raw_token:
        raise HTTPException(
            status_code=401,
            detail="Session expirée ou jeton de rafraîchissement absent.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token_hash = hash_crypto_token(raw_token)
    rt = repo.get_refresh_token_by_hash(token_hash)

    if not rt:
        _clear_refresh_cookie(response)
        raise HTTPException(
            status_code=401,
            detail="Jeton de rafraîchissement invalide.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # REUSE DETECTION: if revoked, breach or replay detected -> revoke family
    if rt.is_revoked:
        repo.revoke_refresh_token_family(str(rt.family_id))
        _clear_refresh_cookie(response)
        repo.record_audit_log(
            user_id=str(rt.user_id),
            event_type="refresh_token_reuse_detected",
            severity="CRITICAL",
            details={"family_id": str(rt.family_id), "token_id": str(rt.id)},
            ip_address=get_client_ip(request),
            user_agent=request.headers.get("user-agent"),
        )
        raise HTTPException(
            status_code=401,
            detail="Alerte de sécurité : réutilisation de jeton détectée. Vos sessions ont été révoquées.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    expires_at_dt = ensure_utc(cast(Optional[datetime], rt.expires_at))
    if expires_at_dt and expires_at_dt < utc_now():
        repo.revoke_refresh_token(str(rt.id))
        _clear_refresh_cookie(response)
        raise HTTPException(
            status_code=401,
            detail="Session expirée. Veuillez vous reconnecter.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = repo.get_user(str(rt.user_id))
    if not user or not user.is_active:
        repo.revoke_refresh_token(str(rt.id))
        _clear_refresh_cookie(response)
        raise HTTPException(
            status_code=401,
            detail="Utilisateur inactif ou supprimé.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # ROTATION
    repo.revoke_refresh_token(str(rt.id))
    new_raw_refresh, new_token_hash, family_id = generate_refresh_token(family_id=str(rt.family_id))
    refresh_expires_at = utc_now() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    repo.create_refresh_token(
        user_id=str(user.id),
        token_hash=new_token_hash,
        family_id=family_id,
        expires_at=refresh_expires_at,
    )
    _set_refresh_cookie(response, new_raw_refresh, request)

    workspaces = repo.get_user_workspaces(str(user.id))
    target_ws = workspaces[0]["workspace_id"] if workspaces else "ws_default"
    target_role = workspaces[0]["role"] if workspaces else Role.VIEWER.value

    requested_ws = request.headers.get("x-target-workspace")
    if requested_ws:
        matched = next((w for w in workspaces if w.get("workspace_id") == requested_ws), None)
        if matched:
            target_ws = matched["workspace_id"]
            target_role = matched["role"]

    session_jti = uuid.uuid4().hex
    access_token = create_access_token(
        user_id=str(user.id),
        role=target_role,
        workspace_id=target_ws,
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
        jti=session_jti,
    )

    client_ip = get_client_ip(request)
    user_agent = request.headers.get("user-agent") or "ContentOps Client"
    try:
        repo.create_session(
            user_id=str(user.id),
            token_jti=session_jti,
            expires_at=utc_now() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
            user_agent=user_agent,
            ip_address=client_ip,
        )
    except Exception:
        pass

    ws_list = [
        WorkspaceMembershipSummary(
            workspace_id=w["workspace_id"],
            name=w["name"],
            role=w["role"],
            timezone=w.get("timezone", "UTC"),
            is_owner=w.get("is_owner", False),
            is_demo=False,
        )
        for w in workspaces
    ]

    # Check if active workspace is demo
    active_ws_record = repo.get_workspace(target_ws)
    is_demo = bool(active_ws_record.is_demo) if active_ws_record else False

    return LoginResponse(
        access_token=access_token,
        token_type="bearer",
        user_id=str(user.id),
        role=target_role,
        workspace_id=target_ws,
        user=_build_user_summary(user),
        workspaces=ws_list,
        is_demo=is_demo,
        expires_at=active_ws_record.expires_at.isoformat() if (active_ws_record and active_ws_record.expires_at) else None,
    )


@router.post("/logout")
def logout(
    request: Request,
    response: Response,
    repo: ContentOpsRepository = Depends(get_repository),
):
    """
    Logs out the user, invalidates the active refresh token and JTI session,
    and removes the httpOnly refresh cookie.
    """
    raw_token = request.cookies.get(REFRESH_COOKIE_NAME)
    if raw_token:
        token_hash = hash_crypto_token(raw_token)
        rt = repo.get_refresh_token_by_hash(token_hash)
        if rt:
            repo.revoke_refresh_token(str(rt.id))

    auth_header = request.headers.get("authorization") or request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token_str = auth_header.split(" ", 1)[1]
        try:
            claims = decode_access_token(token_str)
            jti = claims.get("jti")
            if jti:
                sess = repo.get_session_by_jti(jti)
                if sess:
                    setattr(sess, "is_revoked", True)
                    repo.db.commit()
        except Exception:
            pass

    _clear_refresh_cookie(response)
    return {"message": "Déconnexion réussie."}


@router.get("/me")
def get_me(
    user_ctx: UserContext = Depends(get_current_user),
    repo: ContentOpsRepository = Depends(get_repository),
):
    """Returns current user details, memberships, and active workspace metadata."""
    user = repo.get_user(user_ctx.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable.")

    workspaces = repo.get_user_workspaces(str(user.id))
    ws_list = [
        WorkspaceMembershipSummary(
            workspace_id=w["workspace_id"],
            name=w["name"],
            role=w["role"],
            timezone=w.get("timezone", "UTC"),
            is_owner=w.get("is_owner", False),
            is_demo=False,
        )
        for w in workspaces
    ]

    active_ws = repo.get_workspace(user_ctx.workspace_id)
    is_demo = bool(active_ws.is_demo) if active_ws else False
    expires_at = active_ws.expires_at.isoformat() if active_ws and active_ws.expires_at else None

    return {
        "user": _build_user_summary(user),
        "current_workspace_id": user_ctx.workspace_id,
        "current_role": user_ctx.role,
        "workspaces": ws_list,
        "is_demo": is_demo,
        "expires_at": expires_at,
    }


@router.post("/switch-workspace", response_model=LoginResponse)
def switch_workspace(
    req: SwitchWorkspaceRequest,
    request: Request,
    response: Response,
    user_ctx: UserContext = Depends(get_current_user),
    repo: ContentOpsRepository = Depends(get_repository),
):
    """Switches active tenant workspace and issues new scoped access token."""
    user = repo.get_user(user_ctx.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable.")

    workspaces = repo.get_user_workspaces(str(user.id))
    target = next((w for w in workspaces if w["workspace_id"] == req.workspace_id), None)
    if not target:
        raise HTTPException(
            status_code=403,
            detail=f"Vous n'avez pas accès au workspace '{req.workspace_id}'.",
        )

    session_jti = uuid.uuid4().hex
    access_token = create_access_token(
        user_id=str(user.id),
        role=target["role"],
        workspace_id=target["workspace_id"],
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
        jti=session_jti,
    )

    ws_list = [
        WorkspaceMembershipSummary(
            workspace_id=w["workspace_id"],
            name=w["name"],
            role=w["role"],
            timezone=w.get("timezone", "UTC"),
            is_owner=w.get("is_owner", False),
            is_demo=False,
        )
        for w in workspaces
    ]

    target_ws_model = repo.get_workspace(target["workspace_id"])
    is_demo = bool(target_ws_model.is_demo) if target_ws_model else False

    return LoginResponse(
        access_token=access_token,
        token_type="bearer",
        user_id=str(user.id),
        role=target["role"],
        workspace_id=target["workspace_id"],
        user=_build_user_summary(user),
        workspaces=ws_list,
        is_demo=is_demo,
        expires_at=target_ws_model.expires_at.isoformat() if (target_ws_model and target_ws_model.expires_at) else None,
    )


@router.post("/demo", response_model=LoginResponse)
@limiter.limit("10/minute")
def start_demo_session(
    request: Request,
    response: Response,
    repo: ContentOpsRepository = Depends(get_repository),
):
    """
    Creates an isolated ephemeral demo workspace with rich pre-seeded data
    for 2 hours without requiring registration. Controlled by DEMO_MODE_ENABLED.
    """
    demo_enabled = os.getenv("DEMO_MODE_ENABLED", "true").strip().lower() in ("true", "1", "yes")
    if not demo_enabled:
        raise HTTPException(
            status_code=404,
            detail="Le mode démo interactif est actuellement désactivé sur cette instance.",
        )

    try:
        repo.cleanup_expired_demo_workspaces()
    except Exception:
        pass

    user, ws, role = repo.create_demo_workspace_session(duration_minutes=120)

    session_jti = uuid.uuid4().hex
    access_token = create_access_token(
        user_id=str(user.id),
        role=role,
        workspace_id=str(ws.id),
        expires_delta=timedelta(minutes=120),
        jti=session_jti,
    )

    raw_refresh, refresh_hash, family_id = generate_refresh_token()
    repo.create_refresh_token(
        user_id=str(user.id),
        token_hash=refresh_hash,
        family_id=family_id,
        expires_at=utc_now() + timedelta(hours=2),
    )
    _set_refresh_cookie(response, raw_refresh, request)

    client_ip = get_client_ip(request)
    user_agent = request.headers.get("user-agent") or "ContentOps Demo Client"
    try:
        repo.create_session(
            user_id=str(user.id),
            token_jti=session_jti,
            expires_at=utc_now() + timedelta(hours=2),
            user_agent=user_agent,
            ip_address=client_ip,
        )
    except Exception:
        pass

    ws_list = [
        WorkspaceMembershipSummary(
            workspace_id=str(ws.id),
            name=str(ws.name),
            role=role,
            timezone=str(ws.timezone),
            is_owner=True,
            is_demo=True,
        )
    ]

    return LoginResponse(
        access_token=access_token,
        token_type="bearer",
        user_id=str(user.id),
        role=role,
        workspace_id=str(ws.id),
        user=_build_user_summary(user),
        workspaces=ws_list,
        is_demo=True,
        expires_at=ws.expires_at.isoformat() if ws.expires_at else None,
    )


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
            detail="Dev token generation is strictly disabled in non-dev environments.",
        )
    session_jti = uuid.uuid4().hex
    token = create_access_token(
        user_id=req.user_id,
        role=req.role,
        workspace_id=req.workspace_id,
        jti=session_jti,
    )
    try:
        from infra.db.database import SessionLocal
        db = SessionLocal()
        try:
            repo = ContentOpsRepository(db)
            repo.get_or_create_user(req.user_id, default_role=req.role, workspace_id=req.workspace_id)
            repo.create_session(
                user_id=req.user_id,
                token_jti=session_jti,
                expires_at=utc_now() + timedelta(hours=24),
                user_agent="DevClient/1.0",
                ip_address="127.0.0.1",
            )
        finally:
            db.close()
    except Exception:
        pass

    return {
        "access_token": token,
        "token_type": "bearer",
        "role": req.role,
        "workspace_id": req.workspace_id,
    }
