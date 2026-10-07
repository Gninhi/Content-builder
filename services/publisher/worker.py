import os
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, List, cast
from sqlalchemy.orm import Session

from infra.db.repository import ContentOpsRepository
from infra.db.models import (
    PublicationJobModel,
    ContentVariantModel,
    ApprovalModel,
    PublishedPostModel,
    ContentPackageModel,
    ContentBriefModel,
    WorkspaceModel,
    ConnectedSocialAccountModel,
)
from packages.domain.state_machine import ContentStatus, ContentStateMachine
from packages.domain.idempotency import compute_payload_hash
from packages.connectors.social.base import SocialPublisher
from packages.connectors.social.linkedin import LinkedInSocialPublisher, LinkedInConnector
from packages.connectors.social.x_twitter import XSocialPublisher, XTwitterConnector
from packages.connectors.social.vault import EncryptedOAuthTokenVault
from packages.connectors.social.exceptions import (
    SocialPublishUnknownError,
    SocialAuthenticationError,
)
from packages.observability.tracing import ObservabilityTracer


class PublisherWorker:
    """
    Deterministic publishing worker adhering to PRD Section 6 & ADR 3:
    - Never uses an LLM for direct publishing.
    - Requires APPROVED status.
    - Requires verified cryptographic hash matching approval.
    - Enforces idempotency and logs audit receipt.
    - Implements At-Most-Once protocol: PUBLISHING committed before network dispatch,
      and transitions to PUBLISH_UNKNOWN on timeouts without blind automatic retries.
    - Correlates each publication with Langfuse trace and score telemetry.
    """

    def __init__(self, db_session: Session):
        self.repo = ContentOpsRepository(db_session)
        self.db = db_session
        self.vault = EncryptedOAuthTokenVault(db_session=db_session)
        # Fallback legacy connectors for testing/simulation
        self.linkedin_connector = LinkedInConnector(sandbox_mode=True)
        self.x_connector = XTwitterConnector(sandbox_mode=True)

    def resolve_publisher(self, platform: str, workspace_id: str) -> SocialPublisher:
        """
        Dynamically instantiates the appropriate SocialPublisher.
        Enforces sandbox mode unless LIVE_PUBLISHING_ENABLED is explicitly true.
        Resolves OAuth tokens securely from the encrypted database vault.
        """
        live_enabled = os.getenv("LIVE_PUBLISHING_ENABLED", "false").lower() == "true"
        global_sandbox = os.getenv("SOCIAL_SANDBOX_MODE", "true").lower() == "true"
        sandbox_mode = global_sandbox or not live_enabled

        platform_clean = platform.lower().strip()

        if sandbox_mode:
            if platform_clean == "linkedin":
                return LinkedInSocialPublisher(sandbox_mode=True)
            elif platform_clean in ("x", "twitter"):
                return XSocialPublisher(sandbox_mode=True)
            raise ValueError(f"Unsupported platform: {platform}")

        # Live publishing mode: load credentials from encrypted database vault
        account = (
            self.db.query(ConnectedSocialAccountModel)
            .filter(
                ConnectedSocialAccountModel.workspace_id == workspace_id,
                ConnectedSocialAccountModel.provider == platform_clean,
                ConnectedSocialAccountModel.status == "ACTIVE"
            )
            .first()
        )
        if not account:
            raise SocialAuthenticationError(
                f"No active connected social account found for platform '{platform}' in workspace '{workspace_id}'.",
                provider=platform
            )

        token_record = self.vault.get_token(workspace_id, platform_clean, str(account.account_id))
        if not token_record or not token_record.get("access_token"):
            raise SocialAuthenticationError(
                f"Failed to retrieve or decrypt valid access token for {platform} account '{account.account_id}'.",
                provider=platform
            )

        if platform_clean == "linkedin":
            return LinkedInSocialPublisher(
                access_token=str(token_record["access_token"]),
                token_expires_at=cast(Optional[datetime], account.expires_at),
                author_urn=str(account.account_id),
                sandbox_mode=False
            )
        elif platform_clean in ("x", "twitter"):
            def on_token_refreshed(new_access: str, new_refresh: str, new_exp: datetime):
                self.vault.store_token(
                    workspace_id=workspace_id,
                    provider="x",
                    account_id=str(account.account_id),
                    access_token=new_access,
                    refresh_token=new_refresh,
                    expires_at=new_exp,
                    scopes=cast(Optional[List[str]], account.scopes),
                    account_name=str(account.account_name)
                )

            return XSocialPublisher(
                access_token=str(token_record["access_token"]),
                refresh_token=token_record.get("refresh_token"),
                token_expires_at=cast(Optional[datetime], account.expires_at),
                on_token_refreshed=on_token_refreshed,
                sandbox_mode=False
            )

        raise ValueError(f"Unsupported platform: {platform}")

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
            setattr(job, "status", ContentStatus.PUBLISH_FAILED.value)
            setattr(job, "error_message", f"Precondition failed: Variant status is {variant.status}, expected APPROVED/SCHEDULED.")
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
            setattr(job, "status", ContentStatus.PUBLISH_FAILED.value)
            setattr(job, "error_message", "Security verification failed: Current payload hash does not match an approved record.")
            self.db.commit()
            raise ValueError(job.error_message)

        # Degraded mode safety lock: content generated via fallback requires explicit human reviewer approval
        is_degraded = getattr(variant, "degraded", False) or (variant.media_spec and variant.media_spec.get("degraded", False))
        if is_degraded:
            reviewer = (valid_approval.reviewer_id or "").strip().lower()
            if reviewer in ("system", "auto", "automated", ""):
                setattr(job, "status", ContentStatus.PUBLISH_FAILED.value)
                setattr(job, "error_message", "Degraded mode safety lock: Content generated via fallback requires explicit human reviewer approval before publication.")
                self.db.commit()
                raise ValueError(job.error_message)

        # Check global & workspace kill switch
        kill_switch = (
            os.getenv("KILL_SWITCH_ENABLED", "false").lower() in ("true", "1", "yes")
            or os.getenv("GLOBAL_KILL_SWITCH", "false").lower() in ("true", "1", "yes")
            or os.getenv("KILL_SWITCH_GLOBAL", "false").lower() in ("true", "1", "yes")
        )
        workspace = None
        ws_id = "ws_default"
        if variant.package and variant.package.brief:
            ws_id = str(variant.package.brief.workspace_id)
            workspace = self.db.query(WorkspaceModel).filter(WorkspaceModel.id == ws_id).first()

        if workspace and getattr(workspace, "kill_switch_enabled", False):
            kill_switch = True

        if kill_switch:
            setattr(job, "status", ContentStatus.PUBLISH_FAILED.value)
            setattr(job, "error_message", "Emergency Kill Switch is ACTIVE: All automated publications are halted.")
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
                setattr(job, "status", ContentStatus.PUBLISH_FAILED.value)
                setattr(job, "error_message", f"Publication rate limit reached for workspace '{workspace.id}': {recent_count}/{max_hourly} posts published in the last hour.")
                self.db.commit()
                raise ValueError(job.error_message)

        # 3. Atomic database-level lock transition to PUBLISHING (Committed BEFORE external network call)
        # Guarantees At-Most-Once mutual exclusion across concurrent workers
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
        setattr(variant, "status", ContentStatus.PUBLISHING.value)
        self.db.commit()

        trace_id = str(variant.package_id if variant.package else job.idempotency_key)

        # 4. Delegate to platform publisher
        try:
            publisher = self.resolve_publisher(str(variant.platform), ws_id)
            content_text = str(variant.body)
            pub_result = publisher.publish(
                content=content_text,
                media_urls=None,
                options={"job_id": job_id, "idempotency_key": str(job.idempotency_key)}
            )

            # 5. Record published post and mark SUCCESS
            post = self.repo.record_published_post(
                job_id=str(job.id),
                external_post_id=str(pub_result.platform_post_id),
                final_payload=current_payload,
                platform=str(variant.platform),
                permalink=str(pub_result.permalink_url or "")
            )

            ContentStateMachine.transition(ContentStatus.PUBLISHING, ContentStatus.PUBLISHED)
            setattr(job, "status", ContentStatus.PUBLISHED.value)
            setattr(variant, "status", ContentStatus.PUBLISHED.value)
            self.db.commit()

            # Record Langfuse score for successful publication
            ObservabilityTracer.record_score(
                name="publication_success",
                value=1.0,
                trace_id=trace_id,
                comment=f"Successfully published on {variant.platform} as {pub_result.platform_post_id}"
            )

            receipt = {
                "platform": str(variant.platform),
                "external_id": str(pub_result.platform_post_id),
                "permalink": str(pub_result.permalink_url or ""),
                "published_at": datetime.now(timezone.utc).isoformat(),
                "idempotency_key": str(job.idempotency_key),
                "status": "SUCCESS"
            }

            return {
                "status": "SUCCESS",
                "post_id": str(post.id),
                "external_id": str(post.external_post_id),
                "permalink": str(post.permalink),
                "receipt": receipt,
                "result": pub_result.model_dump()
            }

        except SocialPublishUnknownError as unk_exc:
            # At-Most-Once safety protocol: network timeout or unconfirmed status
            # NEVER retry automatically. Transition strictly to PUBLISH_UNKNOWN.
            ContentStateMachine.transition(ContentStatus.PUBLISHING, ContentStatus.PUBLISH_UNKNOWN)
            setattr(job, "status", ContentStatus.PUBLISH_UNKNOWN.value)
            setattr(variant, "status", ContentStatus.PUBLISH_UNKNOWN.value)
            setattr(job, "error_message", f"PUBLISH_UNKNOWN: {str(unk_exc)}")
            self.db.commit()

            ObservabilityTracer.record_score(
                name="publication_unknown",
                value=0.5,
                trace_id=trace_id,
                comment=f"PUBLISH_UNKNOWN encountered: {str(unk_exc)}. Manual reconciliation required."
            )
            raise unk_exc

        except Exception as exc:
            ContentStateMachine.transition(ContentStatus.PUBLISHING, ContentStatus.PUBLISH_FAILED)
            setattr(job, "status", ContentStatus.PUBLISH_FAILED.value)
            setattr(job, "error_message", str(exc))
            setattr(variant, "status", ContentStatus.PUBLISH_FAILED.value)
            self.db.commit()

            ObservabilityTracer.record_score(
                name="publication_failed",
                value=0.0,
                trace_id=trace_id,
                comment=f"Publication failed: {str(exc)}"
            )
            raise exc

    def reconcile_job(
        self,
        job_id: str,
        manual_resolution: str,
        external_post_id: Optional[str] = None,
        permalink: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Human or scheduled reconciliation for jobs stuck in PUBLISH_UNKNOWN.
        Transitions safely to either PUBLISHED or PUBLISH_FAILED.
        """
        job = self.db.query(PublicationJobModel).filter(PublicationJobModel.id == job_id).first()
        if not job:
            raise ValueError(f"Job '{job_id}' not found.")

        if job.status != ContentStatus.PUBLISH_UNKNOWN.value:
            raise ValueError(f"Job '{job_id}' is in status '{job.status}', expected PUBLISH_UNKNOWN for reconciliation.")

        variant: ContentVariantModel = job.variant
        resolution = manual_resolution.upper().strip()

        if resolution == "CONFIRMED_PUBLISHED":
            post_id = external_post_id or f"reconciled_{job.id}"
            link = permalink or f"https://reconciled.platform.com/posts/{post_id}"

            post = self.repo.record_published_post(
                job_id=str(job.id),
                external_post_id=post_id,
                final_payload={"reconciled": True},
                platform=str(variant.platform),
                permalink=link
            )

            ContentStateMachine.transition(ContentStatus.PUBLISH_UNKNOWN, ContentStatus.PUBLISHED)
            setattr(job, "status", ContentStatus.PUBLISHED.value)
            setattr(variant, "status", ContentStatus.PUBLISHED.value)
            self.db.commit()

            return {
                "status": "RECONCILED_PUBLISHED",
                "job_id": job.id,
                "external_post_id": post.external_post_id,
                "permalink": post.permalink
            }

        elif resolution == "CONFIRMED_FAILED":
            ContentStateMachine.transition(ContentStatus.PUBLISH_UNKNOWN, ContentStatus.PUBLISH_FAILED)
            setattr(job, "status", ContentStatus.PUBLISH_FAILED.value)
            setattr(variant, "status", ContentStatus.PUBLISH_FAILED.value)
            self.db.commit()

            return {
                "status": "RECONCILED_FAILED",
                "job_id": job.id
            }

        else:
            raise ValueError(f"Invalid manual resolution '{manual_resolution}'. Expected CONFIRMED_PUBLISHED or CONFIRMED_FAILED.")
