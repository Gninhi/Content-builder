import os
import unittest.mock
from datetime import datetime, timezone
import pytest

from infra.db.database import get_db_session
from infra.db.repository import ContentOpsRepository
from infra.db.models import PublicationJobModel, ContentVariantModel, PublishedPostModel
from packages.domain.state_machine import ContentStatus
from packages.connectors.social.exceptions import SocialPublishUnknownError
from packages.observability.tracing import ObservabilityTracer
from services.publisher.worker import PublisherWorker


@pytest.fixture(autouse=True)
def clean_env():
    old = os.environ.get("SECRET_VAULT_KEY")
    os.environ["SECRET_VAULT_KEY"] = "super-secret-vault-master-key-32b!"
    yield
    if old is not None:
        os.environ["SECRET_VAULT_KEY"] = old
    else:
        os.environ.pop("SECRET_VAULT_KEY", None)


def test_at_most_once_protocol_transitions_to_publish_unknown_on_timeout():
    """
    Validates At-Most-Once Protocol:
    When an unconfirmed network timeout or SocialPublishUnknownError occurs,
    the job and variant MUST transition to PUBLISH_UNKNOWN.
    The system must NOT retry blindly.
    """
    with get_db_session() as db:
        repo = ContentOpsRepository(db)
        ws = repo.create_workspace("At-Most-Once WS", "UTC", "owner_amo")
        brief = repo.create_brief(workspace_id=ws.id, objective="Obj", platform_targets=["linkedin"])
        pkg = repo.create_content_package(brief.id, 1)
        var = repo.add_variant(
            package_id=pkg.id,
            platform="linkedin",
            hook="Hook AMO",
            body="Reliable At-Most-Once publication test body with sufficient length.",
            cta="Share your thoughts",
            hashtags=["#Reliability", "#AI"],
            media_spec={}
        )
        var.status = ContentStatus.IN_REVIEW.value
        db.commit()

        repo.record_approval(variant_id=var.id, decision="approve", reviewer_id="human_editor_1", workspace_id=ws.id)
        job = repo.schedule_publication(workspace_id=ws.id, variant_id=var.id, scheduled_at=datetime.now(timezone.utc))

        worker = PublisherWorker(db)

        # Mock publisher raising SocialPublishUnknownError (simulating post-transmission timeout)
        mock_publisher = unittest.mock.MagicMock()
        mock_publisher.publish.side_effect = SocialPublishUnknownError("Network read timeout after dispatch", provider="linkedin")

        with unittest.mock.patch.object(worker, "resolve_publisher", return_value=mock_publisher):
            with unittest.mock.patch.object(ObservabilityTracer, "record_score") as mock_score:
                with pytest.raises(SocialPublishUnknownError):
                    worker.execute_job(job.id)

                # Verify Langfuse score for unknown status
                mock_score.assert_called_with(
                    name="publication_unknown",
                    value=0.5,
                    trace_id=unittest.mock.ANY,
                    comment=unittest.mock.ANY
                )

        # Verify state in database: MUST be PUBLISH_UNKNOWN
        db.refresh(job)
        db.refresh(var)
        assert job.status == ContentStatus.PUBLISH_UNKNOWN.value
        assert var.status == ContentStatus.PUBLISH_UNKNOWN.value
        assert "PUBLISH_UNKNOWN" in str(job.error_message)


def test_reconciliation_confirmed_published():
    """
    Validates manual or automated reconciliation when a PUBLISH_UNKNOWN post
    is confirmed to exist on the social platform.
    """
    with get_db_session() as db:
        repo = ContentOpsRepository(db)
        ws = repo.create_workspace("Reconciliation WS", "UTC", "owner_rec")
        brief = repo.create_brief(workspace_id=ws.id, objective="Obj", platform_targets=["linkedin"])
        pkg = repo.create_content_package(brief.id, 1)
        var = repo.add_variant(
            package_id=pkg.id,
            platform="linkedin",
            hook="Hook Rec",
            body="Reconciling indeterminate publication state with platform post lookup.",
            cta="Read more",
            hashtags=["#Engineering"],
            media_spec={}
        )

        var.status = ContentStatus.IN_REVIEW.value
        db.commit()
        repo.record_approval(variant_id=var.id, decision="approve", reviewer_id="reviewer", workspace_id=ws.id)
        job = repo.schedule_publication(workspace_id=ws.id, variant_id=var.id, scheduled_at=datetime.now(timezone.utc))

        # Manually transition to PUBLISH_UNKNOWN
        var.status = ContentStatus.PUBLISH_UNKNOWN.value
        job.status = ContentStatus.PUBLISH_UNKNOWN.value
        db.commit()

        worker = PublisherWorker(db)

        res = worker.reconcile_job(
            job_id=job.id,
            manual_resolution="CONFIRMED_PUBLISHED",
            external_post_id="urn:li:share:confirmed_12345",
            permalink="https://linkedin.com/posts/confirmed_12345"
        )

        assert res["status"] == "RECONCILED_PUBLISHED"
        assert res["external_post_id"] == "urn:li:share:confirmed_12345"

        db.refresh(job)
        db.refresh(var)
        assert job.status == ContentStatus.PUBLISHED.value
        assert var.status == ContentStatus.PUBLISHED.value

        post = db.query(PublishedPostModel).filter(PublishedPostModel.job_id == job.id).first()
        assert post is not None
        assert post.external_post_id == "urn:li:share:confirmed_12345"


def test_reconciliation_confirmed_failed():
    """
    Validates reconciliation when a PUBLISH_UNKNOWN post is confirmed NOT to have been published.
    """
    with get_db_session() as db:
        repo = ContentOpsRepository(db)
        ws = repo.create_workspace("Rec Fail WS", "UTC", "owner_fail")
        brief = repo.create_brief(workspace_id=ws.id, objective="Obj", platform_targets=["x"])
        pkg = repo.create_content_package(brief.id, 1)
        var = repo.add_variant(
            package_id=pkg.id,
            platform="x",
            hook="Hook X Fail",
            body="Reconciling confirmed failed tweet without duplicate creation.",
            cta="Follow",
            hashtags=["#X"],
            media_spec={}
        )

        var.status = ContentStatus.IN_REVIEW.value
        db.commit()
        repo.record_approval(variant_id=var.id, decision="approve", reviewer_id="reviewer", workspace_id=ws.id)
        job = repo.schedule_publication(workspace_id=ws.id, variant_id=var.id, scheduled_at=datetime.now(timezone.utc))

        # Manually transition to PUBLISH_UNKNOWN
        var.status = ContentStatus.PUBLISH_UNKNOWN.value
        job.status = ContentStatus.PUBLISH_UNKNOWN.value
        db.commit()

        worker = PublisherWorker(db)

        res = worker.reconcile_job(
            job_id=job.id,
            manual_resolution="CONFIRMED_FAILED"
        )

        assert res["status"] == "RECONCILED_FAILED"

        db.refresh(job)
        db.refresh(var)
        assert job.status == ContentStatus.PUBLISH_FAILED.value
        assert var.status == ContentStatus.PUBLISH_FAILED.value


def test_multi_platform_partial_failure_isolation():
    """
    Validates multi-platform publishing:
    When LinkedIn succeeds but X fails, LinkedIn must remain published
    and X must fail cleanly without creating duplicates on LinkedIn.
    """
    with get_db_session() as db:
        repo = ContentOpsRepository(db)
        ws = repo.create_workspace("Multi-Platform WS", "UTC", "owner_multi")
        brief = repo.create_brief(workspace_id=ws.id, objective="Obj", platform_targets=["linkedin", "x"])
        pkg = repo.create_content_package(brief.id, 1)

        # Variant 1: LinkedIn (Success)
        var_li = repo.add_variant(
            package_id=pkg.id,
            platform="linkedin",
            hook="LinkedIn Hook",
            body="Multi-platform publishing test variant for LinkedIn platform.",
            cta="Connect",
            hashtags=["#LinkedIn"],
            media_spec={}
        )
        var_li.status = ContentStatus.IN_REVIEW.value
        db.commit()
        repo.record_approval(variant_id=var_li.id, decision="approve", reviewer_id="editor_1", workspace_id=ws.id)

        # Variant 2: X (Failure)
        var_x = repo.add_variant(
            package_id=pkg.id,
            platform="x",
            hook="X Hook",
            body="Multi-platform publishing test variant for X platform.",
            cta="Follow",
            hashtags=["#X"],
            media_spec={}
        )
        var_x.status = ContentStatus.IN_REVIEW.value
        db.commit()
        repo.record_approval(variant_id=var_x.id, decision="approve", reviewer_id="editor_1", workspace_id=ws.id)

        job_li = repo.schedule_publication(workspace_id=ws.id, variant_id=var_li.id, scheduled_at=datetime.now(timezone.utc))
        job_x = repo.schedule_publication(workspace_id=ws.id, variant_id=var_x.id, scheduled_at=datetime.now(timezone.utc))
        db.commit()

        worker = PublisherWorker(db)

        # 1. Execute LinkedIn job (Success)
        res_li = worker.execute_job(job_li.id)
        assert res_li["status"] == "SUCCESS"

        # 2. Execute X job (Mock failure)
        mock_x_publisher = unittest.mock.MagicMock()
        mock_x_publisher.publish.side_effect = RuntimeError("X rate limit tier error")

        with unittest.mock.patch.object(worker, "resolve_publisher", return_value=mock_x_publisher):
            with pytest.raises(RuntimeError):
                worker.execute_job(job_x.id)

        db.refresh(job_li)
        db.refresh(var_li)
        db.refresh(job_x)
        db.refresh(var_x)

        # LinkedIn remains published
        assert job_li.status == ContentStatus.PUBLISHED.value
        assert var_li.status == ContentStatus.PUBLISHED.value

        # X failed independently
        assert job_x.status == ContentStatus.PUBLISH_FAILED.value
        assert var_x.status == ContentStatus.PUBLISH_FAILED.value
