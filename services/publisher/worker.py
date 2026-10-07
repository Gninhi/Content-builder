from typing import Dict, Any
from sqlalchemy.orm import Session
from infra.db.repository import ContentOpsRepository
from infra.db.models import PublicationJobModel, ContentVariantModel, ApprovalModel
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

        # 3. Transition to PUBLISHING using validated state machine
        ContentStateMachine.transition(ContentStatus(job.status), ContentStatus.PUBLISHING)
        ContentStateMachine.transition(ContentStatus(variant.status), ContentStatus.PUBLISHING)
        job.status = ContentStatus.PUBLISHING.value
        variant.status = ContentStatus.PUBLISHING.value
        job.attempt_count += 1
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
