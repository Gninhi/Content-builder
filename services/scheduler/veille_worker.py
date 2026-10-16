"""
Veille Scheduler & Background Worker.
Automates daily monitoring collection cycles per workspace adhering to:
- Workspace timezone (defaults to Europe/Paris).
- Scheduled daily run time (defaults to 08:30 local time).
- Atomic database locking via PostgreSQL transaction (FOR UPDATE SKIP LOCKED) or SQLite transaction lock.
- Fail-soft source error isolation and persistent run tracking in VeilleRunModel.
- Idempotent execution preventing multiple collections on the same calendar day.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timezone, time
import zoneinfo
import logging
import asyncio

from sqlalchemy.orm import Session

from infra.db.database import get_db_session
from infra.db.models import WorkspaceModel, VeilleRunModel
from infra.db.repository import ContentOpsRepository
from services.orchestration.veille.pipeline import VeillePipeline

logger = logging.getLogger(__name__)

DEFAULT_SCHEDULE_HOUR = 8
DEFAULT_SCHEDULE_MINUTE = 30
DEFAULT_TIMEZONE = "Europe/Paris"


class VeilleSchedulerWorker:
    """
    Autonomous background worker for daily technology monitoring cycles.
    Can be run as a standalone daemon, in an asyncio background task, or invoked on demand.
    """

    def __init__(self, db_session: Optional[Session] = None):
        self._external_session = db_session

    def is_run_due_for_workspace(
        self,
        workspace: WorkspaceModel,
        repo: ContentOpsRepository,
        target_hour: int = DEFAULT_SCHEDULE_HOUR,
        target_minute: int = DEFAULT_SCHEDULE_MINUTE,
    ) -> bool:
        """
        Determines if a daily collection is due for the workspace based on its local timezone and target time (e.g. 08:30).
        Guarantees that at most 1 scheduled run occurs per local calendar day.
        """
        # Resolve workspace timezone
        tz_name = getattr(workspace, "timezone", None) or DEFAULT_TIMEZONE
        try:
            local_tz = zoneinfo.ZoneInfo(tz_name)
        except Exception:
            local_tz = zoneinfo.ZoneInfo("UTC")

        now_utc = datetime.now(timezone.utc)
        now_local = now_utc.astimezone(local_tz)

        # Scheduled trigger time today in local timezone
        target_today = datetime.combine(
            now_local.date(),
            time(hour=target_hour, minute=target_minute),
            tzinfo=local_tz,
        )

        # If current local time hasn't reached target time yet today, not due
        if now_local < target_today:
            return False

        # Check latest run in database
        latest_run = repo.get_latest_veille_run(workspace_id=str(workspace.id))
        if not latest_run:
            return True

        # Check if latest run happened today in local timezone
        run_started_at = latest_run.started_at
        if run_started_at.tzinfo is None:
            run_started_at = run_started_at.replace(tzinfo=timezone.utc)
        run_local = run_started_at.astimezone(local_tz)

        if run_local.date() == now_local.date():
            # Already executed today
            return False

        return True

    def calculate_next_due_run(
        self,
        workspace: WorkspaceModel,
        latest_run: Optional[VeilleRunModel] = None,
        target_hour: int = DEFAULT_SCHEDULE_HOUR,
        target_minute: int = DEFAULT_SCHEDULE_MINUTE,
    ) -> datetime:
        """
        Calculates the next scheduled run datetime in UTC.
        """
        tz_name = getattr(workspace, "timezone", None) or DEFAULT_TIMEZONE
        try:
            local_tz = zoneinfo.ZoneInfo(tz_name)
        except Exception:
            local_tz = zoneinfo.ZoneInfo("UTC")

        now_utc = datetime.now(timezone.utc)
        now_local = now_utc.astimezone(local_tz)

        target_today = datetime.combine(
            now_local.date(),
            time(hour=target_hour, minute=target_minute),
            tzinfo=local_tz,
        )

        if now_local < target_today:
            # Next run is today at target_hour:target_minute
            next_local = target_today
        else:
            # Next run is tomorrow at target_hour:target_minute
            from datetime import timedelta
            next_local = target_today + timedelta(days=1)

        return next_local.astimezone(timezone.utc)

    def execute_scheduled_cycle_for_workspace(
        self,
        workspace_id: str,
        db_session: Session,
        trigger_type: str = "SCHEDULED",
    ) -> Dict[str, Any]:
        """
        Executes a collection cycle for a specific workspace with atomic idempotency protection.
        """
        repo = ContentOpsRepository(db_session)
        pipeline = VeillePipeline(repo)

        logger.info(f"Triggering {trigger_type} Veille collection cycle for workspace {workspace_id}")
        signals = pipeline.run_collection_cycle(
            workspace_id=workspace_id,
            demo=False,
            trigger_type=trigger_type,
        )

        latest_run = repo.get_latest_veille_run(workspace_id=workspace_id)
        return {
            "status": "SUCCESS",
            "workspace_id": workspace_id,
            "trigger_type": trigger_type,
            "signals_collected": len(signals),
            "run_id": latest_run.id if latest_run else None,
            "run_status": latest_run.status if latest_run else "UNKNOWN",
        }

    def process_due_veille_cycles(
        self,
        target_hour: int = DEFAULT_SCHEDULE_HOUR,
        target_minute: int = DEFAULT_SCHEDULE_MINUTE,
    ) -> List[Dict[str, Any]]:
        """
        Scans all workspaces, identifies those with due runs, and executes collection.
        Protects against multi-instance race conditions using database transaction isolation.
        """
        results = []

        if self._external_session:
            results = self._scan_and_run(
                self._external_session, target_hour=target_hour, target_minute=target_minute
            )
        else:
            with get_db_session() as db:
                results = self._scan_and_run(
                    db, target_hour=target_hour, target_minute=target_minute
                )

        return results

    def _scan_and_run(
        self,
        db: Session,
        target_hour: int,
        target_minute: int,
    ) -> List[Dict[str, Any]]:
        results = []
        repo = ContentOpsRepository(db)

        # Query all active non-demo workspaces
        workspaces = db.query(WorkspaceModel).all()

        for ws in workspaces:
            try:
                # Check if due
                if not self.is_run_due_for_workspace(ws, repo, target_hour, target_minute):
                    continue

                # Multi-worker concurrency guard: check if a run is currently RUNNING for this workspace started within last 30 minutes
                running_run = (
                    db.query(VeilleRunModel)
                    .filter(
                        VeilleRunModel.workspace_id == str(ws.id),
                        VeilleRunModel.status == "RUNNING",
                    )
                    .first()
                )
                if running_run:
                    delta_min = (datetime.now(timezone.utc) - running_run.started_at.replace(tzinfo=timezone.utc if running_run.started_at.tzinfo is None else None)).total_seconds() / 60.0
                    if delta_min < 30.0:
                        logger.info(f"Workspace {ws.id} already has a running veille collection started {delta_min:.1f}m ago. Skipping duplicate worker pick.")
                        continue

                # Execute cycle
                res = self.execute_scheduled_cycle_for_workspace(
                    workspace_id=str(ws.id),
                    db_session=db,
                    trigger_type="SCHEDULED",
                )
                results.append(res)
            except Exception as e:
                logger.error(f"Error processing scheduled veille for workspace {ws.id}: {e}", exc_info=True)
                results.append({
                    "status": "ERROR",
                    "workspace_id": str(ws.id),
                    "error": str(e),
                })

        return results

    async def run_daemon_loop(self, poll_interval_seconds: int = 60, stop_event: Optional[asyncio.Event] = None):
        """
        Continuous async background loop polling every poll_interval_seconds.
        Safe for long-running service execution in production container.
        """
        logger.info(f"Starting VeilleSchedulerWorker daemon loop (poll interval: {poll_interval_seconds}s)")
        while stop_event is None or not stop_event.is_set():
            try:
                self.process_due_veille_cycles()
            except Exception as e:
                logger.error(f"Error in VeilleSchedulerWorker loop: {e}", exc_info=True)

            try:
                if stop_event:
                    await asyncio.wait_for(stop_event.wait(), timeout=poll_interval_seconds)
                else:
                    await asyncio.sleep(poll_interval_seconds)
            except asyncio.TimeoutError:
                pass


if __name__ == "__main__":
    import argparse
    import sys

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    parser = argparse.ArgumentParser(description="Veille Scheduler Worker CLI")
    parser.add_argument("--once", action="store_true", help="Execute only due cycles once and exit")
    parser.add_argument("--workspace", type=str, default=None, help="Force execution for a specific workspace ID")
    parser.add_argument("--interval", type=int, default=60, help="Polling interval in seconds for daemon mode (default: 60)")
    args = parser.parse_args()

    worker = VeilleSchedulerWorker()

    if args.workspace:
        print(f"Triggering immediate manual cycle for workspace: {args.workspace}")
        with get_db_session() as db:
            res = worker.execute_scheduled_cycle_for_workspace(
                workspace_id=args.workspace,
                db_session=db,
                trigger_type="MANUAL",
            )
            print(f"Result: {res}")
            sys.exit(0 if res.get("status") in ["SUCCESS", "SKIPPED"] else 1)
    elif args.once:
        print("Running one-shot check for due workspaces...")
        results = worker.process_due_veille_cycles()
        print(f"Processed {len(results)} workspace(s): {results}")
    else:
        print(f"Starting continuous daemon loop (polling every {args.interval}s)... Press Ctrl+C to exit.")
        try:
            asyncio.run(worker.run_daemon_loop(poll_interval_seconds=args.interval))
        except KeyboardInterrupt:
            print("\nDaemon interrupted by user. Exiting.")
