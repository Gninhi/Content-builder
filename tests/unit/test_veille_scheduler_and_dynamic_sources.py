"""
Unit & Integration tests for the VeilleSchedulerWorker, dynamic source polling,
fail-soft fault tolerance, timezone scheduling, and concurrency locking.
"""

from datetime import datetime, timezone, timedelta
import zoneinfo
from unittest.mock import MagicMock, patch

from infra.db.database import get_db_session
from infra.db.repository import ContentOpsRepository
from infra.db.models import WorkspaceModel, VeilleRunModel
from services.scheduler.veille_worker import (
    VeilleSchedulerWorker,
    DEFAULT_SCHEDULE_HOUR,
    DEFAULT_SCHEDULE_MINUTE,
)
from services.orchestration.veille.pipeline import parse_published_days_old, METRIC_REGEX


def test_parse_published_days_old():
    # ISO-8601 recent (yesterday)
    yesterday = datetime.now(timezone.utc) - timedelta(days=1)
    iso_str = yesterday.isoformat()
    assert parse_published_days_old(iso_str) == 1

    # RFC-2822 (3 days ago)
    three_days_ago = datetime.now(timezone.utc) - timedelta(days=3)
    rfc_str = three_days_ago.strftime("%a, %d %b %Y %H:%M:%S GMT")
    assert parse_published_days_old(rfc_str) == 3

    # Empty or unparseable defaults honestly to 14
    assert parse_published_days_old("") == 14
    assert parse_published_days_old(None) == 14
    assert parse_published_days_old("invalid-date-string") == 14


def test_metric_regex_extraction():
    assert bool(METRIC_REGEX.search("68% reduction in latency")) is True
    assert bool(METRIC_REGEX.search("Gain de 150k€ par an")) is True
    assert bool(METRIC_REGEX.search("Latence réduite à 850ms")) is True
    assert bool(METRIC_REGEX.search("Débit multiplié par 2.4")) is True
    # Non-metric text should not trigger
    assert bool(METRIC_REGEX.search("Une réunion a eu lieu en 2026 sans rapport.")) is False


def test_veille_scheduler_timezone_due_logic():
    with get_db_session() as db:
        repo = ContentOpsRepository(db)
        ws_id = "ws_test_scheduler_tz"
        repo.ensure_workspace(ws_id)
        ws = repo.get_workspace(ws_id)
        ws.timezone = "Europe/Paris"
        db.commit()

        worker = VeilleSchedulerWorker(db_session=db)

        # 1. Target time 00:00 (definitely reached today)
        is_due = worker.is_run_due_for_workspace(ws, repo, target_hour=0, target_minute=0)
        assert is_due is True

        # 2. Target time 23:59 (definitely not reached today)
        now_paris = datetime.now(timezone.utc).astimezone(zoneinfo.ZoneInfo("Europe/Paris"))
        if now_paris.hour < 23:
            assert worker.is_run_due_for_workspace(ws, repo, target_hour=23, target_minute=59) is False

        # 3. Next due run calculation
        next_due = worker.calculate_next_due_run(ws, target_hour=8, target_minute=30)
        assert next_due.tzinfo is not None
        assert next_due > datetime.now(timezone.utc) - timedelta(hours=24)


def test_veille_pipeline_fail_soft_source_isolation():
    """
    Verifies that if one source in the catalogue throws an error (e.g. HTTP 500 or timeout),
    the pipeline isolates the fault, marks the source as ERROR, and continues polling other sources.
    """
    with get_db_session() as db:
        repo = ContentOpsRepository(db)
        ws_id = "ws_test_fail_soft"
        repo.ensure_workspace(ws_id)

        # Clear existing sources for this test workspace
        existing = repo.list_veille_sources(ws_id)
        for e in existing:
            repo.delete_veille_source(e.id, ws_id)

        # Create 2 sources: 1 failing RSS feed, 1 working RSS feed
        failing_src = repo.create_veille_source(
            workspace_id=ws_id,
            name="Broken Source",
            url="https://invalid-non-existent-domain-404.com/feed.xml",
            axis="ia",
            trust_level="A",
            source_type="rss",
        )
        working_src = repo.create_veille_source(
            workspace_id=ws_id,
            name="Working Source",
            url="https://valid-domain.com/feed.xml",
            axis="ia",
            trust_level="A",
            source_type="rss",
        )

        from packages.tools.schemas import OfficialDataSignalItem, DataConnectorSource
        mock_signal = OfficialDataSignalItem(
            source_type=DataConnectorSource.RSS,
            identifier="item_1",
            title="SOTA AI Breakthrough with 45% gain",
            url="https://valid-domain.com/post/1",
            summary="This breakthrough improves throughput by 45% on enterprise workloads.",
            published_date=datetime.now(timezone.utc).isoformat(),
            metadata={},
        )

        def mock_fetch_rss(feed_url, max_results=3):
            if "invalid" in feed_url:
                raise ConnectionError("DNS resolution failed for broken source")
            return [mock_signal]

        from services.orchestration.veille.pipeline import VeillePipeline
        pipeline = VeillePipeline(repo)

        with patch.object(pipeline.connectors, "fetch_rss_feed", side_effect=mock_fetch_rss):
            signals = pipeline.run_collection_cycle(
                workspace_id=ws_id,
                axis="ia",
                demo=False,
                trigger_type="SCHEDULED",
            )

        # Verify fail-soft: collection succeeded with the working source signals
        assert len(signals) >= 1
        assert signals[0].title == "SOTA AI Breakthrough with 45% gain"

        # Verify failing source was marked ERROR with message in DB
        db.refresh(failing_src)
        assert failing_src.health_status == "ERROR"
        assert "DNS resolution failed" in (failing_src.error_message or "")

        # Verify working source was marked HEALTHY in DB
        db.refresh(working_src)
        assert working_src.health_status == "HEALTHY"
        assert working_src.last_polled_at is not None

        # Verify VeilleRunModel recorded both sources (1 contacted, 1 failed)
        latest_run = repo.get_latest_veille_run(ws_id)
        assert latest_run is not None
        assert latest_run.sources_failed == 1
        assert latest_run.signals_saved >= 1


def test_veille_scheduler_worker_concurrency_guard():
    """
    Verifies that two concurrent worker passes do not pick the same workspace twice
    if a run is already in progress.
    """
    with get_db_session() as db:
        repo = ContentOpsRepository(db)
        ws_id = "ws_test_concurrency"
        repo.ensure_workspace(ws_id)

        # Mark workspace run as currently RUNNING
        run = repo.create_veille_run(ws_id, trigger_type="SCHEDULED")
        assert run.status == "RUNNING"

        worker = VeilleSchedulerWorker(db_session=db)
        ws = repo.get_workspace(ws_id)
        ws.timezone = "Europe/Paris"
        db.commit()

        # Mock is_run_due_for_workspace to True for our workspace, and mock execute_scheduled_cycle
        with patch.object(worker, "is_run_due_for_workspace", return_value=True), \
             patch.object(worker, "execute_scheduled_cycle_for_workspace") as mock_exec, \
             patch.object(db, "query") as mock_query:

            # Make db.query(WorkspaceModel).all() return only [ws]
            query_mock = MagicMock()
            query_mock.all.return_value = [ws]
            query_mock.filter.return_value.first.return_value = run

            def query_side_effect(model):
                if model == WorkspaceModel:
                    return query_mock
                elif model == VeilleRunModel:
                    return query_mock
                return MagicMock()

            mock_query.side_effect = query_side_effect

            results = worker._scan_and_run(db, target_hour=DEFAULT_SCHEDULE_HOUR, target_minute=DEFAULT_SCHEDULE_MINUTE)
            # execute_scheduled_cycle must NOT be called because run.status is RUNNING
            mock_exec.assert_not_called()
            assert len(results) == 0

        # Once completed, status is updated
        repo.complete_veille_run(run.id, status="COMPLETED")
        assert repo.get_latest_veille_run(ws_id).status == "COMPLETED"

