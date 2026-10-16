from typing import Optional
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, Float, DateTime, Text, JSON, ForeignKey, Boolean, UniqueConstraint
from sqlalchemy.orm import relationship
from infra.db.database import Base


def utc_now() -> datetime:
    """Returns current timezone-aware UTC datetime."""
    return datetime.now(timezone.utc)


def ensure_utc(dt: Optional[datetime]) -> Optional[datetime]:
    """Ensures datetime is timezone-aware in UTC (compatible with SQLite naive datetimes)."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


class WorkspaceModel(Base):
    __tablename__ = "workspaces"

    id = Column(String(64), primary_key=True)
    name = Column(String(255), nullable=False)
    timezone = Column(String(64), default="UTC")
    owner_id = Column(String(64), nullable=False)
    kill_switch_enabled = Column(Boolean, default=False, nullable=False)
    is_demo = Column(Boolean, default=False, nullable=False)
    expires_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utc_now)

    brand_profiles = relationship("BrandProfileModel", back_populates="workspace", cascade="all, delete-orphan")
    sources = relationship("ContentSourceModel", back_populates="workspace", cascade="all, delete-orphan")
    veille_sources = relationship("VeilleSourceModel", back_populates="workspace", cascade="all, delete-orphan")
    veille_runs = relationship("VeilleRunModel", back_populates="workspace", cascade="all, delete-orphan")
    signals = relationship("SignalModel", back_populates="workspace", cascade="all, delete-orphan")
    ideas = relationship("IdeaModel", back_populates="workspace", cascade="all, delete-orphan")
    social_accounts = relationship("ConnectedSocialAccountModel", back_populates="workspace", cascade="all, delete-orphan")
    llm_settings = relationship("WorkspaceLLMSettingsModel", uselist=False, back_populates="workspace", cascade="all, delete-orphan")
    members = relationship("WorkspaceMemberModel", back_populates="workspace", cascade="all, delete-orphan")


class WorkspaceLLMSettingsModel(Base):
    __tablename__ = "workspace_llm_settings"

    id = Column(String(64), primary_key=True)
    workspace_id = Column(String(64), ForeignKey("workspaces.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    default_provider_id = Column(String(64), nullable=False, default="nvidia")
    default_model_id = Column(String(128), nullable=False, default="z-ai/glm-5.3-flash")
    default_temperature = Column(Float, nullable=False, default=0.2)
    task_overrides = Column(JSON, default=dict, nullable=False)
    provider_settings = Column(JSON, default=dict, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    workspace = relationship("WorkspaceModel", back_populates="llm_settings")


class BrandProfileModel(Base):
    __tablename__ = "brand_profiles"

    id = Column(String(64), primary_key=True)
    workspace_id = Column(String(64), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False)
    version = Column(Integer, default=1, nullable=False)
    audience = Column(JSON, default=list, nullable=False)
    voice = Column(Text, nullable=False)
    pillars = Column(JSON, default=list, nullable=False)
    prohibited_topics = Column(JSON, default=list, nullable=False)
    cta_policy = Column(JSON, default=dict, nullable=False)
    created_at = Column(DateTime, default=utc_now)

    workspace = relationship("WorkspaceModel", back_populates="brand_profiles")


class ContentSourceModel(Base):
    __tablename__ = "content_sources"

    id = Column(String(64), primary_key=True)
    workspace_id = Column(String(64), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False)
    type = Column(String(32), nullable=False)
    canonical_url = Column(Text, nullable=True)
    raw_content_ref = Column(Text, nullable=False)
    extracted_facts = Column(JSON, default=list, nullable=False)
    provenance = Column(JSON, default=dict, nullable=False)
    status = Column(String(32), default="ingested")
    created_at = Column(DateTime, default=utc_now)

    workspace = relationship("WorkspaceModel", back_populates="sources")


class IdeaModel(Base):
    __tablename__ = "ideas"

    id = Column(String(64), primary_key=True)
    workspace_id = Column(String(64), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(512), nullable=False)
    angle = Column(Text, nullable=False)
    pillar = Column(String(128), nullable=False)
    audience = Column(String(128), nullable=False)
    evidence_refs = Column(JSON, default=list, nullable=False)
    novelty_score = Column(Float, default=0.0)
    relevance_score = Column(Float, default=0.0)
    effort_score = Column(Float, default=0.0)
    total_score = Column(Float, default=0.0)
    priority = Column(String(16), default="high")
    risks = Column(JSON, default=list, nullable=False)
    signal_id = Column(String(64), ForeignKey("signals.id", ondelete="SET NULL"), nullable=True, index=True)
    status = Column(String(32), default="IDEA")
    created_at = Column(DateTime, default=utc_now)

    workspace = relationship("WorkspaceModel", back_populates="ideas")
    signal = relationship("SignalModel", back_populates="ideas")


class ContentBriefModel(Base):
    __tablename__ = "content_briefs"

    id = Column(String(64), primary_key=True)
    workspace_id = Column(String(64), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False)
    idea_id = Column(String(64), ForeignKey("ideas.id", ondelete="SET NULL"), nullable=True)
    objective = Column(Text, nullable=False)
    campaign_id = Column(String(64), nullable=True)
    platform_targets = Column(JSON, default=lambda: ["linkedin", "x"], nullable=False)
    requirements = Column(JSON, default=dict, nullable=False)
    status = Column(String(32), default="BRIEFED")
    created_at = Column(DateTime, default=utc_now)

    packages = relationship("ContentPackageModel", back_populates="brief", cascade="all, delete-orphan")


class ContentPackageModel(Base):
    __tablename__ = "content_packages"

    id = Column(String(64), primary_key=True)
    brief_id = Column(String(64), ForeignKey("content_briefs.id", ondelete="CASCADE"), nullable=False)
    version = Column(Integer, default=1, nullable=False)
    model_metadata = Column(JSON, default=dict, nullable=False)
    qa_score = Column(Float, default=0.0)
    status = Column(String(32), default="DRAFT")
    created_at = Column(DateTime, default=utc_now)

    brief = relationship("ContentBriefModel", back_populates="packages")
    variants = relationship("ContentVariantModel", back_populates="package", cascade="all, delete-orphan")


class ContentVariantModel(Base):
    __tablename__ = "content_variants"

    id = Column(String(64), primary_key=True)
    package_id = Column(String(64), ForeignKey("content_packages.id", ondelete="CASCADE"), nullable=False)
    platform = Column(String(32), nullable=False)
    hook = Column(Text, nullable=False)
    body = Column(Text, nullable=False)
    cta = Column(Text, nullable=False)
    hashtags = Column(JSON, default=list, nullable=False)
    media_spec = Column(JSON, default=dict, nullable=False)
    claims = Column(JSON, default=list, nullable=False)
    payload_hash = Column(String(64), nullable=False)
    degraded = Column(Boolean, default=False, nullable=False)
    status = Column(String(32), default="DRAFT")
    created_at = Column(DateTime, default=utc_now)

    package = relationship("ContentPackageModel", back_populates="variants")
    approvals = relationship("ApprovalModel", back_populates="variant", cascade="all, delete-orphan")
    jobs = relationship("PublicationJobModel", back_populates="variant", cascade="all, delete-orphan")


class ApprovalModel(Base):
    __tablename__ = "approvals"

    id = Column(String(64), primary_key=True)
    variant_id = Column(String(64), ForeignKey("content_variants.id", ondelete="CASCADE"), nullable=False)
    decision = Column(String(32), nullable=False)
    reviewer_id = Column(String(64), nullable=False)
    feedback = Column(Text, nullable=True)
    payload_hash = Column(String(64), nullable=False)
    reviewed_at = Column(DateTime, default=utc_now)

    variant = relationship("ContentVariantModel", back_populates="approvals")


class PublicationJobModel(Base):
    __tablename__ = "publication_jobs"

    id = Column(String(64), primary_key=True)
    variant_id = Column(String(64), ForeignKey("content_variants.id", ondelete="CASCADE"), nullable=False)
    platform = Column(String(32), nullable=False)
    scheduled_at = Column(DateTime, nullable=False)
    idempotency_key = Column(String(64), unique=True, nullable=False)
    status = Column(String(32), default="SCHEDULED")
    attempt_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utc_now)

    variant = relationship("ContentVariantModel", back_populates="jobs")
    published_post = relationship("PublishedPostModel", uselist=False, back_populates="job", cascade="all, delete-orphan")


class PublishedPostModel(Base):
    __tablename__ = "published_posts"

    id = Column(String(64), primary_key=True)
    job_id = Column(String(64), ForeignKey("publication_jobs.id", ondelete="CASCADE"), nullable=False)
    external_post_id = Column(String(128), nullable=False)
    final_payload = Column(JSON, nullable=False)
    platform = Column(String(32), nullable=False)
    published_at = Column(DateTime, nullable=False)
    permalink = Column(Text, nullable=False)
    created_at = Column(DateTime, default=utc_now)

    job = relationship("PublicationJobModel", back_populates="published_post")
    metrics = relationship("MetricSnapshotModel", back_populates="post", cascade="all, delete-orphan")


class MetricSnapshotModel(Base):
    __tablename__ = "metric_snapshots"

    id = Column(String(64), primary_key=True)
    post_id = Column(String(64), ForeignKey("published_posts.id", ondelete="CASCADE"), nullable=False)
    observed_at = Column(DateTime, default=utc_now, nullable=False)
    impressions = Column(Integer, default=0)
    engagements = Column(Integer, default=0)
    clicks = Column(Integer, default=0)
    comments = Column(Integer, default=0)
    shares = Column(Integer, default=0)
    raw_payload = Column(JSON, default=dict, nullable=False)

    post = relationship("PublishedPostModel", back_populates="metrics")


class AgentRunModel(Base):
    __tablename__ = "agent_runs"

    id = Column(String(64), primary_key=True)
    workspace_id = Column(String(64), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False)
    graph = Column(String(64), nullable=False)
    node = Column(String(64), nullable=False)
    trace_id = Column(String(128), nullable=False)
    input_ref = Column(Text, nullable=True)
    output_ref = Column(Text, nullable=True)
    prompt_version = Column(String(32), nullable=True)
    model = Column(String(64), nullable=True)
    cost = Column(Float, default=0.0)
    status = Column(String(32), default="completed")
    created_at = Column(DateTime, default=utc_now)


class ConnectedSocialAccountModel(Base):
    __tablename__ = "connected_social_accounts"
    __table_args__ = (
        UniqueConstraint("workspace_id", "provider", "account_id", name="uq_workspace_provider_account"),
    )

    id = Column(String(64), primary_key=True)
    workspace_id = Column(String(64), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    provider = Column(String(32), nullable=False)
    account_id = Column(String(128), nullable=False)
    account_name = Column(String(255), nullable=True)
    encrypted_token_blob = Column(Text, nullable=False)
    key_id = Column(String(64), nullable=False, default="v1")
    scopes = Column(JSON, default=list, nullable=False)
    expires_at = Column(DateTime, nullable=True)
    status = Column(String(32), default="ACTIVE", nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    workspace = relationship("WorkspaceModel", back_populates="social_accounts")


class UserModel(Base):
    __tablename__ = "users"

    id = Column(String(64), primary_key=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=True)
    full_name = Column(String(255), nullable=False, default="")
    display_name = Column(String(255), nullable=True)
    job_title = Column(String(255), nullable=True)
    avatar_url = Column(Text, nullable=True)
    timezone = Column(String(64), default="UTC", nullable=False)
    language = Column(String(8), default="fr", nullable=False)
    theme = Column(String(16), default="dark", nullable=False)
    notification_preferences = Column(JSON, default=dict, nullable=False)
    ui_preferences = Column(JSON, default=dict, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    email_verified = Column(Boolean, default=False, nullable=False)
    email_verification_token_hash = Column(String(128), nullable=True, index=True)
    email_verification_expires_at = Column(DateTime, nullable=True)
    password_reset_token_hash = Column(String(128), nullable=True, index=True)
    password_reset_expires_at = Column(DateTime, nullable=True)
    cgu_accepted_at = Column(DateTime, nullable=True)
    cgu_version = Column(String(32), nullable=True)
    privacy_accepted_at = Column(DateTime, nullable=True)
    privacy_version = Column(String(32), nullable=True)
    failed_login_attempts = Column(Integer, default=0, nullable=False)
    locked_until = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    memberships = relationship("WorkspaceMemberModel", back_populates="user", cascade="all, delete-orphan")
    sessions = relationship("UserSessionModel", back_populates="user", cascade="all, delete-orphan")
    refresh_tokens = relationship("UserRefreshTokenModel", back_populates="user", cascade="all, delete-orphan")


class UserRefreshTokenModel(Base):
    __tablename__ = "user_refresh_tokens"

    id = Column(String(64), primary_key=True)
    user_id = Column(String(64), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    token_hash = Column(String(128), unique=True, index=True, nullable=False)
    family_id = Column(String(64), index=True, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    is_revoked = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)

    user = relationship("UserModel", back_populates="refresh_tokens")


class WorkspaceInvitationModel(Base):
    __tablename__ = "workspace_invitations"

    id = Column(String(64), primary_key=True)
    workspace_id = Column(String(64), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    email = Column(String(255), nullable=False, index=True)
    role = Column(String(32), default="Editor", nullable=False)
    invitation_code_hash = Column(String(128), unique=True, index=True, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    accepted_at = Column(DateTime, nullable=True)
    created_by = Column(String(64), nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)

    workspace = relationship("WorkspaceModel")


class WorkspaceMemberModel(Base):
    __tablename__ = "workspace_members"
    __table_args__ = (
        UniqueConstraint("workspace_id", "user_id", name="uq_workspace_member"),
    )

    id = Column(String(64), primary_key=True)
    workspace_id = Column(String(64), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(String(64), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    role = Column(String(32), nullable=False, default="Viewer")
    created_at = Column(DateTime, default=utc_now, nullable=False)

    workspace = relationship("WorkspaceModel", back_populates="members")
    user = relationship("UserModel", back_populates="memberships")


class UserSessionModel(Base):
    __tablename__ = "user_sessions"

    id = Column(String(64), primary_key=True)
    user_id = Column(String(64), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    token_jti = Column(String(64), unique=True, index=True, nullable=False)
    user_agent = Column(Text, nullable=True)
    ip_address = Column(String(64), nullable=True)
    last_active_at = Column(DateTime, default=utc_now, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    is_revoked = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)

    user = relationship("UserModel", back_populates="sessions")


class AuditLogModel(Base):
    __tablename__ = "audit_logs"

    id = Column(String(64), primary_key=True)
    workspace_id = Column(String(64), nullable=True, index=True)
    user_id = Column(String(64), nullable=False, index=True)
    event_type = Column(String(64), nullable=False, index=True)
    severity = Column(String(16), default="INFO", nullable=False)
    details = Column(JSON, default=dict, nullable=False)
    ip_address = Column(String(64), nullable=True)
    user_agent = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)


class VeilleSourceModel(Base):
    __tablename__ = "veille_sources"

    id = Column(String(64), primary_key=True)
    workspace_id = Column(String(64), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    url = Column(Text, nullable=False)
    axis = Column(String(64), nullable=False, index=True)  # "ia", "frameworks", "metiers"
    trust_level = Column(String(8), nullable=False, default="B")  # "A", "B", "C"
    source_type = Column(String(32), nullable=False, default="web")  # "rss", "arxiv", "github", "hackernews", "web", "serpapi"
    is_active = Column(Boolean, default=True, nullable=False)
    health_status = Column(String(32), default="HEALTHY", nullable=False)  # "HEALTHY", "DEGRADED", "ERROR"
    last_polled_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    workspace = relationship("WorkspaceModel", back_populates="veille_sources")
    signals = relationship("SignalModel", back_populates="source", cascade="all, delete-orphan")


class VeilleRunModel(Base):
    __tablename__ = "veille_runs"

    id = Column(String(64), primary_key=True)
    workspace_id = Column(String(64), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    status = Column(String(32), default="RUNNING", nullable=False, index=True)  # "RUNNING", "COMPLETED", "FAILED"
    trigger_type = Column(String(32), default="SCHEDULED", nullable=False)  # "SCHEDULED", "MANUAL"
    axis = Column(String(64), nullable=True)
    sources_contacted = Column(Integer, default=0, nullable=False)
    sources_failed = Column(Integer, default=0, nullable=False)
    signals_discovered = Column(Integer, default=0, nullable=False)
    signals_saved = Column(Integer, default=0, nullable=False)
    signals_qualified = Column(Integer, default=0, nullable=False)
    signals_rejected = Column(Integer, default=0, nullable=False)
    error_summary = Column(Text, nullable=True)
    execution_metrics = Column(JSON, default=dict, nullable=False)
    started_at = Column(DateTime, default=utc_now, nullable=False)
    completed_at = Column(DateTime, nullable=True)

    workspace = relationship("WorkspaceModel", back_populates="veille_runs")


class SignalModel(Base):
    __tablename__ = "signals"

    id = Column(String(64), primary_key=True)
    workspace_id = Column(String(64), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    source_id = Column(String(64), ForeignKey("veille_sources.id", ondelete="SET NULL"), nullable=True, index=True)
    canonical_url = Column(Text, nullable=True)
    url_hash = Column(String(64), nullable=False, index=True)  # SHA-256 for 90-day dedup
    title = Column(String(512), nullable=False)
    title_hash = Column(String(64), nullable=False, index=True)  # Normalized title hash for dedup
    summary = Column(Text, nullable=False)
    axis = Column(String(64), nullable=False, index=True)  # "ia", "frameworks", "metiers"
    trust_level = Column(String(8), nullable=False, default="B")  # "A", "B", "C"
    qualification_score = Column(Float, nullable=False, default=3.0)  # 0.0 to 5.0
    qualification_criteria = Column(JSON, default=dict, nullable=False)  # Authority, Freshness, Fact density, Impact, Exec relevance
    facts = Column(JSON, default=list, nullable=False)  # [{"fact": "...", "source_url": "...", "quote": "..."}]
    executive_takeaway = Column(Text, nullable=False)  # Why it matters for tech leaders / execs
    raw_content_ref = Column(Text, nullable=True)
    status = Column(String(32), default="QUALIFIED", nullable=False, index=True)  # "NEW", "QUALIFIED", "REJECTED", "CONVERTED"
    is_synthetic = Column(Boolean, default=False, nullable=False)  # True for demo mode
    created_at = Column(DateTime, default=utc_now, nullable=False, index=True)

    workspace = relationship("WorkspaceModel", back_populates="signals")
    source = relationship("VeilleSourceModel", back_populates="signals")
    ideas = relationship("IdeaModel", back_populates="signal")

