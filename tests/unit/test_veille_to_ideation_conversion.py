from fastapi.testclient import TestClient
from apps.api.main import app
from packages.security.auth import create_access_token
from infra.db.database import SessionLocal
from infra.db.repository import ContentOpsRepository

client = TestClient(app)


def test_signal_to_idea_transactional_conversion_and_idempotency():
    db = SessionLocal()
    repo = ContentOpsRepository(db)

    ws_id = "ws_test_conv"
    # Ensure workspace exists
    ws = repo.get_workspace(ws_id)
    if not ws:
        repo.create_workspace(name="Test Conv WS", timezone="UTC", owner_id="user_conv")
        # Ensure ID matches
        ws_obj = repo.get_workspace(ws_id)
        if not ws_obj:
            from infra.db.models import WorkspaceModel
            db.add(WorkspaceModel(id=ws_id, name="Test Conv WS", owner_id="user_conv"))
            db.commit()

    token = create_access_token("user_conv", "Owner", ws_id)
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Create a qualified signal
    signal = repo.save_signal(
        workspace_id=ws_id,
        title="GLM-5.3 Foundation Model Architecture",
        canonical_url="https://z-ai.org/blog/glm-5-3",
        summary="Z.ai launches GLM-5.3 with native deep reasoning and MoE architecture.",
        axis="ia",
        trust_level="A",
        qualification_score=4.8,
        qualification_criteria={"authority": 1.0, "freshness": 1.0, "fact_density": 1.0},
        facts=[
            {"fact": "128k token context window", "source_url": "https://z-ai.org/blog/glm-5-3", "quote": "128k tokens"},
            {"fact": "Native deep reasoning", "source_url": "https://z-ai.org/blog/glm-5-3", "quote": "reasoning tokens"}
        ],
        executive_takeaway="Un modèle souverain haute performance pour le déploiement d'agents d'entreprise.",
        status="QUALIFIED"
    )

    # 2. Convert signal to idea via endpoint
    res = client.post(f"/v1/signals/{signal.id}/convert", headers=headers)
    assert res.status_code == 201
    data = res.json()
    assert data["success"] is True
    idea = data["idea"]
    assert idea["signal_id"] == signal.id
    assert idea["title"] == signal.title
    assert idea["pillar"] == "IA générative & LLMs"
    assert len(idea["evidence_refs"]) >= 2
    assert idea["evidence_refs"][0]["verified"] is True
    assert idea["priority"] == "high"

    # 3. Verify signal status is updated to CONVERTED
    db.expire_all()
    updated_signal = repo.get_signal(signal.id, ws_id)
    assert updated_signal.status == "CONVERTED"

    # 4. Idempotency test: calling convert a second time returns the SAME idea without creating a duplicate
    res_repeat = client.post(f"/v1/signals/{signal.id}/convert", headers=headers)
    assert res_repeat.status_code == 201
    data_repeat = res_repeat.json()
    assert data_repeat["idea"]["id"] == idea["id"]

    all_ideas = repo.list_ideas(ws_id)
    matching_ideas = [i for i in all_ideas if i.signal_id == signal.id]
    assert len(matching_ideas) == 1, "Must not duplicate ideas for the same signal"

    # 5. Non-eligible signal test (REJECTED)
    rejected_signal = repo.save_signal(
        workspace_id=ws_id,
        title="Fake rumors signal",
        canonical_url="https://spam.example.com",
        summary="Unverified rumors",
        axis="ia",
        trust_level="C",
        qualification_score=1.5,
        qualification_criteria={},
        facts=[],
        executive_takeaway="N/A",
        status="REJECTED"
    )
    res_rejected = client.post(f"/v1/signals/{rejected_signal.id}/convert", headers=headers)
    assert res_rejected.status_code == 400
    assert "rejeté" in res_rejected.json()["detail"].lower()

    # 6. Inter-tenant isolation test: another workspace cannot convert this signal
    foreign_token = create_access_token("other_user", "Owner", "ws_other_tenant")
    res_foreign = client.post(f"/v1/signals/{signal.id}/convert", headers={"Authorization": f"Bearer {foreign_token}"})
    assert res_foreign.status_code == 400 or res_foreign.status_code == 404
    assert "introuvable" in res_foreign.json()["detail"].lower()

    db.close()
