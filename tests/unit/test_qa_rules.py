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
