from typing import cast, List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from packages.contracts.schemas import (
    PublicationScheduleRequest,
    PublicationJobResponse,
    PublicationReconcileRequest,
)
from packages.domain.state_machine import ContentStatus, ContentStateMachine
from services.publisher.worker import PublisherWorker
from apps.api.dependencies import get_repository, UserContext, require_roles
from infra.db.repository import ContentOpsRepository
from infra.db.models import PublicationJobModel, ContentVariantModel, ContentPackageModel, ContentBriefModel

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
    job = repo.db.query(PublicationJobModel).filter(
        PublicationJobModel.id == job_id,
        PublicationJobModel.workspace_id == user.workspace_id
    ).first()
    if not job:
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
    job = repo.db.query(PublicationJobModel).filter(
        PublicationJobModel.id == job_id,
        PublicationJobModel.workspace_id == user.workspace_id
    ).first()
    if not job:
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
    job = repo.db.query(PublicationJobModel).filter(
        PublicationJobModel.id == job_id,
        PublicationJobModel.workspace_id == user.workspace_id
    ).first()
    if not job:
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


@router.get("/v1/publications", response_model=List[PublicationJobResponse])
def list_publications(
    status: Optional[str] = Query(None, description="Filter by publication status"),
    limit: int = Query(50, ge=1, le=100, description="Max jobs to return (1-100)"),
    repo: ContentOpsRepository = Depends(get_repository),
    user: UserContext = Depends(require_roles("Owner", "Editor", "Viewer", "ServiceAgent"))
):
    query = repo.db.query(PublicationJobModel).filter(PublicationJobModel.workspace_id == user.workspace_id)
    if status:
        query = query.filter(PublicationJobModel.status == status)
    jobs = query.order_by(PublicationJobModel.scheduled_at.desc()).limit(limit).all()
    return [
        PublicationJobResponse(
            id=str(j.id),
            variant_id=str(j.variant_id),
            platform=str(j.platform),
            scheduled_at=cast(datetime, j.scheduled_at),
            idempotency_key=str(j.idempotency_key),
            status=ContentStatus(str(j.status)),
            attempt_count=int(j.attempt_count) if j.attempt_count is not None else 0,
            error_message=str(j.error_message) if j.error_message else None,
        )
        for j in jobs
    ]
