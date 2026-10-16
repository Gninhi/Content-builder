import pytest
from fastapi.testclient import TestClient
from apps.api.main import app
from packages.security.auth import create_access_token, Role
from infra.db.database import init_db, SessionLocal
from infra.db.repository import ContentOpsRepository
from infra.db.models import WorkspaceModel, WorkspaceMemberModel

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_workspace():
    init_db()
    db = SessionLocal()
    try:
        repo = ContentOpsRepository(db)
        if not repo.get_user("usr_pag_tester"):
            repo.create_user(user_id="usr_pag_tester", email="pag_tester@example.com", full_name="Pagination Tester")
        if not db.query(WorkspaceModel).filter(WorkspaceModel.id == "ws_pag_test").first():
            ws = WorkspaceModel(id="ws_pag_test", name="Pagination Test WS", timezone="UTC", owner_id="usr_pag_tester")
            db.add(ws)
            db.commit()
            repo.create_or_version_brand_profile("ws_pag_test", ["Engineers"], "Direct", ["Tech"], [], {})
        m = db.query(WorkspaceMemberModel).filter(
            WorkspaceMemberModel.workspace_id == "ws_pag_test",
            WorkspaceMemberModel.user_id == "usr_pag_tester"
        ).first()
        if not m:
            repo.add_workspace_member("ws_pag_test", "usr_pag_tester", "Owner")
    finally:
        db.close()


@pytest.fixture
def auth_headers():
    token = create_access_token(user_id="usr_pag_tester", workspace_id="ws_pag_test", role=Role.OWNER)
    return {"Authorization": f"Bearer {token}"}


def test_signals_pagination_upper_bound_rejection(auth_headers):
    """X-004: GET /v1/signals rejects limit > 100 with HTTP 422 Unprocessable Entity."""
    # Exceeding upper bound
    resp = client.get("/v1/signals?limit=101", headers=auth_headers)
    assert resp.status_code == 422, f"Expected 422 for limit=101, got {resp.status_code}: {resp.text}"

    # Zero or negative
    resp = client.get("/v1/signals?limit=0", headers=auth_headers)
    assert resp.status_code == 422

    # Exactly max allowed limit
    resp = client.get("/v1/signals?limit=100", headers=auth_headers)
    assert resp.status_code == 200


def test_publications_pagination_upper_bound_rejection(auth_headers):
    """X-004: GET /v1/publications enforces limit <= 100."""
    resp = client.get("/v1/publications?limit=101", headers=auth_headers)
    assert resp.status_code == 422, f"Expected 422 for limit=101, got {resp.status_code}: {resp.text}"

    resp = client.get("/v1/publications?limit=50", headers=auth_headers)
    assert resp.status_code == 200


def test_sources_pagination_upper_bound_rejection(auth_headers):
    """X-004: GET /v1/sources enforces limit <= 100."""
    resp = client.get("/v1/sources?limit=101", headers=auth_headers)
    assert resp.status_code == 422, f"Expected 422 for limit=101, got {resp.status_code}: {resp.text}"

    resp = client.get("/v1/sources?limit=50", headers=auth_headers)
    assert resp.status_code == 200


def test_ideas_pagination_upper_bound_rejection(auth_headers):
    """X-004: GET /v1/ideas enforces limit <= 100."""
    resp = client.get("/v1/ideas?limit=101", headers=auth_headers)
    assert resp.status_code == 422, f"Expected 422 for limit=101, got {resp.status_code}: {resp.text}"

    resp = client.get("/v1/ideas?limit=50", headers=auth_headers)
    assert resp.status_code == 200


def test_inbox_pagination_upper_bound_rejection(auth_headers):
    """X-004: GET /v1/inbox enforces limit <= 100."""
    resp = client.get("/v1/inbox?limit=101", headers=auth_headers)
    assert resp.status_code == 422, f"Expected 422 for limit=101, got {resp.status_code}: {resp.text}"

    resp = client.get("/v1/inbox?limit=50", headers=auth_headers)
    assert resp.status_code == 200
