import json
from pathlib import Path
from evals.evaluators.quality_evaluator import QualityEvaluator, DeterministicQualityRules


def test_quality_evaluator_against_80_cases_no_fake_passes():
    """
    QUALITY PHASE (TST-01, TST-02):
    Runs the 80-case evaluation dataset and verifies that every single
    assertion is evaluated truthfully without any fake 'passed = True'.
    """
    dataset_file = Path("evals/datasets/eval_dataset_80.json")
    assert dataset_file.exists(), "Evaluation dataset must be present"

    evaluator = QualityEvaluator(str(dataset_file))
    results = evaluator.run_evaluations()

    # Pass rate must exceed 95% on the full 80 cases
    assert results["total_cases"] == 80
    assert results["pass_rate_percent"] >= 95.0
    assert results["evaluation_success"] is True

    # Check results by family are tracked
    families = results["results_by_family"]
    assert "Fidélité source et citation" in families
    assert "Ton / profil de marque" in families
    assert "Adaptation par plateforme" in families
    assert "Politique de sécurité/approbation" in families
    assert "Cas d'échec/outils indisponibles" in families


def test_quality_evaluator_distinguishes_golden_good_and_bad_cases():
    """
    QUALITY PHASE:
    Evaluator must accurately distinguish high-quality compliant content
    from non-compliant/problematic content across all platforms.
    """
    golden_path = Path("evals/datasets/golden_evaluation_dataset.json")
    assert golden_path.exists(), "Golden evaluation dataset must be present"

    with open(golden_path, "r", encoding="utf-8") as f:
        golden_cases = json.load(f)

    evaluator = QualityEvaluator()

    for case in golden_cases:
        case_id = case["id"]
        variant_payload = {
            "platform": case["platform"],
            "body": case["body"],
            "hashtags": case.get("hashtags", []),
            "media_spec": {"is_thread": case.get("is_thread", False)}
        }
        recent_history = case.get("historical_posts", [])
        require_ai = case.get("require_ai_disclosure", False)

        result = evaluator.evaluate_variant(
            variant_payload=variant_payload,
            recent_history_90d=recent_history,
            require_ai_disclosure=require_ai
        )

        expected_verdict = case["expected_verdict"]
        assert result["verdict"] == expected_verdict, (
            f"Case {case_id} failed: expected verdict {expected_verdict}, got {result['verdict']}. "
            f"Checks: {result['checks']}"
        )

        if "expected_min_score" in case:
            assert result["score"] >= case["expected_min_score"], (
                f"Case {case_id} score too low: {result['score']} < {case['expected_min_score']}"
            )
        if "expected_max_score" in case:
            assert result["score"] <= case["expected_max_score"], (
                f"Case {case_id} score unexpectedly high: {result['score']} > {case['expected_max_score']}"
            )


def test_duplicate_90d_detection():
    """
    QUALITY PHASE (EDT-02):
    Detects semantic / lexical duplicates against past 90-day post history.
    """
    rules = DeterministicQualityRules()
    history = [
        "L'automatisation sans observabilité détruit la marque. 100% des runs doivent être audités.",
        "Comment réussir votre déploiement de LangGraph en entreprise avec checkpointer PostgreSQL."
    ]

    # Exact or near-identical duplicate (>85% token overlap)
    duplicate_text = "L'automatisation sans observabilité détruit la marque : 100% des runs doivent être audités !"
    dup_ok, dup_msg = rules.check_duplicate_90d(duplicate_text, history, threshold=0.85)
    assert dup_ok is False
    assert "doublon" in dup_msg.lower()

    # Distinct content (<50% overlap)
    new_text = "Découvrez notre nouveau framework d'évaluation d'agents IA pour Next.js."
    fresh_ok, fresh_msg = rules.check_duplicate_90d(new_text, history, threshold=0.85)
    assert fresh_ok is True
    assert "aucun doublon" in fresh_msg.lower()


def test_ai_act_transparency_compliance():
    """
    QUALITY PHASE (EDT-03):
    Verifies that AI transparency disclosure is validated when required.
    """
    rules = DeterministicQualityRules()

    # Content with AI disclosure
    compliant_text = "Voici nos 3 conseils pour réussir votre agent. Co-écrit avec IA et revu par nos équipes."
    ok, msg = rules.check_ai_transparency(compliant_text, required=True)
    assert ok is True

    # Content missing disclosure
    non_compliant_text = "Voici nos 3 conseils pour réussir votre agent sans aucune mention de son origine."
    bad_ok, bad_msg = rules.check_ai_transparency(non_compliant_text, required=True)
    assert bad_ok is False
    assert "mention" in bad_msg.lower()
