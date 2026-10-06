from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from datetime import datetime
import uuid

from infra.db.models import (
    WorkspaceModel,
    BrandProfileModel,
    ContentSourceModel,
    IdeaModel,
    ContentBriefModel,
    ContentPackageModel,
    ContentVariantModel,
    ApprovalModel,
    PublicationJobModel,
    PublishedPostModel,
    MetricSnapshotModel,
    AgentRunModel,
)
from packages.domain.state_machine import ContentStatus, ContentStateMachine
from packages.domain.idempotency import compute_payload_hash, compute_idempotency_key


class ContentOpsRepository:
    def __init__(self, db: Session):
        self.db = db

    # ----------------- Workspaces -----------------
    def create_workspace(self, name: str, timezone: str = "UTC", owner_id: str = "owner_1") -> WorkspaceModel:
        ws = WorkspaceModel(
            id=f"ws_{uuid.uuid4().hex[:12]}",
            name=name,
            timezone=timezone,
            owner_id=owner_id
        )
        self.db.add(ws)
        self.db.commit()
        self.db.refresh(ws)
        return ws

    def get_workspace(self, workspace_id: str) -> Optional[WorkspaceModel]:
        return self.db.query(WorkspaceModel).filter(WorkspaceModel.id == workspace_id).first()

    # ----------------- Brand Profiles -----------------
    def create_or_version_brand_profile(
        self,
        workspace_id: str,
        audience: List[str],
        voice: str,
        pillars: List[str],
        prohibited_topics: List[str],
        cta_policy: Dict[str, Any]
    ) -> BrandProfileModel:
        latest = (
            self.db.query(BrandProfileModel)
            .filter(BrandProfileModel.workspace_id == workspace_id)
            .order_by(BrandProfileModel.version.desc())
            .first()
        )
        next_version = (latest.version + 1) if latest else 1
        bp = BrandProfileModel(
            id=f"bp_{uuid.uuid4().hex[:12]}",
            workspace_id=workspace_id,
            version=next_version,
            audience=audience,
            voice=voice,
            pillars=pillars,
            prohibited_topics=prohibited_topics,
            cta_policy=cta_policy
        )
        self.db.add(bp)
        self.db.commit()
        self.db.refresh(bp)
        return bp

    def get_latest_brand_profile(self, workspace_id: str) -> Optional[BrandProfileModel]:
        return (
            self.db.query(BrandProfileModel)
            .filter(BrandProfileModel.workspace_id == workspace_id)
            .order_by(BrandProfileModel.version.desc())
            .first()
        )

    # ----------------- Content Sources -----------------
    def add_source(
        self,
        workspace_id: str,
        source_type: str,
        raw_content_ref: str,
        extracted_facts: List[Dict[str, Any]],
        provenance: Dict[str, Any],
        canonical_url: Optional[str] = None
    ) -> ContentSourceModel:
        # Deduplication check via canonical_url or content hash
        if canonical_url:
            existing = (
                self.db.query(ContentSourceModel)
                .filter(
                    ContentSourceModel.workspace_id == workspace_id,
                    ContentSourceModel.canonical_url == canonical_url
                )
                .first()
            )
            if existing:
                return existing

        source = ContentSourceModel(
            id=f"src_{uuid.uuid4().hex[:12]}",
            workspace_id=workspace_id,
            type=source_type,
            canonical_url=canonical_url,
            raw_content_ref=raw_content_ref,
            extracted_facts=extracted_facts,
            provenance=provenance,
            status="ingested"
        )
        self.db.add(source)
        self.db.commit()
        self.db.refresh(source)
        return source

    def list_sources(self, workspace_id: str) -> List[ContentSourceModel]:
        return self.db.query(ContentSourceModel).filter(ContentSourceModel.workspace_id == workspace_id).all()

    # ----------------- Ideas -----------------
    def save_idea(
        self,
        workspace_id: str,
        title: str,
        angle: str,
        pillar: str,
        audience: str,
        evidence_refs: List[Dict[str, Any]],
        novelty_score: float,
        relevance_score: float,
        effort_score: float,
        priority: str,
        risks: List[str]
    ) -> IdeaModel:
        total = round((novelty_score * 0.35) + (relevance_score * 0.45) - (effort_score * 0.20), 2)
        idea = IdeaModel(
            id=f"idea_{uuid.uuid4().hex[:12]}",
            workspace_id=workspace_id,
            title=title,
            angle=angle,
            pillar=pillar,
            audience=audience,
            evidence_refs=evidence_refs,
            novelty_score=novelty_score,
            relevance_score=relevance_score,
            effort_score=effort_score,
            total_score=total,
            priority=priority,
            risks=risks,
            status=ContentStatus.IDEA.value
        )
        self.db.add(idea)
        self.db.commit()
        self.db.refresh(idea)
        return idea

    def list_ideas(self, workspace_id: str, status: Optional[str] = None) -> List[IdeaModel]:
        q = self.db.query(IdeaModel).filter(IdeaModel.workspace_id == workspace_id)
        if status:
            q = q.filter(IdeaModel.status == status)
        return q.order_by(IdeaModel.total_score.desc()).all()

    # ----------------- Briefs & Packages -----------------
    def create_brief(
        self,
        workspace_id: str,
        objective: str,
        idea_id: Optional[str] = None,
        campaign_id: Optional[str] = None,
        platform_targets: Optional[List[str]] = None,
        requirements: Optional[Dict[str, Any]] = None
    ) -> ContentBriefModel:
        if idea_id:
            idea = self.db.query(IdeaModel).filter(IdeaModel.id == idea_id).first()
            if idea:
                idea.status = ContentStatus.BRIEFED.value

        brief = ContentBriefModel(
            id=f"brief_{uuid.uuid4().hex[:12]}",
            workspace_id=workspace_id,
            idea_id=idea_id,
            objective=objective,
            campaign_id=campaign_id,
            platform_targets=platform_targets or ["linkedin", "x"],
            requirements=requirements or {},
            status=ContentStatus.BRIEFED.value
        )
        self.db.add(brief)
        self.db.commit()
        self.db.refresh(brief)
        return brief

    def create_content_package(
        self,
        brief_id: str,
        version: int = 1,
        model_metadata: Optional[Dict[str, Any]] = None,
        qa_score: float = 0.0
    ) -> ContentPackageModel:
        package = ContentPackageModel(
            id=f"pkg_{uuid.uuid4().hex[:12]}",
            brief_id=brief_id,
            version=version,
            model_metadata=model_metadata or {},
            qa_score=qa_score,
            status=ContentStatus.DRAFT.value
        )
        self.db.add(package)
        self.db.commit()
        self.db.refresh(package)
        return package

    def add_variant(
        self,
        package_id: str,
        platform: str,
        hook: str,
        body: str,
        cta: str,
        hashtags: Optional[List[str]] = None,
        media_spec: Optional[Dict[str, Any]] = None,
        claims: Optional[List[Dict[str, Any]]] = None
    ) -> ContentVariantModel:
        raw_payload = {
            "platform": platform,
            "hook": hook,
            "body": body,
            "cta": cta,
            "hashtags": hashtags or [],
            "media_spec": media_spec or {},
        }
        p_hash = compute_payload_hash(raw_payload)

        variant = ContentVariantModel(
            id=f"var_{uuid.uuid4().hex[:12]}",
            package_id=package_id,
            platform=platform,
            hook=hook,
            body=body,
            cta=cta,
            hashtags=hashtags or [],
            media_spec=media_spec or {},
            claims=claims or [],
            payload_hash=p_hash,
            status=ContentStatus.DRAFT.value
        )
        self.db.add(variant)
        self.db.commit()
        self.db.refresh(variant)
        return variant

    # ----------------- Approvals (HITL) -----------------
    def record_approval(
        self,
        variant_id: str,
        decision: str,
        reviewer_id: str,
        feedback: Optional[str] = None,
        edited_payload: Optional[Dict[str, Any]] = None
    ) -> ApprovalModel:
        variant = self.db.query(ContentVariantModel).filter(ContentVariantModel.id == variant_id).first()
        if not variant:
            raise ValueError(f"Content variant '{variant_id}' not found.")

        current_status = ContentStatus(variant.status)

        if decision == "edit" and edited_payload:
            variant.hook = edited_payload.get("hook", variant.hook)
            variant.body = edited_payload.get("body", variant.body)
            variant.cta = edited_payload.get("cta", variant.cta)
            variant.hashtags = edited_payload.get("hashtags", variant.hashtags)
            variant.media_spec = edited_payload.get("media_spec", variant.media_spec)
            # Recompute payload hash
            raw = {
                "platform": variant.platform,
                "hook": variant.hook,
                "body": variant.body,
                "cta": variant.cta,
                "hashtags": variant.hashtags,
                "media_spec": variant.media_spec
            }
            variant.payload_hash = compute_payload_hash(raw)
            # Edited draft goes to IN_REVIEW or APPROVED
            decision = "approve"

        # Apply state transition
        if decision == "approve":
            next_status = ContentStateMachine.transition(current_status, ContentStatus.APPROVED)
        elif decision == "reject":
            next_status = ContentStateMachine.transition(current_status, ContentStatus.REJECTED)
        elif decision == "request_rewrite":
            next_status = ContentStateMachine.transition(current_status, ContentStatus.REWRITE_REQUESTED)
        else:
            raise ValueError(f"Unknown approval decision '{decision}'")

        variant.status = next_status.value

        approval = ApprovalModel(
            id=f"appr_{uuid.uuid4().hex[:12]}",
            variant_id=variant.id,
            decision=decision,
            reviewer_id=reviewer_id,
            feedback=feedback,
            payload_hash=variant.payload_hash,
            reviewed_at=datetime.utcnow()
        )
        self.db.add(approval)
        self.db.commit()
        self.db.refresh(approval)
        return approval

    # ----------------- Publication Jobs -----------------
    def schedule_publication(
        self,
        workspace_id: str,
        variant_id: str,
        scheduled_at: datetime
    ) -> PublicationJobModel:
        variant = self.db.query(ContentVariantModel).filter(ContentVariantModel.id == variant_id).first()
        if not variant:
            raise ValueError(f"Variant '{variant_id}' not found.")

        if variant.status not in (ContentStatus.APPROVED.value, ContentStatus.SCHEDULED.value):
            raise ValueError(f"Cannot schedule variant with status '{variant.status}'. Must be APPROVED.")

        # Verify an approval exists with the exact payload hash
        latest_approval = (
            self.db.query(ApprovalModel)
            .filter(
                ApprovalModel.variant_id == variant.id,
                ApprovalModel.decision == "approve",
                ApprovalModel.payload_hash == variant.payload_hash
            )
            .first()
        )
        if not latest_approval:
            raise ValueError("Integrity error: No valid approval found matching current payload hash.")

        idempotency_key = compute_idempotency_key(
            workspace_id=workspace_id,
            variant_id=variant.id,
            platform=variant.platform,
            scheduled_at=scheduled_at.isoformat(),
            version=1
        )

        # Check existing job
        existing_job = self.db.query(PublicationJobModel).filter(PublicationJobModel.idempotency_key == idempotency_key).first()
        if existing_job:
            return existing_job

        variant.status = ContentStatus.SCHEDULED.value

        job = PublicationJobModel(
            id=f"job_{uuid.uuid4().hex[:12]}",
            variant_id=variant.id,
            platform=variant.platform,
            scheduled_at=scheduled_at,
            idempotency_key=idempotency_key,
            status=ContentStatus.SCHEDULED.value
        )
        self.db.add(job)
        self.db.commit()
        self.db.refresh(job)
        return job

    def record_published_post(
        self,
        job_id: str,
        external_post_id: str,
        final_payload: Dict[str, Any],
        platform: str,
        permalink: str
    ) -> PublishedPostModel:
        job = self.db.query(PublicationJobModel).filter(PublicationJobModel.id == job_id).first()
        if job:
            job.status = ContentStatus.PUBLISHED.value
            if job.variant:
                job.variant.status = ContentStatus.PUBLISHED.value

        post = PublishedPostModel(
            id=f"post_{uuid.uuid4().hex[:12]}",
            job_id=job_id,
            external_post_id=external_post_id,
            final_payload=final_payload,
            platform=platform,
            published_at=datetime.utcnow(),
            permalink=permalink
        )
        self.db.add(post)
        self.db.commit()
        self.db.refresh(post)
        return post

    # ----------------- Metrics -----------------
    def record_metric_snapshot(
        self,
        post_id: str,
        impressions: int,
        engagements: int,
        clicks: int,
        comments: int,
        shares: int,
        raw_payload: Optional[Dict[str, Any]] = None
    ) -> MetricSnapshotModel:
        metric = MetricSnapshotModel(
            id=f"met_{uuid.uuid4().hex[:12]}",
            post_id=post_id,
            observed_at=datetime.utcnow(),
            impressions=impressions,
            engagements=engagements,
            clicks=clicks,
            comments=comments,
            shares=shares,
            raw_payload=raw_payload or {}
        )
        self.db.add(metric)
        self.db.commit()
        self.db.refresh(metric)
        return metric

    # ----------------- Agent Run Logging -----------------
    def log_agent_run(
        self,
        workspace_id: str,
        graph: str,
        node: str,
        trace_id: str,
        prompt_version: str,
        model: str,
        cost: float = 0.0,
        input_ref: Optional[str] = None,
        output_ref: Optional[str] = None,
        status: str = "completed"
    ) -> AgentRunModel:
        run = AgentRunModel(
            id=f"run_{uuid.uuid4().hex[:12]}",
            workspace_id=workspace_id,
            graph=graph,
            node=node,
            trace_id=trace_id,
            input_ref=input_ref,
            output_ref=output_ref,
            prompt_version=prompt_version,
            model=model,
            cost=cost,
            status=status
        )
        self.db.add(run)
        self.db.commit()
        self.db.refresh(run)
        return run
