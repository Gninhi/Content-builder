import uuid
from datetime import datetime, timedelta, timezone
from infra.db.database import get_db_session
from infra.db.repository import ContentOpsRepository
from infra.db.models import VeilleRunModel
from services.orchestration.memory import (
    ShortTermGraphMemory,
    WorkspaceMemoryService,
    EvidenceMemoryService,
)


def test_short_term_memory_thread_isolation_and_pruning():
    """Lot 5 (Section 9.1): Verify workspace-scoped deterministic thread_id and state pruning."""
    tid_a = ShortTermGraphMemory.build_thread_id("ws_alpha", "content_production", "brief_1")
    tid_b = ShortTermGraphMemory.build_thread_id("ws_beta", "content_production", "brief_1")
    assert tid_a == "ws_alpha:content_production:brief_1"
    assert tid_b == "ws_beta:content_production:brief_1"
    assert tid_a != tid_b
    assert ShortTermGraphMemory.validate_thread_ownership(tid_a, "ws_alpha") is True
    assert ShortTermGraphMemory.validate_thread_ownership(tid_a, "ws_beta") is False

    noisy_state = {
        "workspace_id": "ws_alpha",
        "raw_html": "<html><body>Huge page</body></html>",
        "raw_sources": [
            {"url": "https://example.com", "raw_html": "<script>x</script>", "content": "A" * 5000}
        ],
    }
    pruned = ShortTermGraphMemory.prune_state_for_checkpoint(noisy_state, max_text_len=500)
    assert "raw_html" not in pruned
    assert "raw_html" not in pruned["raw_sources"][0]
    assert len(pruned["raw_sources"][0]["content"]) == 500


def test_workspace_memory_isolation_and_propositional_learning():
    """Lot 5 (Section 9.2): Verify WorkspaceMemoryService isolates tenants and never auto-mutates BrandProfileModel."""
    with get_db_session() as db:
        repo = ContentOpsRepository(db)
        ws_a = repo.create_workspace("Memory WS A", "UTC", "owner_mem_a")
        ws_b = repo.create_workspace("Memory WS B", "UTC", "owner_mem_b")

        repo.create_or_version_brand_profile(
            workspace_id=ws_a.id,
            audience=["CISO", "CTO"],
            voice="Sobre et analytique",
            pillars=["Cybersécurité IA"],
            prohibited_topics=["hype non vérifiée"],
            cta_policy={"allowed_ctas": ["Demandez l'audit"]},
        )
        repo.create_or_version_brand_profile(
            workspace_id=ws_b.id,
            audience=["Growth Marketers"],
            voice="Énergique",
            pillars=["Automatisation"],
            prohibited_topics=["jargon technique"],
            cta_policy={"allowed_ctas": ["Testez maintenant"]},
        )

        mem_service = WorkspaceMemoryService(db)
        mem_a = mem_service.get_editorial_memory(ws_a.id)
        mem_b = mem_service.get_editorial_memory(ws_b.id)

        assert mem_a["brand_voice"] == "Sobre et analytique"
        assert "Cybersécurité IA" in mem_a["pillars"]
        assert mem_b["brand_voice"] == "Énergique"
        assert "Cybersécurité IA" not in mem_b["pillars"]

        # Propositional learning (ADR 0006): must NOT auto-mutate BrandProfileModel in DB
        proposal = mem_service.propose_brand_profile_adjustment(
            workspace_id=ws_a.id,
            proposed_voice="Encore plus concis",
            rationale="Les relecteurs raccourcissent systématiquement les phrases.",
        )
        assert proposal["status"] == "PROPOSED_FOR_HUMAN_REVIEW"
        assert proposal["auto_applied"] is False

        latest_bp_a = repo.get_latest_brand_profile(ws_a.id)
        assert latest_bp_a.voice == "Sobre et analytique"
        assert latest_bp_a.version == 1


def test_evidence_memory_isolation_and_retention_purge():
    """Lot 5 (Section 9.3 & 9.4): Verify EvidenceMemoryService isolates workspace signals and purges expired runs."""
    with get_db_session() as db:
        repo = ContentOpsRepository(db)
        ws_a = repo.create_workspace("Evidence WS A", "UTC", "owner_ev_a")
        ws_b = repo.create_workspace("Evidence WS B", "UTC", "owner_ev_b")

        repo.save_signal(
            workspace_id=ws_a.id,
            title="Signal Confidentiel WS A",
            summary="Données exclusives pour le tenant A sur LangGraph.",
            axis="ia",
            trust_level="A",
            qualification_score=4.5,
            qualification_criteria={"trust": 1.2},
            facts=[{"fact": "Fait vérifié A1", "quote": "LangGraph"}],
            executive_takeaway="Impact majeur A",
            canonical_url=f"https://example.com/ws-a-{uuid.uuid4().hex[:6]}",
            enrichment_status="ENRICHED",
        )
        repo.save_signal(
            workspace_id=ws_b.id,
            title="Signal Confidentiel WS B",
            summary="Données exclusives pour le tenant B.",
            axis="frameworks",
            trust_level="A",
            qualification_score=4.6,
            qualification_criteria={"trust": 1.2},
            facts=[{"fact": "Fait vérifié B1", "quote": "tenant B"}],
            executive_takeaway="Impact majeur B",
            canonical_url=f"https://example.com/ws-b-{uuid.uuid4().hex[:6]}",
            enrichment_status="ENRICHED",
        )

        ev_service = EvidenceMemoryService(db)
        dossier_a = ev_service.get_verified_evidence_dossier(ws_a.id)
        assert len(dossier_a) == 1
        assert dossier_a[0]["title"] == "Signal Confidentiel WS A"

        # Add an old VeilleRunModel (120 days ago) and a recent one (2 days ago)
        old_run = VeilleRunModel(
            id=f"vrun_old_{uuid.uuid4().hex[:8]}",
            workspace_id=ws_a.id,
            trigger_type="scheduled",
            status="COMPLETED",
            started_at=(datetime.now(timezone.utc) - timedelta(days=120)).replace(tzinfo=None),
        )
        recent_run = VeilleRunModel(
            id=f"vrun_rec_{uuid.uuid4().hex[:8]}",
            workspace_id=ws_a.id,
            trigger_type="manual",
            status="COMPLETED",
            started_at=(datetime.now(timezone.utc) - timedelta(days=2)).replace(tzinfo=None),
        )
        db.add(old_run)
        db.add(recent_run)
        db.commit()

        purged_count = ev_service.purge_expired_runs(ws_a.id, retention_days=90)
        assert purged_count == 1
        remaining = db.query(VeilleRunModel).filter(VeilleRunModel.workspace_id == ws_a.id).all()
        assert len(remaining) == 1
        assert remaining[0].id == recent_run.id
