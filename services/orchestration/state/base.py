from typing import TypedDict, List, Dict, Any, Optional
from packages.domain.state_machine import ContentStatus
from packages.resilience.circuit_breaker import CycleBudget


class IdeaResearchState(TypedDict, total=False):
    workspace_id: str
    topic_or_brief: str
    pillars: List[str]
    audience: List[str]
    target_count: int
    raw_sources: List[Dict[str, Any]]
    generated_ideas: List[Dict[str, Any]]
    enrichment_count: int
    enrichment_history: List[Dict[str, Any]]
    enable_agentic_enrichment: Optional[bool]
    resolved_llm: Optional[Dict[str, Any]]
    llm_override: Optional[Dict[str, Any]]
    demo: Optional[bool]
    strict_llm: Optional[bool]
    status: Optional[str]
    cached: Optional[bool]
    run_id: str
    errors: List[str]
    cycle_budget: Optional[CycleBudget]


class ContentProductionState(TypedDict, total=False):
    workspace_id: str
    brief_id: str
    objective: str
    angle: str
    target_platforms: List[str]
    brand_voice: str
    audience: List[str]
    prohibited_topics: List[str]
    cta_policy: Dict[str, Any]
    require_ai_disclosure: bool
    sources: List[Dict[str, Any]]
    requirements: Dict[str, Any]
    generated_variants: List[Dict[str, Any]]
    qa_results: Dict[str, Any]
    qa_attempt: int
    max_qa_retries: int
    qa_feedback_history: List[Dict[str, Any]]
    operation_mode: str
    target_variant_id: Optional[str]
    rewrite_instructions: Optional[str]
    previous_variant: Optional[Dict[str, Any]]
    resolved_llm: Optional[Dict[str, Any]]
    llm_override: Optional[Dict[str, Any]]
    strict_llm: Optional[bool]
    tags: List[str]
    status: ContentStatus
    run_id: str
    errors: List[str]
    cycle_budget: Optional[CycleBudget]


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
    cycle_budget: Optional[CycleBudget]
