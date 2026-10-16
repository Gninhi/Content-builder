from datetime import datetime, timezone
import pytest
from fastapi.testclient import TestClient

from apps.api.main import app
from infra.db.database import get_db_session
from infra.db.repository import ContentOpsRepository
from infra.db.models import PublicationJobModel
from packages.domain.state_machine import ContentStatus
from packages.security.auth import create_access_token

client = TestClient(app, raise_server_exceptions=False)


@pytest.fixture
def publishing_job_fixture():
    with get_db_session() as db:
        repo = ContentOpsRepository(db)
        ws = repo.create_workspace("Cancel Test WS", "UTC", "owner_cancel")
        brief = repo.create_brief(workspace_id=ws.id, objective="Test Cancel Guard", platform_targets=["linkedin"])
        pkg = repo.create_content_package(brief.id, 1)
        var = repo.add_variant(
            package_id=pkg.id,
            platform="linkedin",
            hook="Hook test",
            body="Body content testing cancellation safety rules.",
            cta="CTA test",
            hashtags=["#Safety"],
            media_spec={}
        )
        var.status = ContentStatus.IN_REVIEW.value
        db.commit()

        repo.record_approval(variant_id=var.id, decision="approve", reviewer_id="owner_cancel", workspace_id=ws.id)
        job = repo.schedule_publication(
            workspace_id=ws.id,
            variant_id=var.id,
            scheduled_at=datetime.now(timezone.utc)
        )
        db.commit()

        owner_token = create_access_token(user_id="owner_cancel", role="Owner", workspace_id=ws.id)

        return {
            "workspace_id": ws.id,
            "job_id": job.id,
            "variant_id": var.id,
            "owner_token": owner_token,
        }


def test_cannot_cancel_job_in_publishing_state(publishing_job_fixture):
    """C5: Cancelling a job in PUBLISHING state must be blocked with HTTP 400."""
    fix = publishing_job_fixture
    job_id = fix["job_id"]
    headers = {"Authorization": f"Bearer {fix['owner_token']}"}

    # Simulate job transitioning to PUBLISHING
    with get_db_session() as db:
        job = db.query(PublicationJobModel).filter(PublicationJobModel.id == job_id).first()
        job.status = ContentStatus.PUBLISHING.value
        db.commit()

    res = client.post(f"/v1/publications/{job_id}/cancel", headers=headers)
    assert res.status_code == 400
    assert "Cannot cancel" in res.json()["detail"]


def test_cannot_cancel_job_in_publish_unknown_state(publishing_job_fixture):
    """C5: Cancelling a job in PUBLISH_UNKNOWN state must be blocked with HTTP 400."""
    fix = publishing_job_fixture
    job_id = fix["job_id"]
    headers = {"Authorization": f"Bearer {fix['owner_token']}"}

    # Simulate job transitioning to PUBLISH_UNKNOWN
    with get_db_session() as db:
        job = db.query(PublicationJobModel).filter(PublicationJobModel.id == job_id).first()
        job.status = ContentStatus.PUBLISH_UNKNOWN.value
        db.commit()

    res = client.post(f"/v1/publications/{job_id}/cancel", headers=headers)
    assert res.status_code == 400
    assert "Cannot cancel" in res.json()["detail"]


def test_reconcile_endpoint_exposed_and_functional(publishing_job_fixture):
    """C5: POST /v1/publications/{job_id}/reconcile must be exposed and resolve UNKNOWN jobs."""
    fix = publishing_job_fixture
    job_id = fix["job_id"]
    headers = {"Authorization": f"Bearer {fix['owner_token']}"}

    # Put job in PUBLISH_UNKNOWN
    with get_db_session() as db:
        job = db.query(PublicationJobModel).filter(PublicationJobModel.id == job_id).first()
        job.status = ContentStatus.PUBLISH_UNKNOWN.value
        db.commit()

    res = client.post(
        f"/v1/publications/{job_id}/reconcile",
        headers=headers,
        json={
            "resolution": "CONFIRMED_FAILED"
        }
    )
    assert res.status_code == 200
    assert res.json()["status"] == "RECONCILED_FAILED"
