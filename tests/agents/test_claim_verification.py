from packages.domain.state_machine import ContentStatus
from services.orchestration.nodes.quality import quality_gate_node
from services.orchestration.nodes.production import verify_claim_against_sources


def test_claim_verification_against_empty_sources():
    """C1: A claim generated with no matching sources must NOT be marked verified."""
    claim_text = "Notre chiffre d affaires a bondi de 350% en 2026."
    sources = []
    
    is_verified, confidence = verify_claim_against_sources(claim_text, sources)
    assert is_verified is False
    assert confidence < 0.5


def test_claim_verification_against_matching_sources():
    """C1: A claim matching source extracts is properly verified."""
    claim_text = "80% des projets IA échouent sans gouvernance éditoriale claire."
    sources = [
        {"content": "Une étude démontre que 80% des projets IA échouent sans gouvernance éditoriale claire dans les entreprises."}
    ]
    
    is_verified, confidence = verify_claim_against_sources(claim_text, sources)
    assert is_verified is True
    assert confidence >= 0.8


def test_quality_gate_fails_when_claim_is_unverified():
    """C1: Quality gate must fail when an unverified claim is present."""
    state = {
        "generated_variants": [
            {
                "platform": "linkedin",
                "hook": "Test hook",
                "body": "Test body avec une allégation non sourcée.",
                "cta": "Click here",
                "hashtags": ["#AI"],
                "claims": [
                    {
                        "claim": "Allégation mensongère hallucinée",
                        "source_id": "src_fake",
                        "verified": False,
                        "confidence_score": 0.2
                    }
                ]
            }
        ],
        "prohibited_topics": []
    }
    
    result = quality_gate_node(state)
    assert result["status"] == ContentStatus.QA_FAILED
    checks = result["generated_variants"][0]["checks"]
    claims_check = next(c for c in checks if c["rule_id"] == "FACTUAL_CLAIMS_VERIFIED")
    assert claims_check["passed"] is False
    assert "Allégation mensongère hallucinée" in claims_check["details"]
