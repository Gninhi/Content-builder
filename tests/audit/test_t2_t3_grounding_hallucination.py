import json
from pathlib import Path
from unittest.mock import patch

from packages.prompts.veille_queries import compute_qualification_score
from services.orchestration.nodes.research import collect_sources_node, ideation_and_scoring_node
from packages.tools.schemas import WebSearchResponse


def test_t2_attribution_and_qualification_rubric_blindspot():
    """
    T2 AUDIT TEST: Vérification de la détection des fausses attributions
    et évaluation de la grille de qualification algorithmique.
    """
    dataset_path = Path(__file__).parent / "golden_signals_reference_dataset.json"
    with open(dataset_path, "r", encoding="utf-8") as f:
        bench_data = json.load(f)

    signals = bench_data["sample_50_signals"]
    erroneous_sig = next(s for s in signals if not s["attribution_correct"])

    # 1. Évaluation avec attribution non vérifiée (FND-07)
    q_unverified = compute_qualification_score(
        trust_level=erroneous_sig["trust_level"],
        days_old=3,
        has_concrete_facts=True,
        is_strategic=True,
        is_exec_relevant=True,
        attribution_verified=False
    )
    assert q_unverified["is_qualified"] is False, "Une fausse attribution doit être rejetée !"
    assert q_unverified["breakdown"]["requires_confirmation"] is True

    # 2. Évaluation avec attribution vérifiée (Harmonisation 3.2 FND-09)
    q_verified = compute_qualification_score(
        trust_level="A",
        days_old=2,
        has_concrete_facts=True,
        is_strategic=True,
        is_exec_relevant=True,
        attribution_verified=True
    )
    assert q_verified["is_qualified"] is True
    assert q_verified["score"] >= 3.2


def test_t3_hallucination_empty_sources_and_fabricated_claims():
    """
    T3 AUDIT TEST: Comportement en l'absence de sources (Correction FND-02 et FND-08).
    Vérifie qu'aucune idée n'est inventée et aucune fausse source n'est injectée.
    """
    state = {
        "workspace_id": "ws_audit_t3",
        "topic_or_brief": "SujetTotalementInconnuEtSansSource2026",
        "pillars": ["IA générative"],
        "audience": ["Tech Leads"],
        "target_count": 3,
        "raw_sources": [],
        "llm_override": None
    }

    # Simulation d'un moteur de recherche ne renvoyant aucun résultat
    empty_search_resp = WebSearchResponse(
        query="SujetTotalementInconnuEtSansSource2026",
        engine_used="serpapi",
        total_results=0,
        results=[],
        cost_usd=0.0,
        latency_ms=80.0,
        status="NO_DATA",
        error_message="Aucun résultat"
    )

    with patch("services.orchestration.nodes.research.WebSearchTool.search", return_value=empty_search_resp), \
         patch("services.orchestration.nodes.research.resolve_and_get_llm", return_value=(None, None)), \
         patch("services.orchestration.nodes.research.get_gemini_model", return_value=None):
        state_after_collect = collect_sources_node(state)
        # Aucune source n'a pu être trouvée
        assert len(state_after_collect["raw_sources"]) == 0

        # Exécution du noeud d'idéation
        merged_state = {**state, **state_after_collect}
        result = ideation_and_scoring_node(merged_state)

        # PREUVE DE LA CORRECTION (FND-02 & FND-08):
        # En l'absence de sources vérifiables, le système retourne status="NO_DATA",
        # aucune idée n'est fabriquée et aucune source factice n'est injectée.
        assert result.get("status") == "NO_DATA"
        assert "generated_ideas" in result
        assert len(result["generated_ideas"]) == 0
        assert "ec.europa.eu" not in str(result)
        assert "arxiv.org" not in str(result)
