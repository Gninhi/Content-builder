from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class SocialProvider(str, Enum):
    LINKEDIN = "linkedin"
    X = "x"
    INSTAGRAM = "instagram"
    YOUTUBE = "youtube"


class SocialAccountStatus(str, Enum):
    ACTIVE = "ACTIVE"
    EXPIRED = "EXPIRED"
    REVOKED = "REVOKED"
    PENDING_OAUTH = "PENDING_OAUTH"


class PublicationStatus(str, Enum):
    DRAFT = "DRAFT"
    SCHEDULED = "SCHEDULED"
    PUBLISHING = "PUBLISHING"
    PUBLISHED = "PUBLISHED"
    FAILED = "FAILED"
    DELETED = "DELETED"


class ConnectedSocialAccount(BaseModel):
    """
    Data model representing an external connected social account
    associated with a specific workspace.
    """
    id: str = Field(..., description="Unique internal account identifier")
    workspace_id: str = Field(..., description="Multi-tenant workspace isolation ID")
    provider: SocialProvider = Field(..., description="Social network provider")
    account_id: str = Field(..., description="Provider external account ID or handle")
    account_name: str = Field(..., description="Display name or profile handle")
    granted_scopes: List[str] = Field(default_factory=list, description="OAuth scopes granted by user")
    status: SocialAccountStatus = Field(default=SocialAccountStatus.PENDING_OAUTH)
    token_expires_at: Optional[datetime] = Field(None, description="Access token expiration timestamp (UTC)")
    connected_at: Optional[datetime] = Field(None, description="Account connection timestamp")
    last_used_at: Optional[datetime] = Field(None, description="Last successful publication timestamp")


class PublicationResult(BaseModel):
    """Result of a social publication or scheduling request."""
    platform_post_id: str
    provider: SocialProvider
    status: PublicationStatus
    published_at: Optional[datetime] = None
    scheduled_at: Optional[datetime] = None
    permalink_url: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
