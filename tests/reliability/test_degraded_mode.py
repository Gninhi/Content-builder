from datetime import datetime, timezone
import pytest
from services.orchestration.nodes.production import generate_variants_node
from services.publisher.worker import PublisherWorker
from infra.db.database import get_db_session
from infra.db.repository import ContentOpsRepository
from packages.domain.state_machine import ContentStatus
from packages.observability.tracing import ObservabilityTracer


def test_production_fallback_sets_degraded_flag_and_observability(monkeypatch):
    """
    RELIABILITY P0 (OBS-04, REL-05):
    When LLM fails or is unavailable, fallback must NOT be silent:
    - variant receives degraded=True
    - trace is tagged 'degraded'
    - dedicated degraded_fallback score is recorded
    """
    recorded_scores = []
    tagged_traces = []

    def mock_record_score(name, value, trace_id=None, comment=None):
        recorded_scores.append({"name": name, "value": value, "trace_id": trace_id})
        return True

    def mock_tag_trace(trace_id, tags):
        tagged_traces.append({"trace_id": trace_id, "tags": tags})
        return True

    monkeypatch.setattr(ObservabilityTracer, "record_score", mock_record_score)
    monkeypatch.setattr(ObservabilityTracer, "tag_trace", mock_tag_trace)
    # Ensure get_gemini_model returns None to trigger fallback
    monkeypatch.setattr("services.orchestration.nodes.production.get_gemini_model", lambda **kwargs: None)

    state = {
        "workspace_id": "ws_degraded_test",
        "brief_id": "brief_123",
        "objective": "Démonstration mode dégradé",
        "angle": "Fiabilité opérationnelle",
        "audience": "Ingénieurs",
        "requirements": {},
        "voice": "Direct",
        "prohibited_topics": [],
        "cta_policy": {},
        "target_platforms": ["linkedin"],
        "source_evidence_pool": []
    }

    result = generate_variants_node(state)
    variants = result.get("generated_variants", [])
    assert len(variants) > 0
    variant = variants[0]

    # Must be explicitly marked degraded
    assert variant.get("degraded") is True
    assert "degraded" in result.get("tags", []) or any("degraded" in item["tags"] for item in tagged_traces)

    # Score must be recorded
    degraded_scores = [s for s in recorded_scores if s["name"] == "degraded_fallback"]
    assert len(degraded_scores) == 1
    assert degraded_scores[0]["value"] == 1.0


def test_degraded_variant_blocks_automated_publication():
    """
    RELIABILITY P0:
    Any content marked degraded=True MUST block automated publishing without human approval.
    """
    with get_db_session() as db:
        repo = ContentOpsRepository(db)
        ws = repo.create_workspace("Degraded Guard WS", "UTC", "owner_deg")
        brief = repo.create_brief(workspace_id=ws.id, objective="Obj Degraded", platform_targets=["linkedin"])
        pkg = repo.create_content_package(brief.id, 1)

        # Variant with degraded=True
        var = repo.add_variant(
            package_id=pkg.id,
            platform="linkedin",
            hook="Hook degraded",
            body="Contenu dégradé nécessitant impérativement une validation humaine.",
            cta="CTA",
            hashtags=["#degraded"],
            degraded=True
        )
        var.status = ContentStatus.IN_REVIEW.value
        db.commit()

        # Approval performed by an automated/system account (not human)
        repo.record_approval(variant_id=var.id, decision="approve", reviewer_id="system", workspace_id=ws.id)
        job = repo.schedule_publication(workspace_id=ws.id, variant_id=var.id, scheduled_at=datetime.now(timezone.utc))

        worker = PublisherWorker(db)
        # Automated publication MUST be blocked
        with pytest.raises(ValueError) as exc_info:
            worker.execute_job(job.id)

        assert "degraded" in str(exc_info.value).lower()
        assert "human" in str(exc_info.value).lower() or "humain" in str(exc_info.value).lower()
