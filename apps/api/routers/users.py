import io
import re
from pathlib import Path
from typing import List, Optional
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File
from fastapi.responses import FileResponse
from PIL import Image

from apps.api.dependencies import get_current_user, get_repository, UserContext
from infra.db.models import UserModel
from infra.db.repository import ContentOpsRepository
from packages.contracts.users import (
    UserProfileResponse,
    UserProfileUpdate,
    UserWorkspaceInfo,
    ChangePasswordRequest,
    SessionInfoResponse,
    PersonalDataExportResponse,
    AvatarUploadResponse,
)
from packages.security.passwords import (
    hash_password,
    verify_password,
    validate_password_strength,
)

router = APIRouter(prefix="/v1", tags=["User Profile"])

AVATAR_DIR = Path("storage/avatars")
AVATAR_DIR.mkdir(parents=True, exist_ok=True)
MAX_AVATAR_SIZE_BYTES = 2 * 1024 * 1024  # 2 MB


def _get_client_ip(request: Request) -> Optional[str]:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else None


def _to_profile_response(user_model: UserModel, workspaces: List[UserWorkspaceInfo]) -> UserProfileResponse:
    return UserProfileResponse(
        id=str(user_model.id),
        email=str(user_model.email),
        full_name=str(user_model.full_name or ""),
        display_name=str(user_model.display_name) if user_model.display_name else None,
        job_title=str(user_model.job_title) if user_model.job_title else None,
        avatar_url=str(user_model.avatar_url) if user_model.avatar_url else None,
        timezone=str(user_model.timezone or "UTC"),
        language=str(user_model.language or "fr"),
        theme=str(user_model.theme or "dark"),
        notification_preferences=dict(user_model.notification_preferences or {}),
        ui_preferences=dict(user_model.ui_preferences or {}),
        created_at=getattr(user_model, "created_at"),
        updated_at=getattr(user_model, "updated_at"),
        workspaces=workspaces,
    )


@router.get("/me", response_model=UserProfileResponse)
def get_my_profile(
    user: UserContext = Depends(get_current_user),
    repo: ContentOpsRepository = Depends(get_repository),
):
    """Retrieves the authenticated user's profile and workspace memberships."""
    user_model = repo.get_or_create_user(
        user_id=user.user_id,
        default_role=user.role,
        workspace_id=user.workspace_id,
    )
    workspaces_data = repo.get_user_workspaces(user.user_id)
    workspaces = [UserWorkspaceInfo(**ws) for ws in workspaces_data]
    return _to_profile_response(user_model, workspaces)


@router.patch("/me", response_model=UserProfileResponse)
def update_my_profile(
    updates: UserProfileUpdate,
    request: Request,
    user: UserContext = Depends(get_current_user),
    repo: ContentOpsRepository = Depends(get_repository),
):
    """
    Updates user personal profile and preferences.
    Mass assignment of sensitive fields (email, role, id, is_active) is strictly rejected.
    """
    update_dict = updates.model_dump(exclude_unset=True)
    if not update_dict:
        return get_my_profile(user=user, repo=repo)

    updated_user = repo.update_user_profile(user.user_id, update_dict)
    if not updated_user:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable.")

    repo.record_audit_log(
        user_id=user.user_id,
        event_type="USER_PROFILE_UPDATED",
        workspace_id=user.workspace_id,
        details={"updated_fields": list(update_dict.keys())},
        ip_address=_get_client_ip(request),
        user_agent=request.headers.get("user-agent"),
    )

    workspaces_data = repo.get_user_workspaces(user.user_id)
    workspaces = [UserWorkspaceInfo(**ws) for ws in workspaces_data]
    return _to_profile_response(updated_user, workspaces)


@router.post("/me/avatar", response_model=AvatarUploadResponse)
async def upload_avatar(
    request: Request,
    file: UploadFile = File(...),
    user: UserContext = Depends(get_current_user),
    repo: ContentOpsRepository = Depends(get_repository),
):
    """
    Secure avatar upload:
    - Inspects file content and magic bytes (JPEG, PNG, WebP only; rejects SVG / HTML / scripts)
    - Enforces 2MB maximum size limit
    - Strips EXIF metadata using Pillow re-encoding
    - Normalizes & resizes image to max 512x512
    """
    content = await file.read()
    if len(content) > MAX_AVATAR_SIZE_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"L'image dépasse la taille maximale autorisée (2 Mo). Taille reçue: {len(content)} octets.",
        )

    # Magic byte verification
    is_jpeg = content.startswith(b"\xff\xd8\xff")
    is_png = content.startswith(b"\x89PNG\r\n\x1a\n")
    is_webp = len(content) > 12 and content[:4] == b"RIFF" and content[8:12] == b"WEBP"

    if not (is_jpeg or is_png or is_webp):
        raise HTTPException(
            status_code=415,
            detail="Format d'image non supporté ou invalide. Formats acceptés : JPEG, PNG, WebP. Les fichiers SVG sont strictement interdits pour des raisons de sécurité.",
        )

    try:
        image = Image.open(io.BytesIO(content))
        image.verify()  # Verify structural integrity
        image = Image.open(io.BytesIO(content))  # Reopen after verify
    except Exception:
        raise HTTPException(
            status_code=400,
            detail="Le fichier fourni n'est pas une image valide ou est corrompu.",
        )

    # Convert to RGB / RGBA to strip EXIF and normalize color space
    if image.mode in ("RGBA", "LA") or (image.mode == "P" and "transparency" in image.info):
        clean_image = image.convert("RGBA")
    else:
        clean_image = image.convert("RGB")

    # Resize to max 512x512 while maintaining aspect ratio
    clean_image.thumbnail((512, 512), Image.Resampling.LANCZOS)

    # Save to disk as WebP
    filename = f"avatar_{user.user_id}_{int(datetime.now(timezone.utc).timestamp())}.webp"
    file_path = AVATAR_DIR / filename
    clean_image.save(file_path, format="WEBP", quality=85)

    avatar_url = f"/v1/avatars/{filename}"
    repo.update_user_profile(user.user_id, {"avatar_url": avatar_url})

    repo.record_audit_log(
        user_id=user.user_id,
        event_type="USER_AVATAR_UPDATED",
        workspace_id=user.workspace_id,
        details={"filename": filename, "size_bytes": file_path.stat().st_size},
        ip_address=_get_client_ip(request),
        user_agent=request.headers.get("user-agent"),
    )

    return AvatarUploadResponse(avatar_url=avatar_url, message="Avatar mis à jour avec succès.")


@router.get("/avatars/{filename}")
def serve_avatar(filename: str):
    """Serves sanitized avatar files with strict path-traversal prevention."""
    if not re.match(r"^avatar_[a-zA-Z0-9_\-]+\.webp$", filename):
        raise HTTPException(status_code=404, detail="Avatar introuvable.")

    file_path = AVATAR_DIR / filename
    if not file_path.is_file():
        raise HTTPException(status_code=404, detail="Avatar introuvable.")

    return FileResponse(
        path=str(file_path),
        media_type="image/webp",
        headers={
            "X-Content-Type-Options": "nosniff",
            "Cache-Control": "public, max-age=86400",
        },
    )


@router.post("/me/change-password")
def change_password(
    req: ChangePasswordRequest,
    request: Request,
    user: UserContext = Depends(get_current_user),
    repo: ContentOpsRepository = Depends(get_repository),
):
    """
    Changes user password securely:
    - Verifies current password if one is already set
    - Validates new password complexity
    - Hashes with Argon2id
    - Automatically revokes other active sessions
    """
    user_model = repo.get_or_create_user(
        user_id=user.user_id,
        default_role=user.role,
        workspace_id=user.workspace_id,
    )

    if user_model.password_hash:
        if not verify_password(req.current_password, str(user_model.password_hash)):
            raise HTTPException(status_code=400, detail="Le mot de passe actuel est incorrect.")

    # Validate complexity
    is_valid, error_msg = validate_password_strength(req.new_password)
    if not is_valid:
        raise HTTPException(status_code=422, detail=error_msg or "Mot de passe trop faible.")

    new_hash = hash_password(req.new_password)
    repo.update_user_password(user.user_id, new_hash)

    # Revoke other sessions
    revoked_count = repo.revoke_other_sessions(user.user_id, current_jti=user.jti)

    repo.record_audit_log(
        user_id=user.user_id,
        event_type="USER_PASSWORD_CHANGED",
        severity="WARNING",
        workspace_id=user.workspace_id,
        details={"other_sessions_revoked": revoked_count},
        ip_address=_get_client_ip(request),
        user_agent=request.headers.get("user-agent"),
    )

    return {
        "message": "Mot de passe mis à jour avec succès. Les autres sessions actives ont été révoquées.",
        "revoked_sessions_count": revoked_count,
    }


@router.get("/me/sessions", response_model=List[SessionInfoResponse])
def get_user_sessions(
    user: UserContext = Depends(get_current_user),
    repo: ContentOpsRepository = Depends(get_repository),
):
    """Lists all active and historical sessions for the current user."""
    sessions = repo.list_user_sessions(user.user_id)
    return [
        SessionInfoResponse(
            id=str(s.id),
            token_jti=str(s.token_jti),
            user_agent=str(s.user_agent) if s.user_agent else None,
            ip_address=str(s.ip_address) if s.ip_address else None,
            last_active_at=getattr(s, "last_active_at"),
            expires_at=getattr(s, "expires_at"),
            is_current=bool(user.jti and str(s.token_jti) == user.jti),
        )
        for s in sessions
        if not s.is_revoked
    ]


@router.delete("/me/sessions/{session_id}")
def revoke_single_session(
    session_id: str,
    request: Request,
    user: UserContext = Depends(get_current_user),
    repo: ContentOpsRepository = Depends(get_repository),
):
    """Revokes a specific session belonging to the user (IDOR protected)."""
    revoked = repo.revoke_session(user.user_id, session_id)
    if not revoked:
        raise HTTPException(status_code=404, detail="Session introuvable ou déjà révoquée.")

    repo.record_audit_log(
        user_id=user.user_id,
        event_type="USER_SESSION_REVOKED",
        workspace_id=user.workspace_id,
        details={"session_id": session_id},
        ip_address=_get_client_ip(request),
        user_agent=request.headers.get("user-agent"),
    )

    return {"message": "Session révoquée avec succès."}


@router.post("/me/sessions/revoke-others")
def revoke_other_sessions(
    request: Request,
    user: UserContext = Depends(get_current_user),
    repo: ContentOpsRepository = Depends(get_repository),
):
    """Revokes all sessions except the current active session."""
    count = repo.revoke_other_sessions(user.user_id, current_jti=user.jti)

    repo.record_audit_log(
        user_id=user.user_id,
        event_type="USER_OTHER_SESSIONS_REVOKED",
        workspace_id=user.workspace_id,
        details={"revoked_count": count},
        ip_address=_get_client_ip(request),
        user_agent=request.headers.get("user-agent"),
    )

    return {"message": f"{count} autre(s) session(s) révoquée(s) avec succès."}


@router.get("/me/export", response_model=PersonalDataExportResponse)
def export_my_data(
    request: Request,
    user: UserContext = Depends(get_current_user),
    repo: ContentOpsRepository = Depends(get_repository),
):
    """
    GDPR Article 20 - Right to data portability.
    Exports all personal data linked to the current user in structured JSON.
    """
    user_model = repo.get_or_create_user(user.user_id, default_role=user.role, workspace_id=user.workspace_id)
    workspaces = repo.get_user_workspaces(user.user_id)
    sessions = repo.list_user_sessions(user.user_id)
    audit_logs = repo.get_user_audit_logs(user.user_id, limit=100)

    repo.record_audit_log(
        user_id=user.user_id,
        event_type="USER_DATA_EXPORTED",
        workspace_id=user.workspace_id,
        details={"scope": "full_gdpr_export"},
        ip_address=_get_client_ip(request),
        user_agent=request.headers.get("user-agent"),
    )

    user_data = {
        "id": user_model.id,
        "email": user_model.email,
        "full_name": user_model.full_name,
        "display_name": user_model.display_name,
        "job_title": user_model.job_title,
        "avatar_url": user_model.avatar_url,
        "timezone": user_model.timezone,
        "language": user_model.language,
        "theme": user_model.theme,
        "notification_preferences": user_model.notification_preferences,
        "ui_preferences": user_model.ui_preferences,
        "created_at": user_model.created_at.isoformat() if user_model.created_at else None,
        "updated_at": user_model.updated_at.isoformat() if user_model.updated_at else None,
    }

    sessions_data = [
        {
            "id": s.id,
            "user_agent": s.user_agent,
            "ip_address": s.ip_address,
            "last_active_at": s.last_active_at.isoformat() if s.last_active_at else None,
            "expires_at": s.expires_at.isoformat() if s.expires_at else None,
            "is_revoked": s.is_revoked,
        }
        for s in sessions
    ]

    logs_data = [
        {
            "id": log.id,
            "event_type": log.event_type,
            "severity": log.severity,
            "details": log.details,
            "created_at": log.created_at.isoformat() if log.created_at else None,
        }
        for log in audit_logs
    ]

    return PersonalDataExportResponse(
        exported_at=datetime.now(timezone.utc),
        user=user_data,
        workspaces=workspaces,
        sessions=sessions_data,
        recent_audit_logs=logs_data,
    )


@router.delete("/me")
def delete_my_account(
    request: Request,
    user: UserContext = Depends(get_current_user),
    repo: ContentOpsRepository = Depends(get_repository),
):
    """
    GDPR Article 17 - Right to erasure.
    Blocks account deletion if the user is the sole Owner of any workspace.
    Otherwise anonymizes personal identity and revokes all sessions.
    """
    is_last_owner, blocked_workspaces = repo.is_last_owner_of_any_workspace(user.user_id)
    if is_last_owner:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Suppression de compte impossible : vous êtes l'unique Propriétaire (Owner) "
                f"du ou des workspace(s) suivant(s) : {', '.join(blocked_workspaces)}. "
                "Veuillez transférer la propriété du workspace ou inviter un autre Propriétaire avant de supprimer votre compte."
            ),
        )

    client_ip = _get_client_ip(request)
    ua = request.headers.get("user-agent")

    # Record deletion audit log before anonymization
    repo.record_audit_log(
        user_id=user.user_id,
        event_type="USER_ACCOUNT_DELETED",
        severity="WARNING",
        workspace_id=user.workspace_id,
        details={"status": "anonymized_and_deactivated"},
        ip_address=client_ip,
        user_agent=ua,
    )

    success = repo.anonymize_user(user.user_id)
    if not success:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable.")

    return {
        "message": "Votre compte a été supprimé et vos données personnelles ont été anonymisées conformément au RGPD.",
    }
