
from infra.db.database import get_db_session
from infra.db.repository import ContentOpsRepository
from services.orchestration.nodes.research import _clean_title, _normalize_score_100, ideation_and_scoring_node
from services.orchestration.nodes.insights import generate_strategy_insights_node


def test_clean_title_removes_category_prefixes():
    pillars = ["IA générative", "Systèmes multi-agents", "Automatisation"]
    
    assert _clean_title("IA générative : Pourquoi les agents échouent", pillars) == "Pourquoi les agents échouent"
    assert _clean_title("Systèmes multi-agents: Architecture de référence", pillars) == "Architecture de référence"
    assert _clean_title("Automatisation : ROI et gains mesurables", pillars) == "ROI et gains mesurables"
    assert _clean_title("Gouvernance et audit de conformité", pillars) == "Gouvernance et audit de conformité"


def test_normalize_score_100():
    assert _normalize_score_100(8.5) == 85.0
    assert _normalize_score_100(9.2) == 92.0
    assert _normalize_score_100(92.0) == 92.0
    assert _normalize_score_100(0.0) == 0.0
    assert _normalize_score_100(100.0) == 100.0


def test_insights_node_returns_no_data_when_no_snapshots():
    state = {
        "workspace_id": "ws_empty_metrics",
        "pillars": ["IA générative"],
        "metric_snapshots": []
    }
    result = generate_strategy_insights_node(state)
    assert result["status"] == "NO_DATA"
    assert len(result["hypotheses"]) == 0
    assert len(result["recommendations"]) == 0


def test_research_node_outputs_0_to_100_scores_and_clean_titles():
    state = {
        "workspace_id": "ws_test_research",
        "topic_or_brief": "Agents autonomes et gouvernance",
        "pillars": ["IA générative", "Systèmes multi-agents"],
        "audience": ["Tech Leads", "DSI"],
        "target_count": 3,
        "raw_sources": [
            {"url": "https://digital-strategy.ec.europa.eu", "content": "Régulation des modèles IA"}
        ]
    }
    result = ideation_and_scoring_node(state)
    ideas = result["generated_ideas"]
    assert len(ideas) >= 3

    for idea in ideas:
        # Title must NOT start with pillar prefix
        for p in state["pillars"]:
            assert not idea["title"].startswith(f"{p} :")
        # Scores must be 0-100 scale
        assert 0.0 <= idea["novelty_score"] <= 100.0
        assert 0.0 <= idea["relevance_score"] <= 100.0
        assert 0.0 <= idea["effort_score"] <= 100.0
        # If fallback, scores are around 70-95
        assert idea["novelty_score"] > 10.0


def test_idea_deduplication_in_repository():
    with get_db_session() as db:
        repo = ContentOpsRepository(db)
        idea1 = repo.save_idea(
            workspace_id="ws_dedup_test",
            title="Titre Unique pour Test Déduplication",
            angle="Angle 1",
            pillar="IA",
            audience="DSI",
            evidence_refs=[],
            novelty_score=85.0,
            relevance_score=90.0,
            effort_score=35.0,
            priority="high",
            risks=[],
            signal_id="sig_test_1"
        )
        assert idea1.id.startswith("idea_")

        # Saving identical title in same workspace must return existing
        idea2 = repo.save_idea(
            workspace_id="ws_dedup_test",
            title="Titre Unique pour Test Déduplication",
            angle="Angle 2 (différent)",
            pillar="IA",
            audience="DSI",
            evidence_refs=[],
            novelty_score=88.0,
            relevance_score=92.0,
            effort_score=40.0,
            priority="high",
            risks=[],
            signal_id="sig_test_2"
        )
        assert idea2.id == idea1.id

        listed = repo.list_ideas("ws_dedup_test")
        matching = [i for i in listed if i.title == "Titre Unique pour Test Déduplication"]
        assert len(matching) == 1
