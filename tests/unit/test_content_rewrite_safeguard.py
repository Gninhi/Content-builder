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
