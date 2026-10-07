import pytest
import json
from pathlib import Path
from fastapi.testclient import TestClient
from apps.api.main import app
from packages.security.auth import create_access_token, Role
from infra.db.database import init_db, SessionLocal
from infra.db.repository import ContentOpsRepository
from services.orchestration.nodes.research import ideation_and_scoring_node, get_llm_cache, compute_cache_key

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_tenants():
    init_db()
    db = SessionLocal()
    try:
        repo = ContentOpsRepository(db)
        if not repo.get_workspace("ws_victim"):
            repo.create_workspace("Victim Corp", owner_id="owner_victim").id = "ws_victim"
            db.commit()
            repo.create_or_version_brand_profile("ws_victim", ["Enterprise"], "Corporate", ["Cybersecurity"], [], {})
        if not repo.get_workspace("ws_attacker"):
            repo.create_workspace("Attacker Corp", owner_id="owner_attacker").id = "ws_attacker"
            db.commit()
            repo.create_or_version_brand_profile("ws_attacker", ["Hacker"], "Hostile", ["Exploits"], [], {})
    finally:
        db.close()


def test_reproduce_sec_v2_01_dev_token_default_env(monkeypatch):
    """
    CRITIQUE SEC-V2-01: When ENV is not defined, /v1/auth/dev-token must FAIL with 403.
    Current buggy behavior: os.getenv('ENV', 'dev') defaults to 'dev' and allows forging tokens!
    """
    monkeypatch.delenv("ENV", raising=False)
    response = client.post(
        "/v1/auth/dev-token",
        json={"user_id": "attacker", "role": "Owner", "workspace_id": "ws_victim"}
    )
    # Production ready expectation: MUST be 403 Forbidden when ENV is not explicitly 'dev'
    assert response.status_code == 403, (
        f"VULNERABILITY REPRODUCED: Unset ENV allowed dev-token generation with status {response.status_code}"
    )


def test_reproduce_sec_v2_02_owner_cross_tenant_bola():
    """
    CRITIQUE SEC-V2-02: Owner of ws_attacker must NOT be able to view or manipulate ws_victim brand profile.
    Current buggy behavior: user.role.lower() != 'owner' bypasses tenant isolation!
    """
    attacker_owner_token = create_access_token(
        user_id="attacker_owner",
        role=Role.OWNER,
        workspace_id="ws_attacker"
    )

    response = client.get(
        "/v1/brand-profiles/ws_victim",
        headers={"Authorization": f"Bearer {attacker_owner_token}"}
    )
    # Production ready expectation: MUST be 403 Forbidden
    assert response.status_code == 403, (
        f"VULNERABILITY REPRODUCED: Attacker Owner accessed victim brand profile with status {response.status_code}"
    )


def test_reproduce_sec_v2_06_mass_assignment_brief_creation():
    """
    ELEVEE SEC-V2-06: Attacker with ws_attacker token must NOT be able to create a brief under ws_victim.
    Current buggy behavior: /v1/briefs blindly trusts req.workspace_id from the body!
    """
    attacker_token = create_access_token(
        user_id="attacker_editor",
        role=Role.EDITOR,
        workspace_id="ws_attacker"
    )

    response = client.post(
        "/v1/briefs",
        headers={"Authorization": f"Bearer {attacker_token}"},
        json={
            "workspace_id": "ws_victim",  # Cross-tenant injection attempt!
            "objective": "Malicious injected campaign into victim tenant",
            "platform_targets": ["linkedin"],
            "requirements": {}
        }
    )
    # Production ready expectation: MUST reject with 403 Forbidden because req.workspace_id != user.workspace_id
    assert response.status_code == 403, (
        f"VULNERABILITY REPRODUCED: Attacker created brief in victim tenant with status {response.status_code}"
    )


def test_reproduce_sec_v2_07_unauthenticated_sources_leak():
    """
    ELEVEE SEC-V2-07: GET /v1/sources must require authentication and reject unauthenticated calls.
    Current buggy behavior: GET /v1/sources has no auth dependency and leaks all sources.
    """
    response = client.get("/v1/sources?workspace_id=ws_victim")
    assert response.status_code in (401, 403), (
        f"VULNERABILITY REPRODUCED: Unauthenticated GET /v1/sources succeeded with status {response.status_code}"
    )


def test_reproduce_sec_v2_05_cross_tenant_cache_leak():
    """
    ELEVEE SEC-V2-05: LLM cache payload must include workspace_id.
    Current buggy behavior: Tenant Attacker receives Tenant Victim's cached output!
    """
    cache = get_llm_cache()
    topic = "confidential_mna_strategy"
    pillars = ["finance"]
    audience = ["executives"]
    
    # Direct cache injection representing victim's proprietary generated ideas
    victim_cache_payload = {
        "topic": topic.strip().lower(),
        "pillars": sorted(pillars),
        "audience": sorted(audience),
        "target_count": 10
    }
    key_without_tenant = compute_cache_key("idea_research", victim_cache_payload)
    cache.set(key_without_tenant, {
        "generated_ideas": [{"title": "Confidential Victim Strategy: Project Titan", "angle": "Secret"}]
    })

    # Attacker asks for ideas on the same topic under ws_attacker
    attacker_state = {
        "workspace_id": "ws_attacker",
        "topic_or_brief": topic,
        "pillars": pillars,
        "audience": audience,
        "target_count": 2,
        "raw_sources": [],
        "errors": []
    }
    attacker_result = ideation_and_scoring_node(attacker_state)

    # In production, attacker MUST NOT receive victim's cached idea!
    # If attacker_result["cached"] is True and contains "Confidential Victim Strategy", leak is proven!
    ideas = attacker_result.get("generated_ideas", [])
    has_leak = any("Confidential Victim Strategy" in i.get("title", "") for i in ideas)
    assert not has_leak, "VULNERABILITY REPRODUCED: Cross-tenant cache leak detected in idea_research_node!"


def test_reproduce_fin_v2_01_pricing_underestimation():
    """
    ELEVEE FIN-V2-01: Pricing in config/pricing.json must match official Google Gemini 3.8 Flash rates.
    Current buggy behavior: pricing is configured at 0.075 / 0.30 instead of 0.75 / 3.75!
    """
    pricing_file = Path("config/pricing.json")
    assert pricing_file.exists(), "Pricing file missing"
    with open(pricing_file, "r") as f:
        pricing_data = json.load(f)
    
    flash_38 = pricing_data.get("models", {}).get("gemini-3.8-flash", {})
    input_1m = flash_38.get("input_per_1m", 0.0)
    output_1m = flash_38.get("output_per_1m", 0.0)

    # Official rates per ai.google.dev/pricing: $0.75 / 1M input, $3.75 / 1M output
    assert input_1m == 0.75, f"VULNERABILITY REPRODUCED: Gemini 3.8 Flash input price is {input_1m}, expected 0.75"
    assert output_1m == 3.75, f"VULNERABILITY REPRODUCED: Gemini 3.8 Flash output price is {output_1m}, expected 3.75"
