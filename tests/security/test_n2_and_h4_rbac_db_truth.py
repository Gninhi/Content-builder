import uuid
from fastapi import APIRouter, Depends
from fastapi.testclient import TestClient
from apps.api.main import app
from apps.api.dependencies import require_roles, UserContext
from packages.security.auth import create_access_token
from infra.db.database import get_db_session
from infra.db.repository import ContentOpsRepository

test_router = APIRouter(prefix="/v1/test-rbac")


@test_router.post("/service-only")
def service_only_endpoint(user: UserContext = Depends(require_roles("ServiceAgent"))):
    return {"status": "ok", "role": user.role}


@test_router.post("/editor-only")
def editor_only_endpoint(user: UserContext = Depends(require_roles("Editor"))):
    return {"status": "ok", "role": user.role}


app.include_router(test_router)
client = TestClient(app, raise_server_exceptions=False)


def test_owner_cannot_access_service_agent_only_endpoint():
    """
    Test N2:
    Owner should NOT bypass ServiceAgent-only routes.
    Segregation of duties must be enforced.
    """
    uid = f"usr_{uuid.uuid4().hex[:8]}"
    token = create_access_token(user_id=uid, role="Owner", workspace_id="ws_test")
    headers = {"Authorization": f"Bearer {token}"}

    res = client.post("/v1/test-rbac/service-only", headers=headers)
    assert res.status_code == 403, f"Expected 403 for Owner accessing ServiceAgent route, got {res.status_code}"


def test_db_role_takes_precedence_over_stale_jwt_token():
    """
    Test N2 & H4:
    If a user has an active token stating 'Editor', but their DB membership role was demoted to 'Viewer',
    the live DB membership role takes precedence and forbids editor actions.
    """
    uid = f"usr_{uuid.uuid4().hex[:8]}"
    ws_id = f"ws_{uuid.uuid4().hex[:8]}"
    with get_db_session() as db:
        repo = ContentOpsRepository(db)
        repo.create_user(user_id=uid, email=f"{uid}@test.com", full_name="Test User")
        ws = repo.create_workspace(name="Test Org", timezone="UTC", owner_id="other_owner")
        ws_id = str(ws.id)
        # Add user as Viewer in DB
        repo.add_workspace_member(workspace_id=ws_id, user_id=uid, role="Viewer")

    # Attacker crafts or uses stale JWT claiming 'Editor'
    stale_token = create_access_token(user_id=uid, role="Editor", workspace_id=ws_id)
    headers = {"Authorization": f"Bearer {stale_token}"}

    res = client.post("/v1/test-rbac/editor-only", headers=headers)
    assert res.status_code == 403, f"Expected 403 since DB role is Viewer, got {res.status_code}: {res.text}"


def test_deactivated_user_in_db_is_rejected_fail_closed():
    """
    Test H4:
    If user account is marked is_active=False in DB, fail-closed: return 401 even with valid JWT.
    """
    uid = f"usr_{uuid.uuid4().hex[:8]}"
    ws_id = f"ws_{uuid.uuid4().hex[:8]}"
    with get_db_session() as db:
        repo = ContentOpsRepository(db)
        u = repo.create_user(user_id=uid, email=f"{uid}@test.com", full_name="Inactive User")
        u.is_active = False
        db.commit()

    token = create_access_token(user_id=uid, role="Editor", workspace_id=ws_id)
    headers = {"Authorization": f"Bearer {token}"}

    res = client.post("/v1/test-rbac/editor-only", headers=headers)
    assert res.status_code == 401, f"Expected 401 for deactivated user, got {res.status_code}: {res.text}"
