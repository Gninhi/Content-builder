from datetime import datetime, timezone
from unittest.mock import MagicMock, patch
from infra.db.database import get_db_session
from infra.db.repository import ContentOpsRepository
from infra.db.models import PublicationJobModel
from packages.domain.state_machine import ContentStatus
from packages.connectors.social.models import PublicationResult, PublicationStatus, SocialProvider
from services.publisher.worker import PublisherWorker


def test_db_failure_after_network_success_transitions_to_publish_unknown():
    """
    H9: If publisher.publish() succeeds on the network but subsequent DB commit fails,
    the job MUST transition to PUBLISH_UNKNOWN (never PUBLISH_FAILED) to prevent duplicate publishing.
    """
    now = datetime.now(timezone.utc)
    with get_db_session() as db:
        repo = ContentOpsRepository(db)
        ws = repo.create_workspace("DB Fail WS", "UTC", "owner_db_fail")
        brief = repo.create_brief(workspace_id=ws.id, objective="Test DB Fail Guard", platform_targets=["linkedin"])
        pkg = repo.create_content_package(brief.id, 1)
        var = repo.add_variant(pkg.id, "linkedin", "Hook DB", "Body DB content", "CTA", ["#DB"], {})
        var.status = ContentStatus.IN_REVIEW.value
        db.commit()
        repo.record_approval(var.id, "approve", "owner_db_fail", ws.id)
        job = repo.schedule_publication(ws.id, var.id, now)
        db.commit()
        job_id = job.id

    mock_pub_result = PublicationResult(
        platform_post_id="ext_post_12345",
        provider=SocialProvider.LINKEDIN,
        status=PublicationStatus.PUBLISHED,
        published_at=now,
        permalink_url="https://linkedin.com/posts/ext_post_12345",
        metadata={}
    )

    with get_db_session() as db:
        worker = PublisherWorker(db)
        mock_publisher = MagicMock()
        mock_publisher.publish.return_value = mock_pub_result

        with patch.object(worker, "resolve_publisher", return_value=mock_publisher), \
             patch.object(worker.repo, "record_published_post", side_effect=RuntimeError("DB Connection Lost")):
            try:
                worker.execute_job(job_id)
            except Exception:
                pass

    with get_db_session() as db:
        reloaded_job = db.query(PublicationJobModel).filter_by(id=job_id).first()
        # Must be PUBLISH_UNKNOWN, NEVER PUBLISH_FAILED!
        assert reloaded_job.status == ContentStatus.PUBLISH_UNKNOWN.value
