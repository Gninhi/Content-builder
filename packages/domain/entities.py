from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from packages.domain.state_machine import ContentStatus


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class Workspace:
    id: str
    name: str
    timezone: str = "UTC"
    owner_id: str = "default_owner"
    created_at: datetime = field(default_factory=utc_now)


@dataclass
class BrandProfile:
    id: str
    workspace_id: str
    version: int
    audience: List[str]
    voice: str
    pillars: List[str]
    prohibited_topics: List[str]
    cta_policy: Dict[str, Any]
    created_at: datetime = field(default_factory=utc_now)


@dataclass
class ContentSource:
    id: str
    workspace_id: str
    type: str  # url, note, text, rss
    canonical_url: Optional[str]
    raw_content_ref: str
    extracted_facts: List[Dict[str, Any]]
    provenance: Dict[str, Any]
    status: str = "ingested"
    created_at: datetime = field(default_factory=utc_now)


@dataclass
class Idea:
    id: str
    workspace_id: str
    title: str
    angle: str
    pillar: str
    audience: str
    evidence_refs: List[Dict[str, Any]]
    novelty_score: float
    relevance_score: float
    effort_score: float
    total_score: float
    priority: str  # high, medium, low
    risks: List[str]
    status: ContentStatus = ContentStatus.IDEA
    created_at: datetime = field(default_factory=utc_now)


@dataclass
class ContentBrief:
    id: str
    idea_id: str
    objective: str
    campaign_id: Optional[str]
    platform_targets: List[str]  # e.g., ["linkedin", "x"]
    requirements: Dict[str, Any]
    status: ContentStatus = ContentStatus.BRIEFED
    created_at: datetime = field(default_factory=utc_now)


@dataclass
class ContentVariant:
    id: str
    package_id: str
    platform: str  # "linkedin", "x", etc.
    hook: str
    body: str
    cta: str
    hashtags: List[str]
    media_spec: Dict[str, Any]
    claims: List[Dict[str, Any]]  # [{"claim": str, "source_id": str, "verified": bool}]
    payload_hash: str
    status: ContentStatus = ContentStatus.DRAFT
    created_at: datetime = field(default_factory=utc_now)


@dataclass
class ContentPackage:
    id: str
    brief_id: str
    version: int
    model_metadata: Dict[str, Any]
    qa_score: float
    variants: List[ContentVariant] = field(default_factory=list)
    status: ContentStatus = ContentStatus.DRAFT
    created_at: datetime = field(default_factory=utc_now)


@dataclass
class Approval:
    id: str
    variant_id: str
    decision: str  # "approve", "edit", "reject", "request_rewrite"
    reviewer_id: str
    feedback: Optional[str]
    payload_hash: str  # linked to exact variant payload hash
    reviewed_at: datetime = field(default_factory=utc_now)


@dataclass
class PublicationJob:
    id: str
    variant_id: str
    platform: str
    scheduled_at: datetime
    idempotency_key: str
    status: ContentStatus = ContentStatus.SCHEDULED
    attempt_count: int = 0
    max_retries: int = 3
    error_message: Optional[str] = None
    created_at: datetime = field(default_factory=utc_now)


@dataclass
class PublishedPost:
    id: str
    job_id: str
    external_post_id: str
    final_payload: Dict[str, Any]
    platform: str
    published_at: datetime
    permalink: str
    created_at: datetime = field(default_factory=utc_now)


@dataclass
class MetricSnapshot:
    id: str
    post_id: str
    observed_at: datetime
    impressions: int
    engagements: int
    clicks: int
    comments: int
    shares: int
    raw_payload: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentRun:
    id: str
    graph: str
    node: str
    trace_id: str
    input_ref: str
    output_ref: str
    prompt_version: str
    model: str
    cost: float = 0.0
    status: str = "completed"
    created_at: datetime = field(default_factory=utc_now)
