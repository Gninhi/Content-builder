from fastapi.testclient import TestClient

from apps.api.main import app
from apps.api.dependencies import get_current_user, UserContext
from infra.db.database import get_db_session
from infra.db.repository import ContentOpsRepository
from packages.prompts.veille_queries import compute_qualification_score, get_queries_for_axis, SUPPORTED_AXES


def test_qualification_score_rubric():
    res = compute_qualification_score(
        trust_level="A",
        days_old=3,
        has_concrete_facts=True,
        is_strategic=True,
        is_exec_relevant=True,
    )
    assert res["score"] == 5.0
    assert res["is_qualified"] is True
    assert res["breakdown"]["authority"] == 1.0

    res_low = compute_qualification_score(
        trust_level="C",
        days_old=45,
        has_concrete_facts=False,
        is_strategic=False,
        is_exec_relevant=False,
    )
    assert res_low["score"] < 3.0
    assert res_low["is_qualified"] is False


def test_query_bank_axes():
    for axis in SUPPORTED_AXES:
        queries = get_queries_for_axis(axis, count=2)
        assert len(queries) == 2
        for q in queries:
            assert "query" in q
            assert "trust_target" in q


def test_repository_veille_sources_and_signals():
    with get_db_session() as db:
        repo = ContentOpsRepository(db)
        sources = repo.seed_default_veille_sources("ws_test_veille")
        assert len(sources) >= 10

        # Test deduplication on 90-day window
        sig1 = repo.save_signal(
            workspace_id="ws_test_veille",
            title="EU AI Act Framework Test Signal",
            summary="A test summary of EU AI Act enforcement.",
            axis="ia",
            trust_level="A",
            qualification_score=4.5,
            qualification_criteria={"authority": 1.0},
            facts=[{"fact": "Obligation test", "source_url": "https://ec.europa.eu"}],
            executive_takeaway="Takeaway for leaders",
            canonical_url="https://ec.europa.eu/ai-act-test",
        )
        assert sig1.id.startswith("sig_")

        # Second save with same canonical URL should deduplicate
        sig2 = repo.save_signal(
            workspace_id="ws_test_veille",
            title="EU AI Act Framework Test Signal - Variant",
            summary="Another summary",
            axis="ia",
            trust_level="A",
            qualification_score=4.8,
            qualification_criteria={"authority": 1.0},
            facts=[{"fact": "Obligation test", "source_url": "https://ec.europa.eu"}],
            executive_takeaway="Updated Takeaway",
            canonical_url="https://ec.europa.eu/ai-act-test",
        )
        assert sig2.id == sig1.id
        assert sig2.qualification_score == 4.8


def test_signals_api_endpoints():
    client = TestClient(app)

    # Mock Owner auth
    def mock_owner_context():
        return UserContext(user_id="owner_test", workspace_id="ws_api_test", role="Owner")

    app.dependency_overrides[get_current_user] = mock_owner_context

    try:
        # 1. Trigger collection in demo mode
        resp = client.post("/v1/signals/collect", json={"demo": True, "axis": "ia"})
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 2
        assert data[0]["is_synthetic"] is True
        sig_id = data[0]["id"]

        # 2. List signals
        list_resp = client.get("/v1/signals?axis=ia&min_score=3.0")
        assert list_resp.status_code == 200
        assert len(list_resp.json()) >= 1

        # 3. Get single signal
        get_resp = client.get(f"/v1/signals/{sig_id}")
        assert get_resp.status_code == 200
        assert get_resp.json()["id"] == sig_id

        # 4. Update status
        patch_resp = client.patch(f"/v1/signals/{sig_id}/status", json={"status": "CONVERTED"})
        assert patch_resp.status_code == 200
        assert patch_resp.json()["status"] == "CONVERTED"

        # 5. List sources and seed
        seed_resp = client.post("/v1/signals/sources/seed")
        assert seed_resp.status_code == 200
        sources = client.get("/v1/signals/sources").json()
        assert len(sources) >= 10

    finally:
        app.dependency_overrides.pop(get_current_user, None)


def test_signals_sources_rbac_owner_only():
    client = TestClient(app)

    # Mock Editor auth (should be forbidden from creating sources)
    def mock_editor_context():
        return UserContext(user_id="editor_test", workspace_id="ws_rbac_test", role="Editor")

    app.dependency_overrides[get_current_user] = mock_editor_context

    try:
        resp = client.post(
            "/v1/signals/sources",
            json={
                "name": "Unauthorized Source",
                "url": "https://example.com/feed",
                "axis": "ia",
                "trust_level": "B",
                "source_type": "rss"
            }
        )
        assert resp.status_code == 403
    finally:
        app.dependency_overrides.pop(get_current_user, None)
