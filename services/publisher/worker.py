import os
from datetime import datetime, timezone, timedelta
from typing import Dict, Any
from sqlalchemy.orm import Session
from infra.db.repository import ContentOpsRepository
from infra.db.models import (
    PublicationJobModel,
    ContentVariantModel,
    ApprovalModel,
    PublishedPostModel,
    ContentPackageModel,
    ContentBriefModel,
    WorkspaceModel
)
from packages.domain.state_machine import ContentStatus, ContentStateMachine
from packages.domain.idempotency import compute_payload_hash
from packages.connectors.social.linkedin import LinkedInConnector
from packages.connectors.social.x_twitter import XTwitterConnector


class PublisherWorker:
    """
    Deterministic publishing worker adhering to PRD Section 6 & ADR 3:
    - Never uses an LLM for direct publishing.
    - Requires APPROVED status.
    - Requires verified cryptographic hash matching approval.
    - Enforces idempotency and logs audit receipt.
    """

    def __init__(self, db_session: Session):
        self.repo = ContentOpsRepository(db_session)
        self.db = db_session
        self.linkedin_connector = LinkedInConnector(sandbox_mode=True)
        self.x_connector = XTwitterConnector(sandbox_mode=True)

    def execute_job(self, job_id: str) -> Dict[str, Any]:
        job = self.db.query(PublicationJobModel).filter(PublicationJobModel.id == job_id).first()
        if not job:
            raise ValueError(f"Publication job '{job_id}' not found.")

        # Idempotency check: if already published, return existing receipt
        if job.status == ContentStatus.PUBLISHED.value:
            existing_post = job.published_post
            return {
                "status": "ALREADY_PUBLISHED",
                "job_id": job.id,
                "external_post_id": existing_post.external_post_id if existing_post else None,
                "permalink": existing_post.permalink if existing_post else None
            }

        # Concurrency locking guard: avoid double processing of in-flight jobs
        if job.status == ContentStatus.PUBLISHING.value:
            raise RuntimeError(f"Concurrent execution detected: Job '{job_id}' is already in PUBLISHING status.")

        variant: ContentVariantModel = job.variant
        if not variant:
            raise ValueError(f"Associated variant not found for job {job_id}")

        # 1. Verify exact status
        if variant.status not in (ContentStatus.APPROVED.value, ContentStatus.SCHEDULED.value):
            job.status = ContentStatus.PUBLISH_FAILED.value
            job.error_message = f"Precondition failed: Variant status is {variant.status}, expected APPROVED/SCHEDULED."
            self.db.commit()
            raise ValueError(job.error_message)

        # 2. Verify payload hash against approval
        current_payload = {
            "platform": variant.platform,
            "hook": variant.hook,
            "body": variant.body,
            "cta": variant.cta,
            "hashtags": variant.hashtags,
            "media_spec": variant.media_spec
        }
        calculated_hash = compute_payload_hash(current_payload)
        
        valid_approval = (
            self.db.query(ApprovalModel)
            .filter(
                ApprovalModel.variant_id == variant.id,
                ApprovalModel.decision == "approve",
                ApprovalModel.payload_hash == calculated_hash
            )
            .first()
        )
        if not valid_approval:
            job.status = ContentStatus.PUBLISH_FAILED.value
            job.error_message = "Security verification failed: Current payload hash does not match an approved record."
            self.db.commit()
            raise ValueError(job.error_message)

        # Degraded mode safety lock: content generated via fallback requires explicit human reviewer approval
        is_degraded = getattr(variant, "degraded", False) or (variant.media_spec and variant.media_spec.get("degraded", False))
        if is_degraded:
            reviewer = (valid_approval.reviewer_id or "").strip().lower()
            if reviewer in ("system", "auto", "automated", ""):
                job.status = ContentStatus.PUBLISH_FAILED.value
                job.error_message = "Degraded mode safety lock: Content generated via fallback requires explicit human reviewer approval before publication."
                self.db.commit()
                raise ValueError(job.error_message)

        # Check global & workspace kill switch
        kill_switch = (
            os.getenv("KILL_SWITCH_ENABLED", "false").lower() in ("true", "1", "yes")
            or os.getenv("GLOBAL_KILL_SWITCH", "false").lower() in ("true", "1", "yes")
        )
        workspace = None
        if variant.package and variant.package.brief:
            ws_id = variant.package.brief.workspace_id
            workspace = self.db.query(WorkspaceModel).filter(WorkspaceModel.id == ws_id).first()

        if workspace and getattr(workspace, "kill_switch_enabled", False):
            kill_switch = True

        if kill_switch:
            job.status = ContentStatus.PUBLISH_FAILED.value
            job.error_message = "Emergency Kill Switch is ACTIVE: All automated publications are halted."
            self.db.commit()
            raise ValueError(job.error_message)

        # Enforce workspace publication rate ceiling
        if workspace:
            max_hourly = int(os.getenv("MAX_HOURLY_PUBLICATIONS", "10"))
            one_hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)
            recent_count = (
                self.db.query(PublishedPostModel)
                .join(PublicationJobModel, PublishedPostModel.job_id == PublicationJobModel.id)
                .join(ContentVariantModel, PublicationJobModel.variant_id == ContentVariantModel.id)
                .join(ContentPackageModel, ContentVariantModel.package_id == ContentPackageModel.id)
                .join(ContentBriefModel, ContentPackageModel.brief_id == ContentBriefModel.id)
                .filter(
                    ContentBriefModel.workspace_id == workspace.id,
                    PublishedPostModel.published_at >= one_hour_ago
                )
                .count()
            )
            if recent_count >= max_hourly:
                job.status = ContentStatus.PUBLISH_FAILED.value
                job.error_message = f"Publication rate limit reached for workspace '{workspace.id}': {recent_count}/{max_hourly} posts published in the last hour."
                self.db.commit()
                raise ValueError(job.error_message)

        # 3. Atomic database-level lock transition to PUBLISHING
        # Guarantees single-execution mutual exclusion across concurrent workers
        updated = (
            self.db.query(PublicationJobModel)
            .filter(
                PublicationJobModel.id == job_id,
                PublicationJobModel.status.in_([ContentStatus.APPROVED.value, ContentStatus.SCHEDULED.value])
            )
            .update(
                {
                    PublicationJobModel.status: ContentStatus.PUBLISHING.value,
                    PublicationJobModel.attempt_count: PublicationJobModel.attempt_count + 1
                },
                synchronize_session=False
            )
        )
        if updated == 0:
            self.db.rollback()
            self.db.refresh(job)
            if job.status == ContentStatus.PUBLISHED.value:
                existing_post = job.published_post
                return {
                    "status": "ALREADY_PUBLISHED",
                    "job_id": job.id,
                    "external_post_id": existing_post.external_post_id if existing_post else None,
                    "permalink": existing_post.permalink if existing_post else None
                }
            raise RuntimeError(f"Concurrent execution detected: Job '{job_id}' is already in {job.status} status.")

        ContentStateMachine.transition(ContentStatus(variant.status), ContentStatus.PUBLISHING)
        variant.status = ContentStatus.PUBLISHING.value
        self.db.commit()

        # 4. Delegate to platform connector
        try:
            if variant.platform == "linkedin":
                receipt = self.linkedin_connector.publish(current_payload, job.idempotency_key)
            elif variant.platform == "x":
                receipt = self.x_connector.publish(current_payload, job.idempotency_key)
            else:
                raise ValueError(f"Unsupported platform: {variant.platform}")

            # 5. Record published post and mark SUCCESS
            post = self.repo.record_published_post(
                job_id=job.id,
                external_post_id=receipt["external_id"],
                final_payload=current_payload,
                platform=variant.platform,
                permalink=receipt["permalink"]
            )

            ContentStateMachine.transition(ContentStatus.PUBLISHING, ContentStatus.PUBLISHED)
            job.status = ContentStatus.PUBLISHED.value
            variant.status = ContentStatus.PUBLISHED.value
            self.db.commit()

            return {
                "status": "SUCCESS",
                "post_id": post.id,
                "external_id": post.external_post_id,
                "permalink": post.permalink,
                "receipt": receipt
            }

        except Exception as exc:
            ContentStateMachine.transition(ContentStatus.PUBLISHING, ContentStatus.PUBLISH_FAILED)
            job.status = ContentStatus.PUBLISH_FAILED.value
            job.error_message = str(exc)
            variant.status = ContentStatus.PUBLISH_FAILED.value
            self.db.commit()
            raise exc
