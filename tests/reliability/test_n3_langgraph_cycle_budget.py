import pytest
import time
from unittest.mock import patch
from fastapi.testclient import TestClient
from packages.resilience.circuit_breaker import CycleBudget, BudgetExceededException
from services.orchestration.graphs.content_production import graph as content_production_graph
from services.orchestration.graphs.idea_research import graph as idea_research_graph
from packages.domain.state_machine import ContentStatus
from apps.api.main import app
from infra.db.database import get_db_session
from infra.db.repository import ContentOpsRepository
from infra.db.models import UserModel, WorkspaceMemberModel
from packages.security.auth import create_access_token


def test_content_production_graph_raises_when_token_budget_exceeded():
    """N3: LangGraph content production graph halts and raises BudgetExceededException on token limit."""
    budget = CycleBudget(max_tokens=100, max_duration_seconds=60.0)
    
    initial_state = {
        "workspace_id": "ws_test_budget",
        "brief_id": "brief_123",
        "objective": "Test Cycle Budget Token Limits",
        "angle": "Test Angle",
        "target_platforms": ["linkedin"],
        "brand_voice": "Direct",
        "prohibited_topics": [],
        "cta_policy": {},
        "sources": [{"canonical_url": "https://example.com/source", "facts": []}],
        "requirements": {},
        "generated_variants": [],
        "qa_results": {},
        "status": ContentStatus.DRAFT,
        "run_id": "test_run_token_budget",
        "errors": [],
        "cycle_budget": budget,
    }

    with pytest.raises(BudgetExceededException) as exc_info:
        content_production_graph.invoke(initial_state)

    assert "token budget" in str(exc_info.value).lower()


def test_content_production_graph_raises_when_duration_budget_exceeded():
    """N3: LangGraph content production graph halts and raises BudgetExceededException on duration limit."""
    budget = CycleBudget(max_tokens=50000, max_duration_seconds=0.01)
    time.sleep(0.02)  # force duration expiry

    initial_state = {
        "workspace_id": "ws_test_budget",
        "brief_id": "brief_123",
        "objective": "Test Cycle Budget Duration Limits",
        "angle": "Test Angle",
        "target_platforms": ["linkedin"],
        "brand_voice": "Direct",
        "prohibited_topics": [],
        "cta_policy": {},
        "sources": [{"canonical_url": "https://example.com/source", "facts": []}],
        "requirements": {},
        "generated_variants": [],
        "qa_results": {},
        "status": ContentStatus.DRAFT,
        "run_id": "test_run_duration_budget",
        "errors": [],
        "cycle_budget": budget,
    }

    with pytest.raises(BudgetExceededException) as exc_info:
        content_production_graph.invoke(initial_state)

    assert "duration limit" in str(exc_info.value).lower()


def test_idea_research_graph_raises_when_token_budget_exceeded():
    """N3: LangGraph idea research graph halts and raises BudgetExceededException on token limit."""
    budget = CycleBudget(max_tokens=50, max_duration_seconds=60.0)

    initial_state = {
        "workspace_id": "ws_test_budget",
        "topic_or_brief": "Agent Architectures",
        "pillars": ["AI", "Agents"],
        "audience": ["Engineers"],
        "target_count": 3,
        "raw_sources": [{"url": "https://example.com/article", "content": "Evidence content", "title": "Evidence"}],
        "generated_ideas": [],
        "run_id": "test_run_idea_budget",
        "errors": [],
        "cycle_budget": budget,
    }

    with pytest.raises(BudgetExceededException) as exc_info:
        idea_research_graph.invoke(initial_state)

    assert "token budget" in str(exc_info.value).lower()


def test_api_content_endpoint_returns_429_on_cycle_budget_exceeded():
    """N3: POST /v1/content/generate-variants returns HTTP 429 when CycleBudget is exceeded."""
    client = TestClient(app)

    # Seed user & workspace
    with get_db_session() as db:
        repo = ContentOpsRepository(db)
        user = db.query(UserModel).filter(UserModel.email == "budget_tester@example.com").first()
        if not user:
            user = UserModel(id="usr_budget_1", email="budget_tester@example.com", is_active=True)
            db.add(user)
            db.flush()

        ws = repo.create_workspace("Budget WS", "UTC", str(user.id))
        member = db.query(WorkspaceMemberModel).filter(
            WorkspaceMemberModel.workspace_id == ws.id,
            WorkspaceMemberModel.user_id == user.id
        ).first()
        if not member:
            member = WorkspaceMemberModel(workspace_id=ws.id, user_id=user.id, role="owner")
            db.add(member)
        brief = repo.create_brief(workspace_id=ws.id, objective="Test Budget 429", platform_targets=["linkedin"])
        db.commit()
        token = create_access_token(user_id=str(user.id), role="owner", workspace_id=ws.id)
        brief_id = brief.id
        ws_id = ws.id

    with patch.dict("os.environ", {"CYCLE_BUDGET_MAX_TOKENS": "10"}):
        resp = client.post(
            "/v1/content/generate",
            json={"brief_id": brief_id, "workspace_id": ws_id},
            headers={"Authorization": f"Bearer {token}"}
        )
        assert resp.status_code == 429
        assert "LLM cycle budget exceeded" in resp.json()["detail"]


def test_api_ideas_endpoint_returns_429_on_cycle_budget_exceeded():
    """N3: POST /v1/ideas/research returns HTTP 429 when CycleBudget is exceeded."""
    client = TestClient(app)

    with get_db_session() as db:
        repo = ContentOpsRepository(db)
        user = db.query(UserModel).filter(UserModel.email == "budget_tester_ideas@example.com").first()
        if not user:
            user = UserModel(id="usr_budget_ideas_1", email="budget_tester_ideas@example.com", is_active=True)
            db.add(user)
            db.flush()

        ws = repo.create_workspace("Budget WS Ideas", "UTC", str(user.id))
        member = db.query(WorkspaceMemberModel).filter(
            WorkspaceMemberModel.workspace_id == ws.id,
            WorkspaceMemberModel.user_id == user.id
        ).first()
        if not member:
            member = WorkspaceMemberModel(workspace_id=ws.id, user_id=user.id, role="owner")
            db.add(member)
        repo.add_source(
            workspace_id=ws.id,
            source_type="article",
            raw_content_ref="ref_test",
            extracted_facts=[{"claim": "Grounded claim for testing budget"}],
            provenance={"author": "Test"},
            canonical_url="https://example.com/source_budget"
        )
        db.commit()
        token = create_access_token(user_id=str(user.id), role="owner", workspace_id=ws.id)
        ws_id = ws.id

    with patch.dict("os.environ", {"CYCLE_BUDGET_MAX_TOKENS": "10"}):
        resp = client.post(
            "/v1/ideas/research",
            json={"topic_or_brief": "Agent Systems", "target_count": 2, "workspace_id": ws_id},
            headers={"Authorization": f"Bearer {token}"}
        )
        assert resp.status_code == 429
        assert "LLM cycle budget exceeded" in resp.json()["detail"]

