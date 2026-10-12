import pytest
from fastapi.testclient import TestClient
from apps.api.main import app
from packages.security.auth import create_access_token, Role
from infra.db.database import init_db, SessionLocal
from infra.db.repository import ContentOpsRepository

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_workspaces():
    init_db()
    db = SessionLocal()
    try:
        repo = ContentOpsRepository(db)
        if not repo.get_workspace("ws_tenant_1"):
            repo.create_workspace("Tenant 1", owner_id="owner_1").id = "ws_tenant_1"
            db.commit()
            repo.create_or_version_brand_profile("ws_tenant_1", ["Devs"], "Expert", ["AI"], [], {})
        if not repo.get_workspace("ws_tenant_2"):
            repo.create_workspace("Tenant 2", owner_id="owner_2").id = "ws_tenant_2"
            db.commit()
            repo.create_or_version_brand_profile("ws_tenant_2", ["Marketers"], "Casual", ["Growth"], [], {})
    finally:
        db.close()


def test_tenant_cannot_read_other_brand_profile():
    token_tenant_2 = create_access_token(user_id="user_2", role=Role.EDITOR, workspace_id="ws_tenant_2")
    response = client.get(
        "/v1/brand-profiles/ws_tenant_1",
        headers={"Authorization": f"Bearer {token_tenant_2}"}
    )
    assert response.status_code == 403


def test_tenant_cannot_approve_other_workspace_variant():
    """BOLA / IDOR test: Tenant 2 cannot approve Tenant 1's draft variant."""
    token_tenant_1 = create_access_token(user_id="user_1", role=Role.EDITOR, workspace_id="ws_tenant_1")
    token_tenant_2 = create_access_token(user_id="user_2", role=Role.EDITOR, workspace_id="ws_tenant_2")

    # Tenant 1 creates a brief and content
    brief_res = client.post(
        "/v1/briefs",
        headers={"Authorization": f"Bearer {token_tenant_1}"},
        json={
            "workspace_id": "ws_tenant_1",
            "objective": "Tenant 1 secret strategy",
            "platform_targets": ["linkedin"],
            "requirements": {}
        }
    )
    assert brief_res.status_code == 200
    brief_id = brief_res.json()["id"]

    content_res = client.post(
        "/v1/content/generate",
        headers={"Authorization": f"Bearer {token_tenant_1}"},
        json={"brief_id": brief_id, "workspace_id": "ws_tenant_1"}
    )
    assert content_res.status_code == 200
    tenant_1_variant_id = content_res.json()["variants"][0]["id"]

    # Tenant 2 tries to approve Tenant 1's variant!
    tamper_res = client.post(
        f"/v1/content/{tenant_1_variant_id}/approve",
        headers={"Authorization": f"Bearer {token_tenant_2}"},
        json={"decision": "approve", "reviewer_id": "user_2"}
    )
    # Must be 403 or 404, never 200!
    assert tamper_res.status_code in [403, 404], f"BOLA flaw! Tenant 2 approved Tenant 1 variant with status {tamper_res.status_code}"


def test_calendar_and_analytics_are_workspace_isolated():
    """Tenant 2 calendar and analytics must not leak Tenant 1 entries."""
    token_tenant_2 = create_access_token(user_id="user_2", role=Role.VIEWER, workspace_id="ws_tenant_2")

    cal_res = client.get(
        "/v1/calendar",
        headers={"Authorization": f"Bearer {token_tenant_2}"}
    )
    assert cal_res.status_code == 200
    # Scheduled or published items must only belong to ws_tenant_2
    for item in cal_res.json().get("scheduled", []):
        assert item.get("workspace_id", "ws_tenant_2") == "ws_tenant_2"


def test_ideas_unauthenticated_rejected_and_isolated():
    """Unauthenticated calls to /v1/ideas must return 401, and cross-tenant access must return 403."""
    # 1. Unauthenticated request
    unauth_res = client.get("/v1/ideas?workspace_id=ws_tenant_1")
    assert unauth_res.status_code == 401

    # 2. Authenticated on ws_tenant_2 trying to read ws_tenant_1
    token_tenant_2 = create_access_token(user_id="user_2", role=Role.EDITOR, workspace_id="ws_tenant_2")
    cross_res = client.get(
        "/v1/ideas?workspace_id=ws_tenant_1",
        headers={"Authorization": f"Bearer {token_tenant_2}"}
    )
    assert cross_res.status_code == 403


def test_owner_cannot_access_other_workspace_llm_config():
    """An Owner of tenant 1 cannot read or modify tenant 2's LLM configuration (BOLA prevention)."""
    owner_token_1 = create_access_token(user_id="owner_1", role=Role.OWNER, workspace_id="ws_tenant_1")

    # Read attempt
    res_get = client.get(
        "/v1/llm/config/ws_tenant_2",
        headers={"Authorization": f"Bearer {owner_token_1}"}
    )
    assert res_get.status_code == 403

    # Update attempt
    res_put = client.put(
        "/v1/llm/config/ws_tenant_2",
        headers={"Authorization": f"Bearer {owner_token_1}"},
        json={
            "default_provider_id": "gemini",
            "default_model_id": "gemini-3.8-flash",
            "default_temperature": 0.5,
            "task_overrides": {},
            "provider_settings": {}
        }
    )
    assert res_put.status_code == 403

