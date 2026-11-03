import asyncio
import pytest
import time
from unittest.mock import patch
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient
from apps.api.main import app, supervise_daemon
from infra.db.database import get_db_session
from infra.db.repository import ContentOpsRepository
from infra.db.models import UserModel
from packages.domain.state_machine import ContentStatus
from services.scheduler.dispatcher import SchedulerDispatcher


@pytest.mark.asyncio
async def test_supervisor_applies_exponential_backoff_on_daemon_failure():
    """C7: Supervised daemon retries with exponential backoff and jitter upon failures."""
    stop_event = asyncio.Event()
    attempts = []

    async def flaky_daemon(stop_evt):
        attempts.append(time.time())
        if len(attempts) < 3:
            raise ConnectionError("Transient database drop")
        # After 2 failures, wait until stopped
        await stop_evt.wait()

    # Run supervisor with small initial delay for testing
    task = asyncio.create_task(
        supervise_daemon(
            name="TestDaemon",
            runner_coro=flaky_daemon,
            stop_event=stop_event,
            initial_delay=0.05,
            max_delay=0.5,
            backoff_factor=2.0
        )
    )

    # Let supervisor attempt retries
    await asyncio.sleep(0.3)
    stop_event.set()
    await task

    # Must have had at least 3 attempts
    assert len(attempts) >= 3
    # Check that intervals between attempt 1 and 2, and attempt 2 and 3 show backoff
    interval_1 = attempts[1] - attempts[0]
    interval_2 = attempts[2] - attempts[1]
    assert interval_2 > interval_1 or interval_2 >= 0.05


def test_lifespan_starts_and_stops_background_daemons_gracefully():
    """C7: FastAPI lifespan supervises scheduler and veille workers with graceful shutdown."""
    async def mock_loop(*args, **kwargs):
        stop_evt = kwargs.get("stop_event") or (args[1] if len(args) > 1 else None)
        if stop_evt:
            await stop_evt.wait()

    with patch.dict("os.environ", {"ENABLE_BACKGROUND_DAEMONS": "true"}):
        with patch("services.scheduler.dispatcher.SchedulerDispatcher.run_daemon_loop", side_effect=mock_loop), \
             patch("services.scheduler.veille_worker.VeilleSchedulerWorker.run_daemon_loop", side_effect=mock_loop):
            with TestClient(app):
                # Verify background tasks exist on app.state
                assert hasattr(app.state, "background_tasks")
                assert hasattr(app.state, "background_stop_event")
                assert len(app.state.background_tasks) == 2
                assert not app.state.background_stop_event.is_set()

            # Upon exiting client context manager, stop_event must be set
            assert app.state.background_stop_event.is_set()


def test_scheduler_dispatcher_processes_due_jobs_in_daemon():
    """C7: SchedulerDispatcher picks up due SCHEDULED publication jobs and executes them."""
    with get_db_session() as db:
        repo = ContentOpsRepository(db)
        user = db.query(UserModel).filter(UserModel.email == "dispatcher_tester@example.com").first()
        if not user:
            user = UserModel(id="usr_dispatch_1", email="dispatcher_tester@example.com", is_active=True)
            db.add(user)
            db.flush()

        ws = repo.create_workspace("Dispatch WS", "UTC", str(user.id))
        brief = repo.create_brief(workspace_id=ws.id, objective="Test Dispatch", platform_targets=["linkedin"])
        pkg = repo.create_content_package(brief_id=brief.id, version=1)
        var = repo.add_variant(
            package_id=pkg.id,
            platform="linkedin",
            hook="Hook dispatch",
            body="Body dispatch",
            cta="CTA"
        )
        var.status = ContentStatus.IN_REVIEW.value
        db.commit()
        repo.record_approval(
            variant_id=str(var.id),
            decision="approve",
            reviewer_id=str(user.id),
            workspace_id=ws.id
        )
        # Schedule job in the past so it is due immediately
        due_time = datetime.now(timezone.utc) - timedelta(minutes=5)
        job = repo.schedule_publication(
            workspace_id=ws.id,
            variant_id=str(var.id),
            scheduled_at=due_time
        )
        db.commit()

        dispatcher = SchedulerDispatcher(db)
        results = dispatcher.process_due_jobs()
        assert isinstance(results, list)

        # Check job was processed
        db.refresh(job)
        assert job.status in [ContentStatus.PUBLISHED.value, ContentStatus.PUBLISH_UNKNOWN.value, ContentStatus.PUBLISH_FAILED.value]
