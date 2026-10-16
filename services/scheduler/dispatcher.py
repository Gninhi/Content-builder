from datetime import datetime, timezone
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from infra.db.models import PublicationJobModel
from packages.domain.state_machine import ContentStatus
from services.publisher.worker import PublisherWorker


class SchedulerDispatcher:
    """
    Queue dispatcher polling for due publication jobs and executing them safely.
    """

    def __init__(self, db_session: Session):
        self.db = db_session
        self.worker = PublisherWorker(db_session)

    def process_due_jobs(self) -> List[Dict[str, Any]]:
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
