from sqlalchemy import Column, String, Integer, Float, DateTime, Text, JSON, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from infra.db.database import Base


class WorkspaceModel(Base):
    __tablename__ = "workspaces"

    id = Column(String(64), primary_key=True)
    name = Column(String(255), nullable=False)
    timezone = Column(String(64), default="UTC")
    owner_id = Column(String(64), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    brand_profiles = relationship("BrandProfileModel", back_populates="workspace", cascade="all, delete-orphan")
    sources = relationship("ContentSourceModel", back_populates="workspace", cascade="all, delete-orphan")
    ideas = relationship("IdeaModel", back_populates="workspace", cascade="all, delete-orphan")


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
    created_at = Column(DateTime, default=datetime.utcnow)

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
    created_at = Column(DateTime, default=datetime.utcnow)

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
    status = Column(String(32), default="IDEA")
    created_at = Column(DateTime, default=datetime.utcnow)

    workspace = relationship("WorkspaceModel", back_populates="ideas")


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
    created_at = Column(DateTime, default=datetime.utcnow)

    packages = relationship("ContentPackageModel", back_populates="brief", cascade="all, delete-orphan")


class ContentPackageModel(Base):
    __tablename__ = "content_packages"

    id = Column(String(64), primary_key=True)
    brief_id = Column(String(64), ForeignKey("content_briefs.id", ondelete="CASCADE"), nullable=False)
    version = Column(Integer, default=1, nullable=False)
    model_metadata = Column(JSON, default=dict, nullable=False)
    qa_score = Column(Float, default=0.0)
    status = Column(String(32), default="DRAFT")
    created_at = Column(DateTime, default=datetime.utcnow)

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
    status = Column(String(32), default="DRAFT")
    created_at = Column(DateTime, default=datetime.utcnow)

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
    reviewed_at = Column(DateTime, default=datetime.utcnow)

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
    created_at = Column(DateTime, default=datetime.utcnow)

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
    created_at = Column(DateTime, default=datetime.utcnow)

    job = relationship("PublicationJobModel", back_populates="published_post")
    metrics = relationship("MetricSnapshotModel", back_populates="post", cascade="all, delete-orphan")


class MetricSnapshotModel(Base):
    __tablename__ = "metric_snapshots"

    id = Column(String(64), primary_key=True)
    post_id = Column(String(64), ForeignKey("published_posts.id", ondelete="CASCADE"), nullable=False)
    observed_at = Column(DateTime, default=datetime.utcnow, nullable=False)
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
    created_at = Column(DateTime, default=datetime.utcnow)
