import pytest
from datetime import datetime, timezone, timedelta
from packages.resilience.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerOpenException,
    CircuitState,
    retry_with_backoff,
    CycleBudget,
    BudgetExceededException,
)
from infra.db.database import get_db_session
from infra.db.repository import ContentOpsRepository
from packages.domain.state_machine import ContentStatus
from services.publisher.worker import PublisherWorker


def test_circuit_breaker_trips_after_failures_and_recovers():
    """
    RELIABILITY P0 (REL-03):
    Circuit breaker must trip to OPEN after threshold failures,
    prevent cascading calls, and test recovery in HALF_OPEN.
    """
    cb = CircuitBreaker(failure_threshold=2, recovery_timeout=0.2, name="test_cb")

    def failing_call():
        raise RuntimeError("Downstream 503 Service Unavailable")

    # 1. First failure -> still CLOSED
    with pytest.raises(RuntimeError):
        cb.execute(failing_call)
    assert cb.state == CircuitState.CLOSED
    assert cb.failure_count == 1

    # 2. Second failure -> trips to OPEN
    with pytest.raises(RuntimeError):
        cb.execute(failing_call)
    assert cb.state == CircuitState.OPEN

    # 3. Third call blocked immediately by circuit breaker without executing fn
    with pytest.raises(CircuitBreakerOpenException):
        cb.execute(failing_call)

    # 4. Wait for recovery timeout
    import time
    time.sleep(0.25)

    # State transitions to HALF_OPEN and succeeds -> resets to CLOSED
    def successful_call():
        return "OK"

    result = cb.execute(successful_call)
    assert result == "OK"
    assert cb.state == CircuitState.CLOSED
    assert cb.failure_count == 0


def test_retry_with_exponential_backoff_and_jitter():
    """
    RELIABILITY P0 (REL-03):
    Retry helper handles transient failures (429/5xx) with backoff.
    """
    attempts = 0

    def flaky_service():
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            raise ConnectionError("Transient network timeout (504)")
        return "Connected"

    res = retry_with_backoff(
        flaky_service,
        max_retries=3,
        initial_delay=0.01,
        max_delay=0.1,
        backoff_factor=1.5,
        jitter=True,
        retryable_exceptions=(ConnectionError,)
    )
    assert res == "Connected"
    assert attempts == 3


def test_cycle_budget_enforcement():
    """
    RELIABILITY P0:
    Enforces token and duration budgets per agent cycle.
    """
    budget = CycleBudget(max_tokens=1000, max_duration_seconds=10.0)
    budget.add_tokens(500)
    assert budget.used_tokens == 500

    # Exceeding token budget raises exception
    with pytest.raises(BudgetExceededException) as exc_info:
        budget.add_tokens(600)
    assert "token budget" in str(exc_info.value).lower()


def test_global_and_workspace_kill_switch_blocks_publishing(monkeypatch):
    """
    RELIABILITY P0 (SEC-03, REL-06):
    Global kill switch or workspace kill switch halts all publications immediately.
    """
    with get_db_session() as db:
        repo = ContentOpsRepository(db)
        ws = repo.create_workspace("KillSwitch WS", "UTC", "owner_ks")
        brief = repo.create_brief(workspace_id=ws.id, objective="Test Kill Switch", platform_targets=["linkedin"])
        pkg = repo.create_content_package(brief.id, 1)
        var = repo.add_variant(
            package_id=pkg.id,
            platform="linkedin",
            hook="Hook KS",
            body="Post intended for publish before emergency stop.",
            cta="CTA"
        )
        var.status = ContentStatus.IN_REVIEW.value
        db.commit()

        repo.record_approval(variant_id=var.id, decision="approve", reviewer_id="human_editor", workspace_id=ws.id)
        job = repo.schedule_publication(
            workspace_id=ws.id,
            variant_id=var.id,
            scheduled_at=datetime.now(timezone.utc)
        )

        worker = PublisherWorker(db)

        # 1. Test Global Kill Switch via environment variable
        monkeypatch.setenv("KILL_SWITCH_ENABLED", "true")
        with pytest.raises(ValueError) as exc:
            worker.execute_job(job.id)
        assert "kill switch" in str(exc.value).lower()

        # 2. Test Workspace-level kill switch in DB
        monkeypatch.delenv("KILL_SWITCH_ENABLED", raising=False)
        ws.kill_switch_enabled = True
        db.commit()

        # Reset job to SCHEDULED for test
        job.status = ContentStatus.SCHEDULED.value
        var.status = ContentStatus.SCHEDULED.value
        db.commit()

        with pytest.raises(ValueError) as exc2:
            worker.execute_job(job.id)
        assert "kill switch" in str(exc2.value).lower()


def test_workspace_publication_hourly_rate_cap(monkeypatch):
    """
    RELIABILITY P0:
    Hourly rate limit per workspace prevents runaway publication loops.
    """
    with get_db_session() as db:
        repo = ContentOpsRepository(db)
        ws = repo.create_workspace("RateCap WS", "UTC", "owner_rc")
        brief = repo.create_brief(workspace_id=ws.id, objective="Test Rate Cap", platform_targets=["linkedin"])
        pkg = repo.create_content_package(brief.id, 1)

        # Configure max 1 publication per hour
        monkeypatch.setenv("MAX_HOURLY_PUBLICATIONS", "1")

        # Create two variants with valid LinkedIn length (>10 chars)
        var1 = repo.add_variant(package_id=pkg.id, platform="linkedin", hook="H1", body="Publication LinkedIn de test valide 1.", cta="CTA")
        var2 = repo.add_variant(package_id=pkg.id, platform="linkedin", hook="H2", body="Publication LinkedIn de test valide 2.", cta="CTA")
        var1.status = ContentStatus.IN_REVIEW.value
        var2.status = ContentStatus.IN_REVIEW.value
        db.commit()

        repo.record_approval(variant_id=var1.id, decision="approve", reviewer_id="editor_1", workspace_id=ws.id)
        repo.record_approval(variant_id=var2.id, decision="approve", reviewer_id="editor_1", workspace_id=ws.id)

        now = datetime.now(timezone.utc)
        job1 = repo.schedule_publication(workspace_id=ws.id, variant_id=var1.id, scheduled_at=now)
        # Schedule second job outside the 15-minute collision window (+30 min)
        job2 = repo.schedule_publication(workspace_id=ws.id, variant_id=var2.id, scheduled_at=now + timedelta(minutes=30))

        worker = PublisherWorker(db)

        # First job succeeds
        res1 = worker.execute_job(job1.id)
        assert res1["status"] == "SUCCESS"

        # Second job hits the 1/hour rate ceiling
        with pytest.raises(ValueError) as exc:
            worker.execute_job(job2.id)
        assert "rate limit" in str(exc.value).lower()


def test_slot_collision_detection_within_buffer_window():
    """
    RELIABILITY P0:
    Prevents scheduling collisions (<15 min) for the same platform in the same workspace.
    """
    with get_db_session() as db:
        repo = ContentOpsRepository(db)
        ws = repo.create_workspace("Collision WS", "UTC", "owner_col")
        brief = repo.create_brief(workspace_id=ws.id, objective="Collision Test", platform_targets=["linkedin"])
        pkg = repo.create_content_package(brief.id, 1)

        var1 = repo.add_variant(package_id=pkg.id, platform="linkedin", hook="H1", body="B1", cta="CTA")
        var2 = repo.add_variant(package_id=pkg.id, platform="linkedin", hook="H2", body="B2", cta="CTA")
        var1.status = ContentStatus.IN_REVIEW.value
        var2.status = ContentStatus.IN_REVIEW.value
        db.commit()

        repo.record_approval(variant_id=var1.id, decision="approve", reviewer_id="editor", workspace_id=ws.id)
        repo.record_approval(variant_id=var2.id, decision="approve", reviewer_id="editor", workspace_id=ws.id)

        target_time = datetime.now(timezone.utc) + timedelta(hours=1)
        job1 = repo.schedule_publication(workspace_id=ws.id, variant_id=var1.id, scheduled_at=target_time)
        assert job1.status == ContentStatus.SCHEDULED.value

        # Attempting to schedule var2 only 5 minutes after var1 (< 15 min buffer) MUST fail
        collision_time = target_time + timedelta(minutes=5)
        with pytest.raises(ValueError) as exc:
            repo.schedule_publication(workspace_id=ws.id, variant_id=var2.id, scheduled_at=collision_time)

        assert "collision" in str(exc.value).lower()
