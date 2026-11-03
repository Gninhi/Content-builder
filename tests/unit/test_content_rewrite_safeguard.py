from unittest.mock import patch
from fastapi.testclient import TestClient

from apps.api.main import app
from infra.db.database import get_db_session
from infra.db.repository import ContentOpsRepository
from packages.domain.state_machine import ContentStatus
from packages.domain.idempotency import compute_payload_hash
from packages.security.auth import create_access_token

client = TestClient(app, raise_server_exceptions=False)


def test_rewrite_never_injects_feedback_into_body_on_failure():
    """H8: If automated rewrite fails, feedback must NEVER be concatenated into public post body."""
    with get_db_session() as db:
        repo = ContentOpsRepository(db)
        ws = repo.create_workspace("Rewrite Guard WS", "UTC", "owner_rewrite")
        brief = repo.create_brief(workspace_id=ws.id, objective="Test Rewrite Guard", platform_targets=["linkedin"])
        pkg = repo.create_content_package(brief.id, 1)
        original_body = "Professional original body text."
        var = repo.add_variant(
            package_id=pkg.id,
            platform="linkedin",
            hook="Hook original",
            body=original_body,
            cta="CTA original",
            hashtags=["#Original"],
            media_spec={}
        )
        var.status = ContentStatus.IN_REVIEW.value
        db.commit()

        owner_token = create_access_token(user_id="owner_rewrite", role="Owner", workspace_id=ws.id)
        variant_id = var.id

    # Simulate LLM failure during rewrite
    with patch("apps.api.routers.content.resolve_and_get_llm", return_value=(None, None)), \
         patch("apps.api.routers.content.get_gemini_model", side_effect=RuntimeError("LLM unavailable")):
        res = client.post(
            f"/v1/content/{variant_id}/rewrite",
            headers={"Authorization": f"Bearer {owner_token}"},
            json={"feedback": "Confidential internal note: Remove claim X and lower price."}
        )

    # Must return an error status (502 or 503), NOT 200 with contaminated body
    assert res.status_code in (502, 503)

    # Verify database body was NOT contaminated
    with get_db_session() as db:
        from infra.db.models import ContentVariantModel
        reloaded_var = db.query(ContentVariantModel).filter(ContentVariantModel.id == variant_id).first()
        assert reloaded_var is not None
        assert "Confidential internal note" not in reloaded_var.body
        assert reloaded_var.body == original_body


def test_rewrite_hash_matches_publisher_canonical_hash():
    """H8: Rewrite payload hash must include platform and exactly match publisher canonical hash."""
    with get_db_session() as db:
        repo = ContentOpsRepository(db)
        ws = repo.create_workspace("Rewrite Hash WS", "UTC", "owner_hash")
        brief = repo.create_brief(workspace_id=ws.id, objective="Test Hash Match", platform_targets=["linkedin"])
        pkg = repo.create_content_package(brief.id, 1)
        var = repo.add_variant(
            package_id=pkg.id,
            platform="linkedin",
            hook="Hook hash test",
            body="Body hash test",
            cta="CTA hash test",
            hashtags=["#Test"],
            media_spec={"media_type": "image"}
        )
        var.status = ContentStatus.IN_REVIEW.value
        db.commit()

        owner_token = create_access_token(user_id="owner_hash", role="Owner", workspace_id=ws.id)
        variant_id = var.id

    from services.orchestration.llm import GeneratedVariant
    mock_revised = GeneratedVariant(
        platform="linkedin",
        hook="New Hook",
        body="New rewritten body content.",
        cta="New CTA",
        hashtags=["#Test"]
    )

    with patch("apps.api.routers.content.resolve_and_get_llm", return_value=("fake_model", None)), \
         patch("apps.api.routers.content.invoke_structured_output", return_value=mock_revised):
        res = client.post(
            f"/v1/content/{variant_id}/rewrite",
            headers={"Authorization": f"Bearer {owner_token}"},
            json={"feedback": "Make it punchier"}
        )

    assert res.status_code == 200
    data = res.json()
    new_hash = data["payload_hash"]

    # Compute expected canonical hash with platform
    expected_hash = compute_payload_hash({
        "platform": "linkedin",
        "hook": "New Hook",
        "body": "New rewritten body content.",
        "cta": "New CTA",
        "hashtags": ["#Test"],
        "media_spec": {"media_type": "image"}
    })

    assert new_hash == expected_hash
    assert data["qa_passed"] is True
    assert data["version"] == 2


def test_reflexive_production_loop_remediates_on_second_attempt():
    """Lot 3 (Section 7.1): Verify bounded reflexive loop retries once with QA feedback and passes."""
    from services.orchestration.graphs.content_production import graph as content_production_graph
    from services.orchestration.llm import GeneratedVariant, GeneratedClaim

    bad_variant = GeneratedVariant(
        platform="linkedin",
        hook="Accroche avec mot interdit",
        body="Ce post LinkedIn parle de crypto speculation sauvage en entreprise alors que c'est interdit par la charte.",
        cta="Partagez votre avis",
        hashtags=["#IA"],
        claims=[GeneratedClaim(claim="80% des projets IA", source_id="https://example.com", verified=True)],
    )
    good_variant = GeneratedVariant(
        platform="linkedin",
        hook="Gouvernance déterministe des agents IA",
        body="En production, 80% des projets IA réussissent grâce à une gouvernance déterministe, des contrôles qualité stricts et une validation humaine.",
        cta="Partagez votre avis",
        hashtags=["#IA"],
        claims=[GeneratedClaim(claim="80% des projets IA", source_id="https://example.com", verified=True)],
    )

    state = {
        "workspace_id": "ws_reflexive_test",
        "brief_id": "brief_ref_1",
        "objective": "Expliquer la gouvernance IA",
        "angle": "Retour terrain",
        "target_platforms": ["linkedin"],
        "brand_voice": "Expert",
        "prohibited_topics": ["crypto speculation"],
        "cta_policy": {"allowed_ctas": ["Partagez votre avis"]},
        "sources": [{"canonical_url": "https://example.com", "facts": ["80% des projets IA réussissent grâce à une gouvernance déterministe"]}],
        "requirements": {},
        "generated_variants": [],
        "qa_results": {},
        "status": ContentStatus.DRAFT,
        "run_id": "run_ref_1",
        "errors": [],
    }

    with patch("services.orchestration.nodes.production.resolve_and_get_llm", return_value=("fake_llm", None)), \
         patch("services.orchestration.nodes.production.invoke_structured_output", side_effect=[bad_variant, good_variant]) as mock_llm:
        result = content_production_graph.invoke(state)

    assert mock_llm.call_count == 2
    assert result["qa_attempt"] == 2
    assert result["status"] == ContentStatus.IN_REVIEW
    assert result["qa_results"]["overall_passed"] is True
    assert len(result["qa_feedback_history"]) == 1
    assert result["qa_feedback_history"][0]["rule_id"] == "BRAND_PROHIBITED_TOPICS"


def test_rewrite_enforces_quality_gate_on_prohibited_topic():
    """Lot 3 (Section 7.3): Rewrite endpoint cannot bypass Quality Gate when prohibited topics are present."""
    with get_db_session() as db:
        repo = ContentOpsRepository(db)
        ws = repo.create_workspace("Rewrite QA Gate WS", "UTC", "owner_qa_rw")
        repo.create_or_version_brand_profile(
            workspace_id=ws.id,
            audience=["DSI"],
            voice="Direct",
            pillars=["IA"],
            prohibited_topics=["competitor_bashing_xyz"],
            cta_policy={"allowed_ctas": ["Votre avis ?"]},
        )
        brief = repo.create_brief(workspace_id=ws.id, objective="Test Rewrite QA", platform_targets=["linkedin"])
        pkg = repo.create_content_package(brief.id, 1)
        var = repo.add_variant(
            package_id=pkg.id,
            platform="linkedin",
            hook="Hook initial valide",
            body="Corps initial parfaitement conforme à la politique éditoriale de l'entreprise.",
            cta="Votre avis ?",
            hashtags=["#IA"],
            media_spec={},
        )
        var.status = ContentStatus.IN_REVIEW.value
        db.commit()
        owner_token = create_access_token(user_id="owner_qa_rw", role="Owner", workspace_id=ws.id)
        variant_id = var.id

    from services.orchestration.llm import GeneratedVariant
    violating_rewrite = GeneratedVariant(
        platform="linkedin",
        hook="Hook réécrit",
        body="Ce post contient competitor_bashing_xyz malgré l'interdiction formelle de la marque.",
        cta="Votre avis ?",
        hashtags=["#IA"],
    )

    with patch("apps.api.routers.content.resolve_and_get_llm", return_value=("fake_model", None)), \
         patch("apps.api.routers.content.invoke_structured_output", return_value=violating_rewrite) as mock_inv:
        res = client.post(
            f"/v1/content/{variant_id}/rewrite",
            headers={"Authorization": f"Bearer {owner_token}"},
            json={"feedback": "Ajoute une comparaison"},
        )

    assert res.status_code == 200
    body = res.json()
    # Tried initial + 1 bounded retry = 2 calls
    assert mock_inv.call_count == 2
    assert body["status"] == "QA_FAILED"
    assert body["variant_status"] == ContentStatus.QA_FAILED.value
    assert body["qa_passed"] is False
    assert body["qa_attempts"] == 2

