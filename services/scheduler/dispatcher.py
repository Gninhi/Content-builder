from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from infra.db.models import PublicationJobModel
from packages.domain.state_machine import ContentStatus
from services.publisher.worker import PublisherWorker


class SchedulerDispatcher:
    """
    Queue dispatcher polling for due publication jobs and executing them safely.
    """

    def __init__(self, db_session: Optional[Session] = None):
        self.db = db_session
        self.worker = PublisherWorker(db_session) if db_session else None

    def process_due_jobs(self) -> List[Dict[str, Any]]:
        if not self.db or not self.worker:
            raise ValueError("SchedulerDispatcher requires a valid db_session to process due jobs.")
        now = datetime.now(timezone.utc)
        due_jobs = (
            self.db.query(PublicationJobModel)
            .filter(
                PublicationJobModel.status == ContentStatus.SCHEDULED.value,
                PublicationJobModel.scheduled_at <= now,
                PublicationJobModel.attempt_count < PublicationJobModel.max_retries
            )
            .all()
        )

        results = []
        for job in due_jobs:
            try:
                res = self.worker.execute_job(str(job.id))
                results.append(res)
            except Exception as e:
                results.append({
                    "job_id": str(job.id),
                    "status": "FAILED",
                    "error": str(e)
                })
        return results

    async def run_daemon_loop(self, poll_interval_seconds: int = 15, stop_event: Any = None) -> None:
        """
        Continuous async background loop polling for due publication jobs.
        Safe for long-running service execution in FastAPI lifespan or standalone daemon.
        """
        import asyncio
        import logging
        from infra.db.database import get_db_session

        log = logging.getLogger("SchedulerDispatcher")
        log.info(f"Starting SchedulerDispatcher daemon loop (poll interval: {poll_interval_seconds}s)")
        while stop_event is None or not stop_event.is_set():
            with get_db_session() as db:
                dispatcher = SchedulerDispatcher(db)
                dispatcher.process_due_jobs()

            try:
                if stop_event:
                    await asyncio.wait_for(stop_event.wait(), timeout=poll_interval_seconds)
                else:
                    await asyncio.sleep(poll_interval_seconds)
            except asyncio.TimeoutError:
                pass


if __name__ == "__main__":
    import time
    import argparse
    import logging
    from infra.db.database import get_db_session

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    logger = logging.getLogger("SchedulerDispatcher")

    parser = argparse.ArgumentParser(description="Publication Scheduler Dispatcher CLI")
    parser.add_argument("--once", action="store_true", help="Process due publication jobs once and exit")
    parser.add_argument("--interval", type=int, default=30, help="Polling interval in seconds (default: 30)")
    args = parser.parse_args()

    if args.once:
        with get_db_session() as db:
            dispatcher = SchedulerDispatcher(db)
            res = dispatcher.process_due_jobs()
            print(f"Processed {len(res)} publication job(s): {res}")
    else:
        print(f"Starting Publication Dispatcher daemon (polling every {args.interval}s)... Press Ctrl+C to stop.")
        try:
            while True:
                with get_db_session() as db:
                    dispatcher = SchedulerDispatcher(db)
                    res = dispatcher.process_due_jobs()
                    if res:
                        logger.info(f"Executed {len(res)} due publication job(s): {res}")
                time.sleep(args.interval)
        except KeyboardInterrupt:
            print("\nPublication Dispatcher stopped by user.")
