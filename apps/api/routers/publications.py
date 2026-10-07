from fastapi import APIRouter, Depends, HTTPException
from packages.contracts.schemas import (
    PublicationScheduleRequest,
    PublicationJobResponse,
)
from packages.domain.state_machine import ContentStatus
from services.publisher.worker import PublisherWorker
from apps.api.dependencies import get_repository, UserContext, require_roles
from infra.db.repository import ContentOpsRepository
from infra.db.models import PublicationJobModel

router = APIRouter(tags=["Publications & Scheduling"])


@router.post("/v1/publications/schedule", response_model=PublicationJobResponse)
def schedule_publication(
    req: PublicationScheduleRequest,
    repo: ContentOpsRepository = Depends(get_repository),
    user: UserContext = Depends(require_roles("Owner", "Editor"))
):
    try:
        job = repo.schedule_publication(
            workspace_id=user.workspace_id,
            variant_id=req.variant_id,
            scheduled_at=req.scheduled_at
        )
        return PublicationJobResponse(
            id=job.id,
            variant_id=job.variant_id,
            platform=job.platform,
            scheduled_at=job.scheduled_at,
            idempotency_key=job.idempotency_key,
            status=ContentStatus(job.status),
            attempt_count=job.attempt_count,
            error_message=job.error_message
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/v1/publications/{job_id}/publish-now")
def publish_now(
    job_id: str,
    repo: ContentOpsRepository = Depends(get_repository),
    user: UserContext = Depends(require_roles("Owner"))
):
    job = repo.db.query(PublicationJobModel).filter(PublicationJobModel.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Publication job not found.")
    job_ws = job.variant.package.brief.workspace_id if (job.variant and job.variant.package and job.variant.package.brief) else None
    if job_ws != user.workspace_id and user.role.lower() != "owner":
        raise HTTPException(status_code=403, detail="Access to publication job in another workspace is forbidden.")

    worker = PublisherWorker(repo.db)
    try:
        result = worker.execute_job(job_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/v1/publications/{job_id}/cancel")
def cancel_publication_job(
    job_id: str,
    repo: ContentOpsRepository = Depends(get_repository),
    user: UserContext = Depends(require_roles("Owner", "Editor"))
):
    job = repo.db.query(PublicationJobModel).filter(PublicationJobModel.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Publication job not found.")
    job_ws = job.variant.package.brief.workspace_id if (job.variant and job.variant.package and job.variant.package.brief) else None
    if job_ws != user.workspace_id and user.role.lower() != "owner":
        raise HTTPException(status_code=403, detail="Access to publication job in another workspace is forbidden.")

    if job.status == ContentStatus.PUBLISHED.value:
        raise HTTPException(status_code=400, detail="Cannot cancel an already published post.")

    job.status = ContentStatus.ARCHIVED.value
    if job.variant:
        job.variant.status = ContentStatus.APPROVED.value
    repo.db.commit()

    return {"message": "Job successfully cancelled and reset to APPROVED state.", "job_id": job.id}
