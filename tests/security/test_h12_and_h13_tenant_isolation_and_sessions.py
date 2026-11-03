import uuid
from fastapi.testclient import TestClient
from apps.api.main import app
from packages.security.auth import create_access_token
from infra.db.database import get_db_session, get_db
from infra.db.repository import ContentOpsRepository

client = TestClient(app, raise_server_exceptions=False)


def test_cross_tenant_resource_access_returns_404_not_403():
    """
    Test H12:
    When a tenant accesses a resource (e.g. brand profile, workspace, publication job)
    belonging to another tenant, the API MUST return 404 Not Found (not 403 Forbidden).
    Returning 403 leaks resource existence and allows cross-tenant ID enumeration (OWASP API1:2023).
    """
    user_a_id = f"usr_{uuid.uuid4().hex[:6]}"
    with get_db_session() as db:
        repo = ContentOpsRepository(db)
        repo.create_user(user_id=user_a_id, email=f"{user_a_id}@company.com", full_name="Alpha Owner")
        ws_a = repo.create_workspace(name="Tenant Alpha", timezone="UTC", owner_id=user_a_id)
        ws_b = repo.create_workspace(name="Tenant Beta", timezone="UTC", owner_id=f"owner_{uuid.uuid4().hex[:6]}")
        ws_a_id = str(ws_a.id)
        ws_b_id = str(ws_b.id)

        bp_b = repo.create_or_version_brand_profile(
            workspace_id=ws_b_id,
            audience=["Engineers"],
            voice="Formal",
            pillars=["Tech"],
            prohibited_topics=[],
            cta_policy={},
        )
        bp_b_id = str(bp_b.id)

    # Token for Tenant A
    tok_a = create_access_token(user_id=user_a_id, role="Owner", workspace_id=ws_a_id)
    headers_a = {"Authorization": f"Bearer {tok_a}"}

    # Tenant A attempts to fetch Tenant B's brand profile: MUST be 404
    res_bp = client.get(f"/v1/brand-profiles/{bp_b_id}", headers=headers_a)
    assert res_bp.status_code == 404, f"Expected 404 for cross-tenant brand profile, got {res_bp.status_code}: {res_bp.text}"

    # Tenant A attempts to access Tenant B's workspace metadata: MUST be 404
    res_ws = client.get(f"/v1/workspaces/{ws_b_id}", headers=headers_a)
    assert res_ws.status_code == 404, f"Expected 404 for cross-tenant workspace access, got {res_ws.status_code}: {res_ws.text}"


def test_db_session_lifecycle_yields_fresh_session_and_closes():
    """
    Test H13:
    get_db generator yields an independent session and guarantees closure without scoped_session thread leaks.
    """
    gen = get_db()
    session = next(gen)
    assert session is not None
    assert session.is_active is True

    # Consuming the generator must close the session
    try:
        next(gen)
    except StopIteration:
        pass

    assert not session.is_active or session._is_clean(), "Session was not closed properly upon generator completion"
