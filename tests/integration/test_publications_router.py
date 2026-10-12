import os
import unittest.mock
from datetime import datetime, timezone
import pytest
from fastapi.testclient import TestClient

from apps.api.main import app
from infra.db.database import get_db_session
from infra.db.repository import ContentOpsRepository
from packages.domain.state_machine import ContentStatus
from packages.security.auth import create_access_token
from services.publisher.worker import PublisherWorker

client = TestClient(app, raise_server_exceptions=False)


@pytest.fixture(autouse=True)
def vault_key_env():
    old = os.environ.get("SECRET_VAULT_KEY")
    os.environ["SECRET_VAULT_KEY"] = "super-secret-vault-master-key-32b!"
    yield
    if old is not None:
        os.environ["SECRET_VAULT_KEY"] = old
    else:
        os.environ.pop("SECRET_VAULT_KEY", None)


@pytest.fixture
def seeded_publication_fixture():
    with get_db_session() as db:
        repo = ContentOpsRepository(db)
        ws = repo.create_workspace("Pub Workspace", "UTC", "owner_pub")
        brief = repo.create_brief(workspace_id=ws.id, objective="Test publications router", platform_targets=["linkedin"])
        pkg = repo.create_content_package(brief.id, 1)
        var = repo.add_variant(
            package_id=pkg.id,
            platform="linkedin",
            hook="Hook publication test",
            body="Comprehensive body testing the publications router endpoints and branches.",
            cta="Follow for more",
            hashtags=["#ContentOps", "#AI"],
            media_spec={}
        )
        var.status = ContentStatus.IN_REVIEW.value
        db.commit()

        # Approve variant so it can be scheduled
        repo.record_approval(variant_id=var.id, decision="approve", reviewer_id="owner_pub", workspace_id=ws.id)

        owner_token = create_access_token(user_id="owner_pub", role="Owner", workspace_id=ws.id)
        editor_token = create_access_token(user_id="editor_pub", role="Editor", workspace_id=ws.id)
        viewer_token = create_access_token(user_id="viewer_pub", role="Viewer", workspace_id=ws.id)
        foreign_token = create_access_token(user_id="foreign_user", role="Owner", workspace_id="ws_foreign_xyz")

        return {
            "workspace_id": ws.id,
            "variant_id": var.id,
            "owner_token": owner_token,
            "editor_token": editor_token,
            "viewer_token": viewer_token,
            "foreign_token": foreign_token
        }


def test_schedule_publication_success(seeded_publication_fixture):
    fixture = seeded_publication_fixture
    response = client.post(
        "/v1/publications/schedule",
        json={
            "variant_id": fixture["variant_id"],
            "scheduled_at": datetime.now(timezone.utc).isoformat()
        },
        headers={"Authorization": f"Bearer {fixture['owner_token']}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["variant_id"] == fixture["variant_id"]
    assert data["platform"] == "linkedin"
    assert data["status"] in ("SCHEDULED", "CLAIMED", "DRAFT")


def test_schedule_publication_invalid_variant_returns_400(seeded_publication_fixture):
    fixture = seeded_publication_fixture
    response = client.post(
        "/v1/publications/schedule",
        json={
            "variant_id": "non_existent_variant_id",
            "scheduled_at": datetime.now(timezone.utc).isoformat()
        },
        headers={"Authorization": f"Bearer {fixture['editor_token']}"}
    )
    assert response.status_code == 400
    assert "not found" in response.json()["detail"].lower()


def test_schedule_publication_forbidden_for_viewer(seeded_publication_fixture):
    fixture = seeded_publication_fixture
    response = client.post(
        "/v1/publications/schedule",
        json={
            "variant_id": fixture["variant_id"],
            "scheduled_at": datetime.now(timezone.utc).isoformat()
        },
        headers={"Authorization": f"Bearer {fixture['viewer_token']}"}
    )
    assert response.status_code == 403


def test_publish_now_not_found(seeded_publication_fixture):
    fixture = seeded_publication_fixture
    response = client.post(
        "/v1/publications/non_existent_job_123/publish-now",
        headers={"Authorization": f"Bearer {fixture['owner_token']}"}
    )
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_publish_now_foreign_workspace_forbidden(seeded_publication_fixture):
    fixture = seeded_publication_fixture
    # Schedule first
    sched_res = client.post(
        "/v1/publications/schedule",
        json={
            "variant_id": fixture["variant_id"],
            "scheduled_at": datetime.now(timezone.utc).isoformat()
        },
        headers={"Authorization": f"Bearer {fixture['owner_token']}"}
    )
    job_id = sched_res.json()["id"]

    # Try accessing with foreign workspace token
    response = client.post(
        f"/v1/publications/{job_id}/publish-now",
        headers={"Authorization": f"Bearer {fixture['foreign_token']}"}
    )
    assert response.status_code == 403
    assert "forbidden" in response.json()["detail"].lower()


def test_publish_now_non_owner_forbidden(seeded_publication_fixture):
    fixture = seeded_publication_fixture
    sched_res = client.post(
        "/v1/publications/schedule",
        json={
            "variant_id": fixture["variant_id"],
            "scheduled_at": datetime.now(timezone.utc).isoformat()
        },
        headers={"Authorization": f"Bearer {fixture['owner_token']}"}
    )
    job_id = sched_res.json()["id"]

    response = client.post(
        f"/v1/publications/{job_id}/publish-now",
        headers={"Authorization": f"Bearer {fixture['editor_token']}"}
    )
    assert response.status_code == 403


def test_publish_now_success_and_error_handling(seeded_publication_fixture):
    fixture = seeded_publication_fixture
    sched_res = client.post(
        "/v1/publications/schedule",
        json={
            "variant_id": fixture["variant_id"],
            "scheduled_at": datetime.now(timezone.utc).isoformat()
        },
        headers={"Authorization": f"Bearer {fixture['owner_token']}"}
    )
    job_id = sched_res.json()["id"]

    # Test error handling branch when execute_job raises
    with unittest.mock.patch.object(PublisherWorker, "execute_job", side_effect=RuntimeError("Worker connection failed")):
        err_res = client.post(
            f"/v1/publications/{job_id}/publish-now",
            headers={"Authorization": f"Bearer {fixture['owner_token']}"}
        )
        assert err_res.status_code == 400
        assert "Worker connection failed" in err_res.json()["detail"]

    # Test success branch
    with unittest.mock.patch.object(PublisherWorker, "execute_job", return_value={"status": "PUBLISHED", "post_id": "test_post_1"}):
        ok_res = client.post(
            f"/v1/publications/{job_id}/publish-now",
            headers={"Authorization": f"Bearer {fixture['owner_token']}"}
        )
        assert ok_res.status_code == 200
        assert ok_res.json()["status"] == "PUBLISHED"


def test_cancel_publication_job_lifecycle(seeded_publication_fixture):
    fixture = seeded_publication_fixture
    sched_res = client.post(
        "/v1/publications/schedule",
        json={
            "variant_id": fixture["variant_id"],
            "scheduled_at": datetime.now(timezone.utc).isoformat()
        },
        headers={"Authorization": f"Bearer {fixture['owner_token']}"}
    )
    job_id = sched_res.json()["id"]

    # 404 test
    res_404 = client.post(
        "/v1/publications/non_existent_job_xyz/cancel",
        headers={"Authorization": f"Bearer {fixture['editor_token']}"}
    )
    assert res_404.status_code == 404

    # 403 foreign workspace test
    res_403 = client.post(
        f"/v1/publications/{job_id}/cancel",
        headers={"Authorization": f"Bearer {fixture['foreign_token']}"}
    )
    assert res_403.status_code == 403

    # Success cancellation test
    cancel_res = client.post(
        f"/v1/publications/{job_id}/cancel",
        headers={"Authorization": f"Bearer {fixture['editor_token']}"}
    )
    assert cancel_res.status_code == 200
    assert "Job successfully cancelled" in cancel_res.json()["message"]

    # Cannot cancel published test
    with get_db_session() as db:
        from infra.db.models import PublicationJobModel
        j = db.query(PublicationJobModel).filter_by(id=job_id).first()
        j.status = ContentStatus.PUBLISHED.value
        db.commit()

    published_cancel_res = client.post(
        f"/v1/publications/{job_id}/cancel",
        headers={"Authorization": f"Bearer {fixture['owner_token']}"}
    )
    assert published_cancel_res.status_code == 400
    assert "already published" in published_cancel_res.json()["detail"].lower()
