import uuid
import pytest
from fastapi.testclient import TestClient

from apps.api.main import app
from infra.db.database import get_db_session
from infra.db.repository import ContentOpsRepository
from packages.security.auth import create_access_token, Role

client = TestClient(app, raise_server_exceptions=False)


@pytest.fixture
def briefs_fixture():
    ws_id = f"ws_brief_{uuid.uuid4().hex[:8]}"
    foreign_ws = f"ws_foreign_{uuid.uuid4().hex[:8]}"

    owner_id = f"user_{uuid.uuid4().hex[:8]}"
    editor_id = f"user_{uuid.uuid4().hex[:8]}"
    viewer_id = f"user_{uuid.uuid4().hex[:8]}"
    foreign_id = f"user_{uuid.uuid4().hex[:8]}"

    owner_tok = create_access_token(user_id=owner_id, role=Role.OWNER, workspace_id=ws_id)
    editor_tok = create_access_token(user_id=editor_id, role=Role.EDITOR, workspace_id=ws_id)
    viewer_tok = create_access_token(user_id=viewer_id, role=Role.VIEWER, workspace_id=ws_id)
    foreign_tok = create_access_token(user_id=foreign_id, role=Role.EDITOR, workspace_id=foreign_ws)

    with get_db_session() as db:
        repo = ContentOpsRepository(db)
        repo.create_workspace(name="Briefs WS", workspace_id=ws_id, owner_id=owner_id)
        repo.add_workspace_member(ws_id, editor_id, "Editor")
        repo.add_workspace_member(ws_id, viewer_id, "Viewer")
        repo.create_workspace(name="Foreign WS", workspace_id=foreign_ws, owner_id=foreign_id)

    return {
        "ws_id": ws_id,
        "foreign_ws": foreign_ws,
        "owner_tok": owner_tok,
        "editor_tok": editor_tok,
        "viewer_tok": viewer_tok,
        "foreign_tok": foreign_tok,
    }


def test_create_brief_and_list_briefs(briefs_fixture):
    fix = briefs_fixture
    headers = {"Authorization": f"Bearer {fix['editor_tok']}"}

    # 1. Create a brief
    payload = {
        "workspace_id": fix["ws_id"],
        "objective": "Launch Campaign Q1",
        "platform_targets": ["linkedin", "x"],
        "requirements": {"tone": "authoritative"},
    }
    create_res = client.post("/v1/briefs", headers=headers, json=payload)
    assert create_res.status_code == 200
    created_brief = create_res.json()
    brief_id = created_brief["id"]
    assert created_brief["objective"] == "Launch Campaign Q1"
    assert created_brief["workspace_id"] == fix["ws_id"]

    # 2. List briefs as Viewer (read-only allowed)
    viewer_headers = {"Authorization": f"Bearer {fix['viewer_tok']}"}
    list_res = client.get("/v1/briefs", headers=viewer_headers)
    assert list_res.status_code == 200
    briefs = list_res.json()
    assert isinstance(briefs, list)
    assert any(b["id"] == brief_id for b in briefs)

    # 3. Get detail of brief
    detail_res = client.get(f"/v1/briefs/{brief_id}", headers=viewer_headers)
    assert detail_res.status_code == 200
    detail = detail_res.json()
    assert detail["id"] == brief_id
    assert detail["objective"] == "Launch Campaign Q1"

    # 4. Cross-tenant isolation: Foreign tenant cannot access brief
    foreign_headers = {"Authorization": f"Bearer {fix['foreign_tok']}"}
    foreign_detail = client.get(f"/v1/briefs/{brief_id}", headers=foreign_headers)
    assert foreign_detail.status_code == 404

    # 5. Non-existent brief returns 404
    not_found = client.get("/v1/briefs/brief_non_existent", headers=headers)
    assert not_found.status_code == 404
