from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from packages.domain.state_machine import ContentStatus


def get_utc_now():
    return datetime.now(timezone.utc)


# Workspace & Brand Profile
class WorkspaceCreate(BaseModel):
    name: str = Field(..., json_schema_extra={"example": "AI & Growth Workspace"})
    timezone: str = Field("UTC", json_schema_extra={"example": "Europe/Paris"})
    owner_id: str = Field("owner_1", json_schema_extra={"example": "owner_1"})


class WorkspaceResponse(BaseModel):
    id: str
    name: str
    timezone: str
    owner_id: str
    created_at: datetime


class BrandProfileCreate(BaseModel):
    workspace_id: str
    audience: List[str] = Field(..., json_schema_extra={"example": ["CTOs", "AI Engineers", "Tech Founders"]})
    voice: str = Field(..., json_schema_extra={"example": "Direct, expert, pragmatique, orienté retour d'expérience."})
    pillars: List[str] = Field(..., json_schema_extra={"example": ["Generative AI & LLMs", "Autonomous Agents", "Enterprise Automation"]})
    prohibited_topics: List[str] = Field(default_factory=list, json_schema_extra={"example": ["Crypto speculation", "Unverified gossip", "Direct competitor bashing"]})
    cta_policy: Dict[str, Any] = Field(default_factory=lambda: {
        "allowed_ctas": ["Visiter le dépôt GitHub", "S'inscrire à la newsletter", "Partager son avis en commentaire"],
        "max_per_post": 1
    })


class BrandProfileResponse(BaseModel):
    id: str
    workspace_id: str
    version: int
    audience: List[str]
    voice: str
    pillars: List[str]
    prohibited_topics: List[str]
    cta_policy: Dict[str, Any]
    created_at: datetime


# Sources & Provenance
class SourceIngestRequest(BaseModel):
    workspace_id: str
    type: str = Field("url", description="url, note, text, or rss")
    url: Optional[str] = None
    raw_text: Optional[str] = None
    title: Optional[str] = None
    author: Optional[str] = None


class SourceResponse(BaseModel):
    id: str
    workspace_id: str
    type: str
    canonical_url: Optional[str]
    raw_content_ref: str
    extracted_facts: List[Dict[str, Any]]
    provenance: Dict[str, Any]
    status: str
    created_at: datetime


# Ideation & Research (PRD Section 6)
class EvidenceItem(BaseModel):
    source_id: str
    claim: str
    confidence: float = 1.0


class IdeaItem(BaseModel):
    id: Optional[str] = None
    title: str
    angle: str
    target_audience: str
    recommended_formats: List[str] = Field(default_factory=lambda: ["linkedin", "x"])
    evidence: List[EvidenceItem]
    novelty_score: float = Field(..., ge=0.0, le=100.0)
    relevance_score: float = Field(..., ge=0.0, le=100.0)
    effort_score: float = Field(..., ge=0.0, le=100.0)
    total_score: Optional[float] = None
    priority: str = Field("high", description="high, medium, or low")
    risks: List[str] = Field(default_factory=list)
    signal_id: Optional[str] = None


class IdeaResearchRequest(BaseModel):
    workspace_id: Optional[str] = None
    topic_or_brief: str
    pillars: Optional[List[str]] = None
    audience: Optional[List[str]] = None
    target_count: int = Field(10, ge=1, le=25)
    signal_id: Optional[str] = None
    llm_override: Optional[Dict[str, Any]] = None


class IdeaResearchResponse(BaseModel):
    ideas: List[IdeaItem]
    sources_used: List[str]
    run_id: str


# Content Brief & Generation
class ContentBriefCreate(BaseModel):
    workspace_id: str
    idea_id: Optional[str] = None
    objective: str = Field(..., json_schema_extra={"example": "Positionner l'expertise sur les systèmes multi-agents"})
    campaign_id: Optional[str] = None
    platform_targets: List[str] = Field(default_factory=lambda: ["linkedin", "x"])
    requirements: Dict[str, Any] = Field(default_factory=dict)


class ClaimReference(BaseModel):
    claim: str
    source_id: str
    verified: bool = True
    confidence_score: float = 1.0


class ContentVariantCreate(BaseModel):
    platform: str
    hook: str
    body: str
    cta: str
    hashtags: List[str] = Field(default_factory=list)
    media_spec: Dict[str, Any] = Field(default_factory=dict)
    claims: List[ClaimReference] = Field(default_factory=list)


class ContentPackageResponse(BaseModel):
    id: str
    brief_id: str
    version: int
    status: ContentStatus
    qa_score: float
    model_metadata: Dict[str, Any]
    variants: List[Dict[str, Any]]
    created_at: datetime


# Quality Gate (PRD Section 6)
class QARuleCheck(BaseModel):
    rule_id: str
    name: str
    passed: bool
    details: str


class QAReviewResult(BaseModel):
    passed: bool
    qa_score: float = Field(..., ge=0.0, le=100.0)
    reasons: List[str] = Field(default_factory=list)
    checks: List[QARuleCheck] = Field(default_factory=list)
    claims_verified_count: int
    unsupported_claims: List[str] = Field(default_factory=list)


# Approvals (HITL)
class ApprovalRequest(BaseModel):
    decision: str = Field(..., description="approve, edit, reject, or request_rewrite")
    reviewer_id: str
    feedback: Optional[str] = None
    edited_payload: Optional[Dict[str, Any]] = None  # if decision == edit


class ApprovalResponse(BaseModel):
    id: str
    variant_id: str
    decision: str
    reviewer_id: str
    payload_hash: str
    status_result: ContentStatus
    reviewed_at: datetime


# Scheduling & Publication
class PublicationScheduleRequest(BaseModel):
    variant_id: str
    scheduled_at: datetime


class PublicationJobResponse(BaseModel):
    id: str
    variant_id: str
    platform: str
    scheduled_at: datetime
    idempotency_key: str
    status: ContentStatus
    attempt_count: int
    error_message: Optional[str] = None


class PublishedPostResponse(BaseModel):
    id: str
    job_id: str
    external_post_id: str
    platform: str
    published_at: datetime
    permalink: str
    receipt: Dict[str, Any]


# Analytics & Strategy Insights (PRD Section 3 & 6)
class MetricSnapshotCreate(BaseModel):
    post_id: str
    observed_at: datetime = Field(default_factory=get_utc_now)
    impressions: int = 0
    engagements: int = 0
    clicks: int = 0
    comments: int = 0
    shares: int = 0
    raw_payload: Dict[str, Any] = Field(default_factory=dict)


class StrategyInsight(BaseModel):
    pillar: str
    fact: str
    hypothesis: str
    confidence_level: float = Field(..., ge=0.0, le=1.0)
    recommended_action: str


class StrategyInsightsResponse(BaseModel):
    workspace_id: str
    generated_at: datetime
    insights: List[StrategyInsight]
    disclaimer: str = "Propositional learning: No automatic parameter changes without explicit user approval."
