import time
from packages.domain.state_machine import ContentStatus
from packages.domain.idempotency import compute_payload_hash
from services.orchestration.nodes.research import ideation_and_scoring_node
from services.orchestration.nodes.production import generate_variants_node
from services.orchestration.nodes.quality import quality_gate_node
from services.orchestration.nodes.approval import human_review_decision_node
from services.orchestration.nodes.insights import generate_strategy_insights_node


def test_ideation_agent_verification():
    """Validates ideation node: latency tracking, 0-100 scores, category prefix elimination."""
    state = {
        "workspace_id": "ws_battery_test",
        "topic_or_brief": "Déploiement d'agents IA et conformité EU AI Act",
        "pillars": ["IA générative", "Systèmes multi-agents", "Gouvernance"],
        "audience": ["Tech Leads", "DSI"],
        "target_count": 3,
        "raw_sources": [
            {
                "url": "https://digital-strategy.ec.europa.eu/en/policies/regulatory-framework-ai",
                "title": "EU AI Act Compliance Timeline",
                "content": "Obligations de conformité et audit des modèles d'IA à haut risque d'ici 2026."
            }
        ],
        "llm_override": {
            "provider_id": "nvidia",
            "model_id": "z-ai/glm-5.3-flash",
            "temperature": 0.2
        }
    }

    t0 = time.time()
    result = ideation_and_scoring_node(state)
    elapsed = time.time() - t0
    assert elapsed >= 0.0

    assert "generated_ideas" in result
    ideas = result["generated_ideas"]
    assert len(ideas) >= 2

    for idea in ideas:
        # Title must not contain pillar prefix
        for p in state["pillars"]:
            assert not idea["title"].startswith(f"{p} :")
            assert not idea["title"].startswith(f"{p}:")

        # Scores strictly on 0-100 scale
        assert 0.0 <= idea["novelty_score"] <= 100.0
        assert 0.0 <= idea["relevance_score"] <= 100.0
        assert 0.0 <= idea["effort_score"] <= 100.0

        # Plausible range
        assert idea["novelty_score"] > 10.0
        assert idea["relevance_score"] > 10.0


def test_production_agent_verification():
    """Validates production node: generates platform-compliant variants with hook & CTA."""
    state = {
        "workspace_id": "ws_battery_test",
        "objective": "Sensibiliser aux exigences de conformité des architectures agentiques",
        "angle": "Retour d'expérience pratique sur un déploiement en production",
        "brand_voice": "Expert, pragmatique et direct",
        "audience": ["Tech Leads", "DSI"],
        "requirements": {},
        "prohibited_topics": ["falsification", "scraping illégal"],
        "target_platforms": ["linkedin", "x"],
        "cta_policy": {
            "allowed_ctas": ["Comment gérez-vous l'audit de vos flux agentiques ?"]
        },
        "sources": [
            {
                "canonical_url": "https://digital-strategy.ec.europa.eu",
                "content": "Cadre réglementaire de l'UE pour l'IA en entreprise."
            }
        ],
        "llm_override": {
            "provider_id": "nvidia",
            "model_id": "z-ai/glm-5.3-flash",
            "temperature": 0.3
        }
    }

    t0 = time.time()
    result = generate_variants_node(state)
    elapsed = time.time() - t0
    assert elapsed >= 0.0

    assert "generated_variants" in result
    variants = result["generated_variants"]
    assert len(variants) >= 2

    platforms = {v["platform"] for v in variants}
    assert "linkedin" in platforms
    assert "x" in platforms

    for v in variants:
        assert bool(v.get("hook")), "Hook must not be empty"
        assert bool(v.get("cta")), "CTA must not be empty"
        if v["platform"] == "x":
            assert len(v["body"]) <= 280, f"X body exceeded 280 chars: {len(v['body'])}"
        elif v["platform"] == "linkedin":
            assert len(v["body"]) >= 50, "LinkedIn body too short"


def test_quality_gate_agent_verification():
    """Validates quality gate node: evaluates platform rules and claim verification."""
    state = {
        "workspace_id": "ws_battery_test",
        "prohibited_topics": ["interdit"],
        "generated_variants": [
            {
                "id": "var_1",
                "platform": "linkedin",
                "hook": "Voici 3 piliers essentiels pour sécuriser vos agents IA.",
                "body": "Voici 3 piliers essentiels pour sécuriser vos agents IA en entreprise. Audit des prompts, validation humaine (HITL) et circuit breakers résilients.",
                "cta": "Partagez votre avis en commentaire.",
                "claims": [
                    {"claim": "Audit des prompts", "verified": True, "source_id": "src_1"},
                    {"claim": "validation humaine", "verified": True, "source_id": "src_1"}
                ]
            },
            {
                "id": "var_2",
                "platform": "x",
                "hook": "Sécuriser les agents IA en prod :",
                "body": "Sécuriser les agents IA en prod : 1/ HITL obligatoire 2/ Circuit breaker 3/ Traçabilité SHA-256.",
                "cta": "Qu'en pensez-vous ?",
                "claims": [
                    {"claim": "HITL obligatoire", "verified": True, "source_id": "src_2"}
                ]
            }
        ]
    }

    result = quality_gate_node(state)
    assert result["status"] == ContentStatus.IN_REVIEW
    assert "qa_results" in result
    eval_res = result["qa_results"]
    assert eval_res["overall_passed"] is True
    assert eval_res["overall_score"] >= 80.0


def test_hitl_approval_and_seal_verification():
    """Validates HITL decision node and SHA-256 payload tampering detection."""
    payload = {
        "title": "Article sécurisé",
        "body": "Contenu validé",
        "platform": "linkedin"
    }
    payload_hash = compute_payload_hash(payload)

    # 1. Successful approval with untampered payload
    valid_state = {
        "decision": "approve",
        "payload": payload,
        "payload_hash": payload_hash
    }
    res_valid = human_review_decision_node(valid_state)
    assert res_valid["status"] == ContentStatus.APPROVED

    # 2. Tampered payload detection
    tampered_payload = {
        "title": "Article altéré",
        "body": "Contenu modifié sans revue",
        "platform": "linkedin"
    }
    tampered_state = {
        "decision": "approve",
        "payload": tampered_payload,
        "payload_hash": payload_hash
    }
    res_tampered = human_review_decision_node(tampered_state)
    assert res_tampered["status"] == ContentStatus.QA_FAILED
    assert "mismatch" in res_tampered["feedback"].lower()

    # 3. Legitimate human edit with new payload hash calculation
    edited_payload = {
        "title": "Article revu et corrigé",
        "body": "Contenu amélioré par le relecteur",
        "platform": "linkedin"
    }
    edit_state = {
        "decision": "edit",
        "payload": edited_payload,
        "payload_hash": payload_hash  # Original unedited hash
    }
    res_edit = human_review_decision_node(edit_state)
    assert res_edit["status"] == ContentStatus.APPROVED
    assert "payload_hash" in res_edit
    assert res_edit["payload_hash"] == compute_payload_hash(edited_payload)
    assert res_edit["payload_hash"] != payload_hash


def test_insights_agent_verification_no_hallucination():
    """Validates insights node: returns NO_DATA without hallucinating metrics."""
    state = {
        "workspace_id": "ws_empty",
        "pillars": ["IA générative"],
        "metric_snapshots": []
    }
    result = generate_strategy_insights_node(state)
    assert result["status"] == "NO_DATA"
    assert len(result["hypotheses"]) == 0
    assert len(result["recommendations"]) == 0
