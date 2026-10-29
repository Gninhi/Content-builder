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
        if not repo.get_workspace("ws_test_veille"):
            repo.create_workspace(name="Veille Test Workspace", workspace_id="ws_test_veille")
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

    from infra.db.database import get_db_session
    from infra.db.repository import ContentOpsRepository
    from infra.db.models import WorkspaceModel, WorkspaceMemberModel
    with get_db_session() as db:
        repo = ContentOpsRepository(db)
        if not repo.get_user("owner_test"):
            repo.create_user("owner_test", "owner@api_test.com", "Owner Test")
        ws = db.query(WorkspaceModel).filter_by(id="ws_api_test").first()
        if not ws:
            ws = WorkspaceModel(id="ws_api_test", name="API Test WS", timezone="UTC", owner_id="owner_test")
            db.add(ws)
            db.commit()
        if not db.query(WorkspaceMemberModel).filter_by(workspace_id="ws_api_test", user_id="owner_test").first():
            repo.add_workspace_member("ws_api_test", "owner_test", "Owner")

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


def test_explainable_qualification_and_missing_date_penalty():
    from packages.prompts.veille_queries import verify_quote_in_text

    # 1. Missing publication date (days_old=None) is penalized (recency_score=0.25)
    res_no_date = compute_qualification_score(
        trust_level="B",
        days_old=None,
        title="Note courte sans métrique",
        text="Un texte très court sans chiffre ni impact stratégique majeur.",
        axis="ia",
    )
    assert res_no_date["breakdown"]["recency_score"] == 0.25
    assert res_no_date["breakdown"]["date_missing_penalized"] is True
    assert res_no_date["is_qualified"] is False
    assert res_no_date["score"] < 3.2

    # 2. High-relevance, fact-dense content with recent date qualifies (>= 3.2)
    rich_text = (
        "En production enterprise, l'adoption de LangGraph et d'un routeur LLM multi-agent "
        "réduit la latence P95 de 48% et diminue le coût d'inférence de 62% selon notre audit "
        "de sécurité et conformité EU AI Act."
    )
    res_rich = compute_qualification_score(
        trust_level="A",
        days_old=2,
        title="Architecture LangGraph multi-agent : réduction de 62% des coûts en production",
        text=rich_text,
        axis="frameworks",
    )
    assert res_rich["is_qualified"] is True
    assert res_rich["score"] >= 3.2
    assert res_rich["breakdown"]["trust_score"] == 1.2
    assert res_rich["breakdown"]["recency_score"] == 0.8

    # 3. Quote verification checks verbatim grounding
    assert verify_quote_in_text("réduit la latence P95 de 48%", rich_text) is True
    assert verify_quote_in_text("Une citation totalement inventée absente du document", rich_text) is False


def test_real_url_source_ingestion_rejects_fictional_and_ssrf():
    from unittest.mock import patch, MagicMock

    client = TestClient(app)

    def mock_owner_context():
        return UserContext(user_id="owner_test", workspace_id="ws_api_test", role="Owner")

    app.dependency_overrides[get_current_user] = mock_owner_context
    try:
        # 1. SSRF URL is rejected with 400
        resp_ssrf = client.post(
            "/v1/sources",
            json={"type": "url", "url": "http://127.0.0.1:8080/internal"},
        )
        assert resp_ssrf.status_code == 400

        # 2. Empty/insufficient HTML content is rejected with 422 (never stores fake text)
        mock_empty_resp = MagicMock()
        mock_empty_resp.status_code = 200
        mock_empty_resp.url = "https://example.com/empty"
        mock_empty_resp.text = "<html><body><p>Court</p></body></html>"
        with patch("apps.api.routers.sources.fetch_safe_url", return_value=mock_empty_resp):
            resp_short = client.post(
                "/v1/sources",
                json={"type": "url", "url": "https://example.com/empty"},
            )
            assert resp_short.status_code == 422

        # 3. Valid HTML content is extracted and stored with sha256 ref and real facts
        mock_good_resp = MagicMock()
        mock_good_resp.status_code = 200
        mock_good_resp.url = "https://example.com/ai-report"
        mock_good_resp.text = (
            "<html><head><title>Rapport IA 2026</title></head><body>"
            "<p>L'industrialisation des systèmes multi-agents en entreprise permet une réduction "
            "de 45% des incidents de conformité grâce aux contrôles déterministes.</p>"
            "</body></html>"
        )
        with patch("apps.api.routers.sources.fetch_safe_url", return_value=mock_good_resp):
            resp_ok = client.post(
                "/v1/sources",
                json={"type": "url", "url": "https://example.com/ai-report"},
            )
            assert resp_ok.status_code == 200
            body = resp_ok.json()
            assert body["raw_content_ref"].startswith("sha256:")
            assert body["provenance"]["extraction_status"] == "extracted"
            assert "Contenu automatique extrait depuis" not in body["provenance"].get("content_preview", "")
            assert len(body["extracted_facts"]) >= 1
    finally:
        app.dependency_overrides.pop(get_current_user, None)

