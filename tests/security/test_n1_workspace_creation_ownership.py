import uuid
from fastapi.testclient import TestClient
from apps.api.main import app
from packages.security.auth import create_access_token
from infra.db.database import get_db_session
from infra.db.models import WorkspaceModel, WorkspaceMemberModel
from infra.db.repository import ContentOpsRepository

client = TestClient(app, raise_server_exceptions=False)


def test_create_workspace_binds_to_authenticated_user_and_creates_member():
    """
    Test N1:
    1. Authenticated user 'user_alice' calls POST /v1/workspaces with owner_id='spoofed_victim'.
    2. The created workspace MUST have owner_id == 'user_alice', ignoring spoofed input.
    3. A WorkspaceMemberModel entry MUST be created with user_id='user_alice' and role='Owner'.
    """
    unique_id = uuid.uuid4().hex[:8]
    user_id = f"usr_{unique_id}"
    email = f"alice_{unique_id}@company.com"
    with get_db_session() as db:
        repo = ContentOpsRepository(db)
        alice = repo.create_user(user_id=user_id, email=email, full_name="Alice Founder")
        alice_id = str(alice.id)

    token = create_access_token(user_id=alice_id, role="Owner", workspace_id="ws_init")
    headers = {"Authorization": f"Bearer {token}"}

    response = client.post(
        "/v1/workspaces",
        headers=headers,
        json={
            "name": "Alice Enterprise",
            "timezone": "Europe/Paris",
            "owner_id": "spoofed_victim"
        }
    )

    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    data = response.json()
    ws_id = data["id"]
    assert data["owner_id"] == alice_id, f"Vulnerability N1: owner_id was not bound to authenticated user! Got {data['owner_id']}"

    # Verify database state
    with get_db_session() as db:
        ws = db.query(WorkspaceModel).filter(WorkspaceModel.id == ws_id).first()
        assert ws is not None
        assert ws.owner_id == alice_id

        member = db.query(WorkspaceMemberModel).filter(
            WorkspaceMemberModel.workspace_id == ws_id,
            WorkspaceMemberModel.user_id == alice_id
        ).first()
        assert member is not None, "Vulnerability N1: No WorkspaceMemberModel created for workspace owner!"
        assert member.role == "Owner"
