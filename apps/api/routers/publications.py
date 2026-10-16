from typing import cast
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from packages.contracts.schemas import (
    PublicationScheduleRequest,
    PublicationJobResponse,
    PublicationReconcileRequest,
)
from packages.domain.state_machine import ContentStatus, ContentStateMachine
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
            id=str(job.id),
            variant_id=str(job.variant_id),
            platform=str(job.platform),
            scheduled_at=cast(datetime, job.scheduled_at),
            idempotency_key=str(job.idempotency_key),
            status=ContentStatus(str(job.status)),
            attempt_count=int(job.attempt_count) if job.attempt_count is not None else 0,
            error_message=str(job.error_message) if job.error_message else None
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
    if job_ws != user.workspace_id:
        raise HTTPException(status_code=404, detail="Publication job not found.")

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
    if job_ws != user.workspace_id:
        raise HTTPException(status_code=404, detail="Publication job not found.")

    current_status = ContentStatus.parse(str(job.status))
    if current_status == ContentStatus.PUBLISHED:
        raise HTTPException(status_code=400, detail="Cannot cancel an already published post.")
    if current_status in (ContentStatus.PUBLISHING, ContentStatus.PUBLISH_UNKNOWN):
        raise HTTPException(
            status_code=400,
            detail=f"Cannot cancel publication job in state '{current_status.value}'. Job is currently publishing or in indeterminate state; reconcile first."
        )

    # State machine transition enforcement
    ContentStateMachine.transition(current_status, ContentStatus.ARCHIVED)
    job.status = ContentStatus.ARCHIVED.value

    if job.variant:
        var_status = ContentStatus.parse(str(job.variant.status))
        ContentStateMachine.transition(var_status, ContentStatus.APPROVED)
        job.variant.status = ContentStatus.APPROVED.value

    repo.db.commit()

    return {"message": "Job successfully cancelled and reset to APPROVED state.", "job_id": str(job.id)}


@router.post("/v1/publications/{job_id}/reconcile")
def reconcile_publication_job(
    job_id: str,
    req: PublicationReconcileRequest,
    repo: ContentOpsRepository = Depends(get_repository),
    user: UserContext = Depends(require_roles("Owner", "Editor"))
):
    job = repo.db.query(PublicationJobModel).filter(PublicationJobModel.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Publication job not found.")
    job_ws = job.variant.package.brief.workspace_id if (job.variant and job.variant.package and job.variant.package.brief) else None
    if job_ws != user.workspace_id:
        raise HTTPException(status_code=404, detail="Publication job not found.")

    worker = PublisherWorker(repo.db)
    try:
        result = worker.reconcile_job(
            job_id=job_id,
            manual_resolution=req.resolution,
            external_post_id=req.external_post_id,
            permalink=req.permalink,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
