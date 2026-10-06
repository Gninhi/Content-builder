import os
from unittest.mock import MagicMock, patch
from services.orchestration.llm import (
    get_gemini_model,
    is_gemini_available,
    GeneratedIdeasBatch,
    GeneratedIdea,
    GeneratedIdeaEvidence,
    GeneratedVariant,
    GeneratedClaim,
)
from packages.observability.tracing import ObservabilityTracer
from packages.observability.metrics import CostAndTokenEstimator
from packages.observability.pii import PIIRedactor
from infra.db.database import SessionLocal, init_db
from infra.db.repository import ContentOpsRepository
from infra.db.models import MetricSnapshotModel


def test_gemini_availability_and_instantiation():
    # Test unavailable when key is empty or default placeholder
    with patch.dict(os.environ, {"GOOGLE_API_KEY": ""}):
        assert is_gemini_available() is False
        assert get_gemini_model() is None

    with patch.dict(os.environ, {"GOOGLE_API_KEY": "your_api_key_placeholder"}):
        assert is_gemini_available() is False

    # Test available and model selection
    with patch.dict(os.environ, {
        "GOOGLE_API_KEY": "AIzaSyFakeKeyForUnitTests1234567890",
        "GEMINI_MODEL": "gemini-3.8-flash"
    }):
        assert is_gemini_available() is True
        model = get_gemini_model(model_type="fast")
        assert model is not None
        assert model.model == "gemini-3.8-flash"


def test_gemini_pydantic_structured_schemas():
    # Validate idea batch schema
    evidence = GeneratedIdeaEvidence(source_id="src_1", claim="IA déterministe réduit les erreurs.")
    idea = GeneratedIdea(
        title="Architecture LangGraph Gouvernée",
        angle="Retour d'expérience",
        target_audience="CTOs",
        recommended_formats=["linkedin", "x"],
        evidence=[evidence],
        novelty_score=8.5,
        relevance_score=9.0,
        effort_score=4.0,
        priority="high",
        risks=[]
    )
    batch = GeneratedIdeasBatch(ideas=[idea])
    assert len(batch.ideas) == 1
    assert batch.ideas[0].title == "Architecture LangGraph Gouvernée"

    # Validate variant schema
    claim = GeneratedClaim(claim="Validation humaine", source_id="src_1", verified=True, confidence_score=0.99)
    variant = GeneratedVariant(
        platform="linkedin",
        hook="Pourquoi les agents libres échouent en prod ?",
        body="Corps du post détaillé.",
        cta="Partagez votre avis.",
        hashtags=["#IA", "#LangGraph"],
        claims=[claim]
    )
    assert variant.platform == "linkedin"
    assert variant.claims[0].verified is True


def test_langfuse_tracing_and_scoring():
    with patch.dict(os.environ, {
        "LANGFUSE_PUBLIC_KEY": "pk-lf-test-12345678",
        "LANGFUSE_SECRET_KEY": "sk-lf-test-12345678",
        "LANGFUSE_HOST": "https://cloud.langfuse.com",
        "LANGFUSE_TRACING_ENABLED": "true"
    }):
        assert ObservabilityTracer.is_tracing_enabled() is True
        meta = ObservabilityTracer.get_run_metadata(
            workspace_id="ws_test",
            graph_name="idea_research_graph",
            node_name="ideation_and_scoring",
            extra_tags=["linkedin"]
        )
        assert meta["graph"] == "idea_research_graph"
        assert "linkedin" in meta["tags"]
        assert "run_id" in meta

        # Test score recording with mocked client
        mock_client = MagicMock()
        with patch.object(ObservabilityTracer, "get_langfuse_client", return_value=mock_client):
            success = ObservabilityTracer.record_score(
                name="human_approval",
                value=1.0,
                trace_id="trace_123",
                comment="Validé par l'éditeur"
            )
            assert success is True
            mock_client.create_score.assert_called_once_with(
                name="human_approval",
                value=1.0,
                trace_id="trace_123",
                comment="Validé par l'éditeur"
            )


def test_gemini_cost_estimator_and_pii_redactor():
    cost_info = CostAndTokenEstimator.estimate_cost(
        input_text="A" * 4000,   # ~1000 input tokens
        output_text="B" * 2000,  # ~500 output tokens
        model="gemini-3.8-flash"
    )
    assert cost_info["model"] == "gemini-3.8-flash"
    assert cost_info["input_tokens"] >= 900
    assert cost_info["estimated_cost_usd"] > 0

    # Test PII redactor for Google and Langfuse keys
    sensitive_text = "API keys: AIzaSyFakeSecret12345678901234567890 and pk-lf-abcdef1234567890 and test@example.com"
    redacted = PIIRedactor.redact(sensitive_text)
    assert "[REDACTED_GOOGLE_KEY]" in redacted
    assert "[REDACTED_LANGFUSE_PUBLIC_KEY]" in redacted
    assert "[REDACTED_EMAIL]" in redacted


def test_strategy_query_metric_snapshot_model_fixed():
    init_db()
    db = SessionLocal()
    try:
        repo = ContentOpsRepository(db)
        assert repo is not None
        # Directly query MetricSnapshotModel via session
        snapshots = db.query(MetricSnapshotModel).all()
        assert isinstance(snapshots, list)
    finally:
        db.close()
