import pytest
from datetime import datetime, timezone
from packages.domain.state_machine import ContentStatus, ContentStateMachine, InvalidStateTransitionError
from infra.db.database import get_db_session
from infra.db.repository import ContentOpsRepository
from services.publisher.worker import PublisherWorker


def test_complete_state_machine_transitions_and_aliases():
    """
    Verifies valid lifecycle:
    draft -> pending_review -> approved -> scheduled -> publishing -> published | failed
    and verifies that illegal transitions are strictly rejected.
    """
    # 1. Standard forward flow
    state = ContentStatus.DRAFT
    state = ContentStateMachine.transition(state, ContentStatus.IN_REVIEW)
    assert state in (ContentStatus.IN_REVIEW, ContentStatus.PENDING_REVIEW)

    state = ContentStateMachine.transition(state, ContentStatus.APPROVED)
    assert state == ContentStatus.APPROVED

    state = ContentStateMachine.transition(state, ContentStatus.SCHEDULED)
    assert state == ContentStatus.SCHEDULED

    state = ContentStateMachine.transition(state, ContentStatus.PUBLISHING)
    assert state == ContentStatus.PUBLISHING

    state_pub = ContentStateMachine.transition(state, ContentStatus.PUBLISHED)
    assert state_pub == ContentStatus.PUBLISHED

    # 2. Failure path from publishing
    state_fail = ContentStateMachine.transition(ContentStatus.PUBLISHING, ContentStatus.PUBLISH_FAILED)
    assert state_fail in (ContentStatus.PUBLISH_FAILED, ContentStatus.FAILED)

    # 3. Strictly illegal transitions
    with pytest.raises(InvalidStateTransitionError):
        ContentStateMachine.transition(ContentStatus.DRAFT, ContentStatus.PUBLISHED)

    with pytest.raises(InvalidStateTransitionError):
        ContentStateMachine.transition(ContentStatus.IN_REVIEW, ContentStatus.PUBLISHED)

    with pytest.raises(InvalidStateTransitionError):
        ContentStateMachine.transition(ContentStatus.SCHEDULED, ContentStatus.DRAFT)


def test_publisher_worker_concurrency_lock():
    """
    Verifies that when a job is currently in PUBLISHING state,
    concurrent execution attempts are locked and rejected to prevent double-publishing.
    """
    with get_db_session() as db:
        repo = ContentOpsRepository(db)
        ws = repo.create_workspace("Lock Test WS", "UTC", "owner_lock")
        brief = repo.create_brief(workspace_id=ws.id, objective="Obj", platform_targets=["linkedin"])
        pkg = repo.create_content_package(brief.id, 1)
        var = repo.add_variant(
            package_id=pkg.id,
            platform="linkedin",
            hook="Hook lock",
            body="Body content for concurrency test with sufficient length.",
            cta="CTA",
            hashtags=["#test"]
        )
        var.status = ContentStatus.IN_REVIEW.value
        db.commit()
        repo.record_approval(variant_id=var.id, decision="approve", reviewer_id="reviewer", workspace_id=ws.id)
        job = repo.schedule_publication(workspace_id=ws.id, variant_id=var.id, scheduled_at=datetime.now(timezone.utc))

        # Set job status to PUBLISHING (simulating active in-flight worker)
        job.status = ContentStatus.PUBLISHING.value
        db.commit()

        worker = PublisherWorker(db)
        with pytest.raises(RuntimeError) as exc_info:
            worker.execute_job(job.id)

        assert "already in publishing" in str(exc_info.value).lower() or "verrou" in str(exc_info.value).lower()


def test_publisher_worker_idempotency_retry_never_duplicates():
    """
    Verifies that retrying an already completed job returns ALREADY_PUBLISHED
    with the exact same external post ID, never creating duplicate records.
    """
    with get_db_session() as db:
        repo = ContentOpsRepository(db)
        ws = repo.create_workspace("Idemp Test WS", "UTC", "owner_idemp")
        brief = repo.create_brief(workspace_id=ws.id, objective="Obj", platform_targets=["linkedin"])
        pkg = repo.create_content_package(brief.id, 1)
        var = repo.add_variant(
            package_id=pkg.id,
            platform="linkedin",
            hook="Hook idemp",
            body="Body content for idempotency retry testing with sufficient length.",
            cta="CTA",
            hashtags=["#idemp"]
        )
        var.status = ContentStatus.IN_REVIEW.value
        db.commit()
        repo.record_approval(variant_id=var.id, decision="approve", reviewer_id="reviewer", workspace_id=ws.id)
        job = repo.schedule_publication(workspace_id=ws.id, variant_id=var.id, scheduled_at=datetime.now(timezone.utc))

        worker = PublisherWorker(db)
        res1 = worker.execute_job(job.id)
        assert res1["status"] == "SUCCESS"
        first_post_id = res1["receipt"]["external_id"]

        # Retry identical job
        res2 = worker.execute_job(job.id)
        assert res2["status"] == "ALREADY_PUBLISHED"
        assert res2["external_post_id"] == first_post_id
