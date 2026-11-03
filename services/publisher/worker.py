import os
import logging
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
from packages.domain.rendering import render_publishable_text, extract_publishable_media
from packages.connectors.social.base import SocialPublisher, SocialPublisherRegistry
from packages.connectors.social.linkedin import LinkedInSocialPublisher, LinkedInConnector
from packages.connectors.social.x_twitter import XSocialPublisher, XTwitterConnector
from packages.connectors.social.vault import EncryptedOAuthTokenVault
from packages.connectors.social.exceptions import (
    SocialPublishUnknownError,
    SocialAuthenticationError,
)
from packages.observability.tracing import ObservabilityTracer

logger = logging.getLogger("PublisherWorker")


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
            try:
                publisher_cls = SocialPublisherRegistry.get_publisher_class(platform_clean)
                return publisher_cls(sandbox_mode=True)
            except ValueError:
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

    def _fail_precondition(self, job: PublicationJobModel, error_msg: str) -> None:
        """Helper to mark job as PUBLISH_FAILED, commit, and raise ValueError."""
        setattr(job, "status", ContentStatus.PUBLISH_FAILED.value)
        setattr(job, "error_message", error_msg)
        self.db.commit()
        raise ValueError(error_msg)

    def _check_idempotency_and_concurrency(self, job: PublicationJobModel) -> Optional[Dict[str, Any]]:
        """Check for completed publication or active concurrent publication."""
        if job.status == ContentStatus.PUBLISHED.value:
            existing_post = job.published_post
            return {
                "status": "ALREADY_PUBLISHED",
                "job_id": job.id,
                "external_post_id": existing_post.external_post_id if existing_post else None,
                "permalink": existing_post.permalink if existing_post else None
            }

        if job.status == ContentStatus.PUBLISHING.value:
            raise RuntimeError(f"Concurrent execution detected: Job '{job.id}' is already in PUBLISHING status.")

        return None

    def _verify_preconditions(self, job: PublicationJobModel, variant: ContentVariantModel) -> Dict[str, Any]:
        """Verify status, payload hash integrity, and degraded mode safety guard."""
        if variant.status not in (ContentStatus.APPROVED.value, ContentStatus.SCHEDULED.value):
            self._fail_precondition(job, f"Precondition failed: Variant status is {variant.status}, expected APPROVED/SCHEDULED.")

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
            self._fail_precondition(job, "Security verification failed: Current payload hash does not match an approved record.")

        # Degraded mode safety lock: fallback generated content requires explicit human reviewer approval
        is_degraded = getattr(variant, "degraded", False) or bool(variant.media_spec and variant.media_spec.get("degraded", False))
        if is_degraded:
            reviewer = (valid_approval.reviewer_id or "").strip().lower()
            if reviewer in ("system", "auto", "automated", ""):
                self._fail_precondition(job, "Degraded mode safety lock: Content generated via fallback requires explicit human reviewer approval before publication.")

        return current_payload

    def _verify_guards_and_limits(self, job: PublicationJobModel, variant: ContentVariantModel) -> str:
        """Verify kill switch and rate limits."""
        if not (variant.package and variant.package.brief and variant.package.brief.workspace_id):
            self._fail_precondition(job, f"Integrity error: Variant '{variant.id}' has no associated brief/workspace hierarchy.")

        ws_id = str(variant.package.brief.workspace_id)
        workspace = self.db.query(WorkspaceModel).filter(WorkspaceModel.id == ws_id).first()

        kill_switch = (
            os.getenv("KILL_SWITCH_ENABLED", "false").lower() in ("true", "1", "yes")
            or os.getenv("GLOBAL_KILL_SWITCH", "false").lower() in ("true", "1", "yes")
            or os.getenv("KILL_SWITCH_GLOBAL", "false").lower() in ("true", "1", "yes")
            or bool(workspace and getattr(workspace, "kill_switch_enabled", False))
        )

        if kill_switch:
            self._fail_precondition(job, "Emergency Kill Switch is ACTIVE: All automated publications are halted.")

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
                self._fail_precondition(job, f"Publication rate limit reached for workspace '{workspace.id}': {recent_count}/{max_hourly} posts published in the last hour.")

        return ws_id

    def _acquire_publishing_lock(self, job: PublicationJobModel, variant: ContentVariantModel) -> Optional[Dict[str, Any]]:
        """Atomic database-level lock transition to PUBLISHING before network call."""
        updated = (
            self.db.query(PublicationJobModel)
            .filter(
                PublicationJobModel.id == job.id,
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
            raise RuntimeError(f"Concurrent execution detected: Job '{job.id}' is already in {job.status} status.")

        ContentStateMachine.transition(ContentStatus(variant.status), ContentStatus.PUBLISHING)
        setattr(variant, "status", ContentStatus.PUBLISHING.value)
        self.db.commit()
        return None

    def _dispatch_publish(self, job: PublicationJobModel, variant: ContentVariantModel, ws_id: str) -> Any:
        """Instantiate connector and dispatch publication over network."""
        publisher = self.resolve_publisher(str(variant.platform), ws_id)
        content_text = render_publishable_text(variant)
        media_urls = extract_publishable_media(variant)
        return publisher.publish(
            content=content_text,
            media_urls=media_urls or None,
            options={"job_id": job.id, "idempotency_key": str(job.idempotency_key)}
        )

    def _record_success(
        self,
        job: PublicationJobModel,
        variant: ContentVariantModel,
        pub_result: Any,
        current_payload: Dict[str, Any],
        trace_id: str
    ) -> Dict[str, Any]:
        """Persist published post record, update state machine to PUBLISHED, and emit metrics."""
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

    def _handle_publish_unknown(
        self,
        job: PublicationJobModel,
        variant: ContentVariantModel,
        unk_exc: SocialPublishUnknownError,
        trace_id: str
    ) -> None:
        """Handle indeterminate publish status with At-Most-Once safety protocol."""
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

    def _handle_publish_error(
        self,
        job: PublicationJobModel,
        variant: Optional[ContentVariantModel],
        exc: Exception,
        pub_result: Any,
        trace_id: str
    ) -> None:
        """Handle publishing exceptions, treating post-network DB failures as PUBLISH_UNKNOWN."""
        if pub_result is not None:
            platform_str = str(variant.platform) if variant else "unknown"
            logger.error(
                f"CRITICAL: Post succeeded on external network ({platform_str} id={pub_result.platform_post_id}), "
                f"but database post-processing/commit failed: {exc}. Transitioning to PUBLISH_UNKNOWN."
            )
            try:
                self.db.rollback()
                ContentStateMachine.transition(ContentStatus.PUBLISHING, ContentStatus.PUBLISH_UNKNOWN)
                job.status = ContentStatus.PUBLISH_UNKNOWN.value
                job.error_message = (
                    f"PUBLISH_UNKNOWN: Post succeeded externally (id={pub_result.platform_post_id}), "
                    f"but local DB transaction failed: {str(exc)}"
                )
                if variant:
                    variant.status = ContentStatus.PUBLISH_UNKNOWN.value
                self.db.commit()
            except Exception as rollback_err:
                logger.critical(f"FATAL: Database error during emergency rollback to PUBLISH_UNKNOWN: {rollback_err}")

            ObservabilityTracer.record_score(
                name="publication_unknown",
                value=0.5,
                trace_id=trace_id,
                comment=f"PUBLISH_UNKNOWN: Network succeeded (id={pub_result.platform_post_id}) but DB failed: {str(exc)}"
            )
            raise SocialPublishUnknownError(
                f"Post succeeded on {platform_str} (id={pub_result.platform_post_id}) but local database transaction failed: {str(exc)}"
            )

        ContentStateMachine.transition(ContentStatus.PUBLISHING, ContentStatus.PUBLISH_FAILED)
        setattr(job, "status", ContentStatus.PUBLISH_FAILED.value)
        setattr(job, "error_message", str(exc))
        if variant:
            setattr(variant, "status", ContentStatus.PUBLISH_FAILED.value)
        self.db.commit()

        ObservabilityTracer.record_score(
            name="publication_failed",
            value=0.0,
            trace_id=trace_id,
            comment=f"Publication failed: {str(exc)}"
        )

    def execute_job(self, job_id: str) -> Dict[str, Any]:
        """
        Execute publishing job adhering strictly to At-Most-Once and zero-trust preconditions.
        """
        job = self.db.query(PublicationJobModel).filter(PublicationJobModel.id == job_id).first()
        if not job:
            raise ValueError(f"Publication job '{job_id}' not found.")

        early_result = self._check_idempotency_and_concurrency(job)
        if early_result:
            return early_result

        variant: ContentVariantModel = job.variant
        if not variant:
            raise ValueError(f"Associated variant not found for job {job_id}")

        current_payload = self._verify_preconditions(job, variant)
        ws_id = self._verify_guards_and_limits(job, variant)

        lock_early_result = self._acquire_publishing_lock(job, variant)
        if lock_early_result:
            return lock_early_result

        trace_id = str(variant.package_id if variant.package else job.idempotency_key)
        pub_result = None

        try:
            pub_result = self._dispatch_publish(job, variant, ws_id)
            return self._record_success(job, variant, pub_result, current_payload, trace_id)
        except SocialPublishUnknownError as unk_exc:
            self._handle_publish_unknown(job, variant, unk_exc, trace_id)
            raise unk_exc
        except Exception as exc:
            self._handle_publish_error(job, variant, exc, pub_result, trace_id)
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
            if not external_post_id:
                raise ValueError("Reconciliation as CONFIRMED_PUBLISHED requires providing a valid external_post_id.")
            post_id = external_post_id
            link = permalink or f"https://{variant.platform}.com/posts/{post_id}"

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
