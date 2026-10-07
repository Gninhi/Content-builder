from services.orchestration.nodes.quality import quality_gate_node
from packages.domain.state_machine import ContentStatus


def test_quality_gate_passes_clean_content():
    state = {
        "generated_variants": [
            {
                "platform": "linkedin",
                "hook": "Accroche percutante et claire pour LinkedIn.",
                "body": "Accroche percutante et claire pour LinkedIn.\n\nVoici le contenu structuré d'ingénierie et de retour d'expérience avec plus de cinquante caractères pour satisfaire les critères de longueur.",
                "cta": "Partagez votre avis en commentaire ci-dessous 👇",
                "hashtags": ["#Tech", "#AI"],
                "claims": [{"claim": "Fait vérifié", "source_id": "src_1", "verified": True}],
                "media_spec": {}
            }
        ],
        "prohibited_topics": ["crypto", "arnaque"]
    }
    result = quality_gate_node(state)
    assert result["qa_results"]["overall_passed"] is True
    assert result["status"] == ContentStatus.IN_REVIEW
    assert result["generated_variants"][0]["qa_score"] == 100.0


def test_quality_gate_fails_on_prohibited_topic():
    state = {
        "generated_variants": [
            {
                "platform": "linkedin",
                "hook": "Investissez dans la nouvelle crypto magique !",
                "body": "Investissez dans la nouvelle crypto magique ! C'est le meilleur moment pour devenir riche sans effort.",
                "cta": "Achetez maintenant",
                "hashtags": ["#Crypto"],
                "claims": [],
                "media_spec": {}
            }
        ],
        "prohibited_topics": ["crypto", "devenir riche"]
    }
    result = quality_gate_node(state)
    assert result["qa_results"]["overall_passed"] is False
    assert result["status"] == ContentStatus.QA_FAILED
    assert result["generated_variants"][0]["status"] == ContentStatus.QA_FAILED.value


def test_quality_gate_fails_on_x_length_exceeded():
    long_tweet = "A" * 290
    state = {
        "generated_variants": [
            {
                "platform": "x",
                "hook": "Hook de test",
                "body": long_tweet,
                "cta": "Cliquez ici",
                "hashtags": [],
                "claims": [],
                "media_spec": {"is_thread": False}
            }
        ],
        "prohibited_topics": []
    }
    result = quality_gate_node(state)
    assert result["qa_results"]["overall_passed"] is False
    assert result["status"] == ContentStatus.QA_FAILED


def test_quality_gate_enforces_ai_transparency_when_configured():
    """Verifies that EU AI Act transparency rule is enforced when require_ai_disclosure is True."""
    # 1. Variant without disclosure when required -> fails QA
    state_without = {
        "generated_variants": [
            {
                "platform": "linkedin",
                "hook": "Super accroche sur le machine learning",
                "body": "Super accroche sur le machine learning avec du contenu technique détaillé et vérifié.",
                "cta": "Laissez un commentaire ci-dessous",
                "hashtags": ["#Tech"],
                "claims": [{"claim": "ML fact", "source_id": "src_1", "verified": True}],
                "media_spec": {}
            }
        ],
        "prohibited_topics": [],
        "require_ai_disclosure": True
    }
    res_without = quality_gate_node(state_without)
    assert res_without["qa_results"]["overall_passed"] is False
    assert res_without["generated_variants"][0]["qa_passed"] is False
    checks = res_without["generated_variants"][0]["checks"]
    assert any(c["rule_id"] == "AI_ACT_TRANSPARENCY" and not c["passed"] for c in checks)

    # 2. Variant with disclosure -> passes QA
    state_with = {
        "generated_variants": [
            {
                "platform": "linkedin",
                "hook": "Super accroche sur le machine learning",
                "body": "Super accroche sur le machine learning avec du contenu technique détaillé et vérifié. Co-écrit avec IA.",
                "cta": "Laissez un commentaire ci-dessous",
                "hashtags": ["#Tech"],
                "claims": [{"claim": "ML fact", "source_id": "src_1", "verified": True}],
                "media_spec": {}
            }
        ],
        "prohibited_topics": [],
        "require_ai_disclosure": True
    }
    res_with = quality_gate_node(state_with)
    assert res_with["qa_results"]["overall_passed"] is True
    assert res_with["generated_variants"][0]["qa_passed"] is True
