import unicodedata
import zoneinfo
from datetime import datetime
from typing import List, Optional, Dict, Any, Literal
from pydantic import BaseModel, Field, ConfigDict, field_validator


class UserWorkspaceInfo(BaseModel):
    workspace_id: str
    name: str
    role: str
    timezone: str
    is_owner: bool


class UserProfileResponse(BaseModel):
    id: str
    email: str
    full_name: str
    display_name: Optional[str] = None
    job_title: Optional[str] = None
    avatar_url: Optional[str] = None
    timezone: str
    language: str
    theme: str
    notification_preferences: Dict[str, Any] = Field(default_factory=dict)
    ui_preferences: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime
    workspaces: List[UserWorkspaceInfo] = Field(default_factory=list)


class UserProfileUpdate(BaseModel):
    """
    Strict profile update contract.
    Strictly forbids mass-assignment of sensitive fields (email, role, id, password_hash, is_active).
    """
    model_config = ConfigDict(extra="forbid")

    full_name: Optional[str] = Field(None, max_length=255)
    display_name: Optional[str] = Field(None, max_length=255)
    job_title: Optional[str] = Field(None, max_length=255)
    timezone: Optional[str] = Field(None, max_length=64)
    language: Optional[Literal["fr", "en", "es", "de"]] = None
    theme: Optional[Literal["dark", "light", "system"]] = None
    notification_preferences: Optional[Dict[str, bool]] = None
    ui_preferences: Optional[Dict[str, Any]] = None

    @field_validator("full_name", "display_name", "job_title", mode="before")
    @classmethod
    def normalize_unicode(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            normalized = unicodedata.normalize("NFC", str(v).strip())
            return normalized
        return v

    @field_validator("timezone")
    @classmethod
    def validate_timezone(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            available = zoneinfo.available_timezones()
            if v not in available and v != "UTC":
                raise ValueError(f"Fuseau horaire IANA invalide: '{v}'. Exemple: 'Europe/Paris', 'America/New_York', 'UTC'")
        return v


class ChangePasswordRequest(BaseModel):
    """Secure password change request."""
    model_config = ConfigDict(extra="forbid")

    current_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=8, max_length=128)


class SessionInfoResponse(BaseModel):
    id: str
    token_jti: str
    user_agent: Optional[str] = None
    ip_address: Optional[str] = None
    last_active_at: datetime
    expires_at: datetime
    is_current: bool = False


class PersonalDataExportResponse(BaseModel):
    exported_at: datetime
    user: Dict[str, Any]
    workspaces: List[Dict[str, Any]]
    sessions: List[Dict[str, Any]]
    recent_audit_logs: List[Dict[str, Any]]


class AvatarUploadResponse(BaseModel):
    avatar_url: str
    message: str = "Avatar mis à jour avec succès."
