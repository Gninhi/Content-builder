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
