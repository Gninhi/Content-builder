import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

from apps.api.main import app
from infra.db.database import get_db_session
from infra.db.repository import ContentOpsRepository
from infra.db.models import WorkspaceModel, VeilleRunModel
from packages.security.auth import create_access_token
from services.scheduler.veille_worker import VeilleSchedulerWorker
from packages.tools.browse import fetch_safe_url

client = TestClient(app, raise_server_exceptions=False)


# =====================================================================
# Fixture: Seeded Test Workspace & Tokens
# =====================================================================
@pytest.fixture
def workspace_fixture():
    with get_db_session() as db:
        repo = ContentOpsRepository(db)
        ws = repo.create_workspace("Test Booster WS", "Europe/Paris", "owner_booster")
        
        if not repo.get_user("owner_booster"):
            repo.create_user("owner_booster", "owner@booster.com", "Owner Booster")
        if not repo.get_user("editor_booster"):
            repo.create_user("editor_booster", "editor@booster.com", "Editor Booster")
        repo.add_workspace_member(ws.id, "editor_booster", "Editor")
        if not repo.get_user("viewer_booster"):
            repo.create_user("viewer_booster", "viewer@booster.com", "Viewer Booster")
        repo.add_workspace_member(ws.id, "viewer_booster", "Viewer")

        if not repo.get_user("other_user"):
            repo.create_user("other_user", "other@booster.com", "Other User")
        ws_foreign = repo.create_workspace("Foreign WS Booster", "UTC", "other_user")

        owner_tok = create_access_token(user_id="owner_booster", role="Owner", workspace_id=ws.id)
        editor_tok = create_access_token(user_id="editor_booster", role="Editor", workspace_id=ws.id)
        viewer_tok = create_access_token(user_id="viewer_booster", role="Viewer", workspace_id=ws.id)
        foreign_tok = create_access_token(user_id="other_user", role="Owner", workspace_id=ws_foreign.id)

        return {
            "workspace_id": ws.id,
            "owner_tok": owner_tok,
            "editor_tok": editor_tok,
            "viewer_tok": viewer_tok,
            "foreign_tok": foreign_tok,
        }


# =====================================================================
# 1. Workspaces & Brand Profiles Router Coverage
# =====================================================================
def test_workspace_router_endpoints(workspace_fixture):
    fix = workspace_fixture
    ws_id = fix["workspace_id"]
    headers = {"Authorization": f"Bearer {fix['owner_tok']}"}

    # GET /v1/workspaces/{ws_id}
    res = client.get(f"/v1/workspaces/{ws_id}", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["id"] == ws_id
    assert data["name"] == "Test Booster WS"

    # POST /v1/workspaces/{ws_id}/kill-switch
    res_ks = client.post(
        f"/v1/workspaces/{ws_id}/kill-switch",
        headers=headers,
        json={"enabled": True}
    )
    assert res_ks.status_code == 200
    assert res_ks.json()["kill_switch_enabled"] is True

    # POST /v1/brand-profiles
    bp_payload = {
        "workspace_id": ws_id,
        "audience": ["Founders", "CTOs"],
        "voice": "Direct & Technique",
        "pillars": ["Agentic AI", "FastAPI"],
        "prohibited_topics": ["Spam", "Clickbait"],
        "cta_policy": {"frequency": "always"}
    }
    res_bp = client.post("/v1/brand-profiles", headers=headers, json=bp_payload)
    assert res_bp.status_code == 200
    bp_data = res_bp.json()
    assert bp_data["version"] == 1

    # GET /v1/brand-profiles/{ws_id}
    res_get_bp = client.get(f"/v1/brand-profiles/{ws_id}", headers=headers)
    assert res_get_bp.status_code == 200
    assert res_get_bp.json()["voice"] == "Direct & Technique"

    # GET /v1/brand-profiles/{ws_id}/versions
    res_vers = client.get(f"/v1/brand-profiles/{ws_id}/versions", headers=headers)
    assert res_vers.status_code == 200
    assert len(res_vers.json()) >= 1

    # Cross-workspace forbidden (OWASP API1:2023 - 404 prevents existence enumeration)
    foreign_headers = {"Authorization": f"Bearer {fix['foreign_tok']}"}
    res_forbidden = client.get(f"/v1/workspaces/{ws_id}", headers=foreign_headers)
    assert res_forbidden.status_code in (403, 404)


# =====================================================================
# 2. Ideas Router Coverage
# =====================================================================
def test_ideas_router_list(workspace_fixture):
    fix = workspace_fixture
    headers = {"Authorization": f"Bearer {fix['viewer_tok']}"}

    # Listing ideas for caller workspace
    res = client.get("/v1/ideas", headers=headers)
    assert res.status_code == 200
    assert isinstance(res.json(), list)

    # Attempting to list with foreign workspace_id query param
    res_403 = client.get(f"/v1/ideas?workspace_id={fix['workspace_id']}", headers={"Authorization": f"Bearer {fix['foreign_tok']}"})
    assert res_403.status_code == 403


# =====================================================================
# 3. Strategy & Insights Router Coverage
# =====================================================================
def test_strategy_router_insights(workspace_fixture):
    fix = workspace_fixture
    headers = {"Authorization": f"Bearer {fix['editor_tok']}"}

    # Generate strategy insights (no metric snapshots -> empty insights)
    res = client.post(
        "/v1/strategy/insights",
        headers=headers,
        json={"workspace_id": fix["workspace_id"]}
    )
    assert res.status_code == 200
    assert "insights" in res.json()

    # Foreign workspace -> 403
    foreign_headers = {"Authorization": f"Bearer {fix['foreign_tok']}"}
    res_403 = client.post(
        "/v1/strategy/insights",
        headers=foreign_headers,
        json={"workspace_id": fix["workspace_id"]}
    )
    assert res_403.status_code == 403


# =====================================================================
# 4. Analytics Router Coverage
# =====================================================================
def test_analytics_router_overview(workspace_fixture):
    fix = workspace_fixture
    headers = {"Authorization": f"Bearer {fix['viewer_tok']}"}

    res = client.get("/v1/analytics/overview", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert "total_posts" in data or "average_engagement_rate" in data


# =====================================================================
# 5. VeilleSchedulerWorker Timing Coverage
# =====================================================================
def test_veille_worker_due_calculations():
    worker = VeilleSchedulerWorker()
    ws = WorkspaceModel(id="ws_tz_test", name="TZ Test", timezone="Europe/Paris")
    
    mock_repo = MagicMock()
    # Scenario 1: No previous run exists -> due if past scheduled time
    mock_repo.get_latest_veille_run.return_value = None
    is_due = worker.is_run_due_for_workspace(ws, mock_repo, target_hour=0, target_minute=0)
    assert is_due is True

    # Scenario 2: Previous run happened today -> not due
    today_utc = datetime.now(timezone.utc)
    mock_run = VeilleRunModel(
        id="run_1",
        workspace_id=ws.id,
        started_at=today_utc,
        status="SUCCESS"
    )
    mock_repo.get_latest_veille_run.return_value = mock_run
    is_due_today = worker.is_run_due_for_workspace(ws, mock_repo, target_hour=0, target_minute=0)
    assert is_due_today is False

    # Scenario 3: Next due run calculation
    next_due = worker.calculate_next_due_run(ws, latest_run=mock_run)
    assert next_due is not None
    assert next_due.tzinfo is not None


# =====================================================================
# 6. Browse Safe Fetcher Anti-SSRF Validation Coverage
# =====================================================================
def test_browse_safe_fetch_validation():
    # Unsupported scheme
    with pytest.raises(PermissionError, match="Protocole non autorisé"):
        fetch_safe_url("ftp://example.com/file.txt")

    # Local IP rejection (SSRF protection)
    with pytest.raises(PermissionError, match="adresse privée ou locale"):
        fetch_safe_url("http://127.0.0.1:8080/admin")
