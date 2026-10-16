from typing import TypedDict, List, Dict, Any, Optional
from packages.domain.state_machine import ContentStatus


class IdeaResearchState(TypedDict):
    workspace_id: str
    topic_or_brief: str
    pillars: List[str]
    audience: List[str]
    target_count: int
    raw_sources: List[Dict[str, Any]]
    generated_ideas: List[Dict[str, Any]]
    run_id: str
    errors: List[str]


class ContentProductionState(TypedDict):
    workspace_id: str
    brief_id: str
    objective: str
    angle: str
    target_platforms: List[str]
    brand_voice: str
    prohibited_topics: List[str]
    cta_policy: Dict[str, Any]
    sources: List[Dict[str, Any]]
    requirements: Dict[str, Any]
    generated_variants: List[Dict[str, Any]]
    qa_results: Dict[str, Any]
    status: ContentStatus
    run_id: str
    errors: List[str]


class ApprovalState(TypedDict):
    variant_id: str
    package_id: str
    payload: Dict[str, Any]
    payload_hash: str
    decision: Optional[str]  # approve, edit, reject, request_rewrite
    reviewer_id: Optional[str]
    feedback: Optional[str]
    status: ContentStatus


class SchedulingState(TypedDict):
    workspace_id: str
    variant_id: str
    platform: str
    scheduled_at: str
    idempotency_key: str
    status: ContentStatus
    job_id: Optional[str]
    error: Optional[str]


class PublishingState(TypedDict):
    job_id: str
    variant_id: str
    platform: str
    payload: Dict[str, Any]
    idempotency_key: str
    approval_hash: str
    status: ContentStatus
    receipt: Optional[Dict[str, Any]]
    error: Optional[str]


class AnalyticsState(TypedDict):
    post_id: str
    platform: str
    time_window: str
    raw_metrics: Dict[str, Any]
    normalized_metrics: Dict[str, Any]
    status: str


class StrategyInsightsState(TypedDict):
    workspace_id: str
    pillars: List[str]
    metric_snapshots: List[Dict[str, Any]]
    hypotheses: List[Dict[str, Any]]
    recommendations: List[Dict[str, Any]]
    confidence_levels: Dict[str, float]
    status: str
