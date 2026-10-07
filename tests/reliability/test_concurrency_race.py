import concurrent.futures
from datetime import datetime, timezone
from infra.db.database import get_db_session, SessionLocal
from infra.db.repository import ContentOpsRepository
from services.publisher.worker import PublisherWorker
from packages.domain.state_machine import ContentStatus
from infra.db.models import PublishedPostModel


def test_concurrent_workers_atomic_lock_prevents_double_publishing():
    """
    CONC-V2-01: Proves that two concurrent worker processes/threads attempting
    to publish the exact same job ID are mutually exclusive at the database level.
    Exactly one succeeds; the other is locked out.
    """
    with get_db_session() as db:
        repo = ContentOpsRepository(db)
        ws = repo.create_workspace("Race WS", "UTC", "owner_race")
        brief = repo.create_brief(workspace_id=ws.id, objective="Race Test", platform_targets=["linkedin"])
        pkg = repo.create_content_package(brief.id, 1)
        var = repo.add_variant(
            package_id=pkg.id,
            platform="linkedin",
            hook="Race Hook",
            body="Unique body content for race testing with adequate length.",
            cta="Race CTA",
            hashtags=["#race"]
        )
        var.status = ContentStatus.IN_REVIEW.value
        db.commit()
        repo.record_approval(variant_id=var.id, decision="approve", reviewer_id="reviewer_race", workspace_id=ws.id)
        job = repo.schedule_publication(workspace_id=ws.id, variant_id=var.id, scheduled_at=datetime.now(timezone.utc))
        job_id = job.id

    # Function executed by worker thread with independent DB session
    def run_worker():
        thread_db = SessionLocal()
        try:
            worker = PublisherWorker(thread_db)
            return worker.execute_job(job_id)
        except Exception as e:
            return {"error": str(e)}
        finally:
            thread_db.close()

    # Launch two workers concurrently
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        f1 = executor.submit(run_worker)
        f2 = executor.submit(run_worker)
        r1 = f1.result()
        r2 = f2.result()

    results = [r1, r2]
    successes = [r for r in results if r.get("status") == "SUCCESS"]
    blocked = [r for r in results if "error" in r or r.get("status") == "ALREADY_PUBLISHED"]

    assert len(successes) == 1, f"Expected exactly 1 successful publication, got: {results}"
    assert len(blocked) == 1, f"Expected exactly 1 blocked execution, got: {results}"

    # Verify database state has exactly 1 published post
    with get_db_session() as db:
        posts = db.query(PublishedPostModel).filter(PublishedPostModel.job_id == job_id).all()
        assert len(posts) == 1, f"Database corruption! Found {len(posts)} posts for job {job_id}"
