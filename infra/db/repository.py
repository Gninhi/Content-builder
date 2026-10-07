from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone, timedelta
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
    ConnectedSocialAccountModel,
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
                setattr(idea, "status", ContentStatus.BRIEFED.value)

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
        claims: Optional[List[Dict[str, Any]]] = None,
        degraded: bool = False
    ) -> ContentVariantModel:
        m_spec = dict(media_spec or {})
        if degraded:
            m_spec["degraded"] = True

        raw_payload = {
            "platform": platform,
            "hook": hook,
            "body": body,
            "cta": cta,
            "hashtags": hashtags or [],
            "media_spec": m_spec,
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
            media_spec=m_spec,
            claims=claims or [],
            payload_hash=p_hash,
            degraded=degraded,
            status=ContentStatus.DRAFT.value
        )
        self.db.add(variant)
        self.db.commit()
        self.db.refresh(variant)
        return variant

    def record_approval(
        self,
        variant_id: str,
        decision: str,
        reviewer_id: str,
        workspace_id: Optional[str] = None,
        feedback: Optional[str] = None,
        edited_payload: Optional[Dict[str, Any]] = None
    ) -> ApprovalModel:
        query = self.db.query(ContentVariantModel)
        if workspace_id:
            query = (
                query.join(ContentPackageModel)
                .join(ContentBriefModel)
                .filter(ContentBriefModel.workspace_id == workspace_id)
            )
        variant = query.filter(ContentVariantModel.id == variant_id).first()
        if not variant:
            raise ValueError(f"Content variant '{variant_id}' not found or access denied for workspace.")

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
            setattr(variant, "payload_hash", compute_payload_hash(raw))
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

        setattr(variant, "status", next_status.value)

        approval = ApprovalModel(
            id=f"appr_{uuid.uuid4().hex[:12]}",
            variant_id=variant.id,
            decision=decision,
            reviewer_id=reviewer_id,
            feedback=feedback,
            payload_hash=variant.payload_hash,
            reviewed_at=datetime.now(timezone.utc)
        )
        self.db.add(approval)
        self.db.commit()
        self.db.refresh(approval)
        return approval

    def schedule_publication(
        self,
        workspace_id: str,
        variant_id: str,
        scheduled_at: datetime
    ) -> PublicationJobModel:
        variant = (
            self.db.query(ContentVariantModel)
            .join(ContentPackageModel)
            .join(ContentBriefModel)
            .filter(
                ContentVariantModel.id == variant_id,
                ContentBriefModel.workspace_id == workspace_id
            )
            .first()
        )
        if not variant:
            raise ValueError(f"Variant '{variant_id}' not found or access denied for workspace '{workspace_id}'.")

        if variant.status not in (ContentStatus.APPROVED.value, ContentStatus.SCHEDULED.value):
            raise ValueError(f"Cannot schedule variant with status '{variant.status}'. Must be APPROVED.")

        # Normalize scheduled_at to timezone-aware UTC
        if scheduled_at.tzinfo is None:
            scheduled_at = scheduled_at.replace(tzinfo=timezone.utc)
        else:
            scheduled_at = scheduled_at.astimezone(timezone.utc)

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
            variant_id=str(variant.id),
            platform=str(variant.platform),
            scheduled_at=scheduled_at.isoformat(),
            version=1
        )

        # Check existing job (idempotent)
        existing_job = self.db.query(PublicationJobModel).filter(PublicationJobModel.idempotency_key == idempotency_key).first()
        if existing_job:
            return existing_job

        # Slot collision detection: check other jobs in same workspace and platform within 15 minutes
        collision_buffer = timedelta(minutes=15)
        existing_scheduled = (
            self.db.query(PublicationJobModel)
            .join(ContentVariantModel, PublicationJobModel.variant_id == ContentVariantModel.id)
            .join(ContentPackageModel, ContentVariantModel.package_id == ContentPackageModel.id)
            .join(ContentBriefModel, ContentPackageModel.brief_id == ContentBriefModel.id)
            .filter(
                ContentBriefModel.workspace_id == workspace_id,
                PublicationJobModel.platform == variant.platform,
                PublicationJobModel.status.in_([ContentStatus.SCHEDULED.value, ContentStatus.PUBLISHING.value])
            )
            .all()
        )
        for prev_job in existing_scheduled:
            if prev_job.idempotency_key == idempotency_key or prev_job.variant_id == variant.id:
                continue
            prev_dt = prev_job.scheduled_at
            if prev_dt.tzinfo is None:
                prev_dt = prev_dt.replace(tzinfo=timezone.utc)
            if abs((scheduled_at - prev_dt).total_seconds()) < collision_buffer.total_seconds():
                raise ValueError(
                    f"Publication slot collision: Another post is already scheduled for platform '{variant.platform}' at {prev_dt} (collision buffer: 15 minutes)."
                )

        setattr(variant, "status", ContentStatus.SCHEDULED.value)

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
            setattr(job, "status", ContentStatus.PUBLISHED.value)
            if job.variant:
                setattr(job.variant, "status", ContentStatus.PUBLISHED.value)

        post = PublishedPostModel(
            id=f"post_{uuid.uuid4().hex[:12]}",
            job_id=job_id,
            external_post_id=external_post_id,
            final_payload=final_payload,
            platform=platform,
            published_at=datetime.now(timezone.utc),
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
            observed_at=datetime.now(timezone.utc),
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

    # ----------------- Workspace Isolated Queries -----------------
    def get_inbox_variants(self, workspace_id: str) -> List[ContentVariantModel]:
        return (
            self.db.query(ContentVariantModel)
            .join(ContentPackageModel)
            .join(ContentBriefModel)
            .filter(
                ContentBriefModel.workspace_id == workspace_id,
                ContentVariantModel.status == ContentStatus.IN_REVIEW.value
            )
            .all()
        )

    def get_editorial_calendar(self, workspace_id: str) -> Dict[str, Any]:
        scheduled_jobs = (
            self.db.query(PublicationJobModel)
            .join(ContentVariantModel)
            .join(ContentPackageModel)
            .join(ContentBriefModel)
            .filter(ContentBriefModel.workspace_id == workspace_id)
            .order_by(PublicationJobModel.scheduled_at.asc())
            .all()
        )
        published_posts = (
            self.db.query(PublishedPostModel)
            .join(PublicationJobModel)
            .join(ContentVariantModel)
            .join(ContentPackageModel)
            .join(ContentBriefModel)
            .filter(ContentBriefModel.workspace_id == workspace_id)
            .order_by(PublishedPostModel.published_at.desc())
            .all()
        )
        return {
            "scheduled": [
                {
                    "job_id": j.id,
                    "variant_id": j.variant_id,
                    "workspace_id": workspace_id,
                    "platform": j.platform,
                    "scheduled_at": j.scheduled_at,
                    "status": j.status,
                    "body_snippet": j.variant.body[:80] + "..." if j.variant else ""
                }
                for j in scheduled_jobs
            ],
            "published": [
                {
                    "post_id": p.id,
                    "job_id": p.job_id,
                    "workspace_id": workspace_id,
                    "platform": p.platform,
                    "published_at": p.published_at,
                    "external_post_id": p.external_post_id,
                    "url": p.permalink
                }
                for p in published_posts
            ]
        }

    # ----------------- Connected Social Accounts -----------------
    def store_connected_social_account(
        self,
        workspace_id: str,
        provider: str,
        account_id: str,
        account_name: str,
        encrypted_blob: str,
        key_id: str = "v1",
        scopes: Optional[List[str]] = None,
        expires_at: Optional[datetime] = None,
        status: str = "ACTIVE"
    ) -> ConnectedSocialAccountModel:
        account = (
            self.db.query(ConnectedSocialAccountModel)
            .filter(
                ConnectedSocialAccountModel.workspace_id == workspace_id,
                ConnectedSocialAccountModel.provider == provider.lower(),
                ConnectedSocialAccountModel.account_id == account_id
            )
            .first()
        )
        if not account:
            account = ConnectedSocialAccountModel(
                id=f"csa_{uuid.uuid4().hex[:12]}",
                workspace_id=workspace_id,
                provider=provider.lower(),
                account_id=account_id,
                account_name=account_name,
                encrypted_token_blob=encrypted_blob,
                key_id=key_id,
                scopes=scopes or [],
                expires_at=expires_at,
                status=status
            )
            self.db.add(account)
        else:
            setattr(account, "account_name", account_name)
            setattr(account, "encrypted_token_blob", encrypted_blob)
            setattr(account, "key_id", key_id)
            setattr(account, "scopes", scopes or [])
            setattr(account, "expires_at", expires_at)
            setattr(account, "status", status)
        self.db.commit()
        self.db.refresh(account)
        return account

    def get_connected_social_account(
        self,
        workspace_id: str,
        provider: str,
        account_id: str
    ) -> Optional[ConnectedSocialAccountModel]:
        return (
            self.db.query(ConnectedSocialAccountModel)
            .filter(
                ConnectedSocialAccountModel.workspace_id == workspace_id,
                ConnectedSocialAccountModel.provider == provider.lower(),
                ConnectedSocialAccountModel.account_id == account_id
            )
            .first()
        )

    def list_connected_social_accounts(
        self,
        workspace_id: str,
        provider: Optional[str] = None
    ) -> List[ConnectedSocialAccountModel]:
        q = self.db.query(ConnectedSocialAccountModel).filter(
            ConnectedSocialAccountModel.workspace_id == workspace_id
        )
        if provider:
            q = q.filter(ConnectedSocialAccountModel.provider == provider.lower())
        return q.all()

    def update_social_account_status(
        self,
        workspace_id: str,
        provider: str,
        account_id: str,
        status: str
    ) -> bool:
        account = self.get_connected_social_account(workspace_id, provider, account_id)
        if not account:
            return False
        setattr(account, "status", status)
        self.db.commit()
        return True

    def delete_connected_social_account(
        self,
        workspace_id: str,
        provider: str,
        account_id: str
    ) -> bool:
        account = self.get_connected_social_account(workspace_id, provider, account_id)
        if not account:
            return False
        self.db.delete(account)
        self.db.commit()
        return True


