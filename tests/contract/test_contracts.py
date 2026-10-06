import pytest
from packages.contracts.schemas import (
    WorkspaceCreate,
    BrandProfileCreate,
    IdeaItem,
    EvidenceItem,
    QAReviewResult
)
from packages.contracts.events import create_domain_event, DomainEvent


def test_contracts_schema_validation():
    workspace = WorkspaceCreate(name="Production Space", timezone="Europe/Paris", owner_id="owner_1")
    assert workspace.name == "Production Space"

    brand = BrandProfileCreate(
        workspace_id="ws_01",
        audience=["CTOs", "Engineers"],
        voice="Pragmatic",
        pillars=["Agents", "LLMs"],
        prohibited_topics=["Scams"]
    )
    assert len(brand.pillars) == 2

    idea = IdeaItem(
        title="Architecture LangGraph",
        angle="Retour d'expérience",
        target_audience="Engineers",
        recommended_formats=["linkedin"],
        evidence=[EvidenceItem(source_id="src_1", claim="Fait technique", confidence=0.9)],
        novelty_score=8.5,
        relevance_score=9.0,
        effort_score=3.5,
        priority="high",
        risks=[]
    )
    assert idea.novelty_score == 8.5


def test_domain_event_structure():
    event = create_domain_event(
        event_type="content.approved",
        workspace_id="ws_test",
        aggregate_id="var_123",
        actor_type="human",
        payload={"variant_id": "var_123", "decision": "approve"}
    )
    assert isinstance(event, DomainEvent)
    assert event.event_type == "content.approved"
    assert event.schema_version == "1.0"
    assert event.actor_type == "human"
    assert len(event.event_id) > 10
