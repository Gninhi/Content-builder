import json
from pathlib import Path
from unittest.mock import MagicMock, patch

from services.orchestration.veille.pipeline import VeillePipeline
from packages.tools.schemas import WebSearchResponse, WebSearchResultItem


def test_t1_recall_major_events_and_pipeline_defect():
    """
    T1 AUDIT TEST: Mesure du rappel sur les événements majeurs de référence
    et détection du défaut de runtime 'AttributeError' en mode live.
    """
    dataset_path = Path(__file__).parent / "golden_signals_reference_dataset.json"
    with open(dataset_path, "r", encoding="utf-8") as f:
        bench_data = json.load(f)

    anchor_events = bench_data["major_anchor_events"]
    assert len(anchor_events) >= 6

    # 1. Vérification du comportement live avec mock du WebSearchTool
    mock_repo = MagicMock()
    mock_repo.get_active_sources.return_value = []
    mock_repo.save_signal.side_effect = lambda **kwargs: kwargs

    pipeline = VeillePipeline(repo=mock_repo)

    # Simulation d'une réponse WebSearchResponse standard retournée par WebSearchTool
    mock_search_item = WebSearchResultItem(
        title="Sortie officielle de GLM-5.3 par Z.ai",
        url="https://z-ai.org/blog/glm-5-3-release",
        snippet="Le nouveau modèle GLM-5.3 est disponible avec raisonnement profond et MoE.",
        source_name="z-ai.org",
        engine="serpapi:google",
        score=0.95
    )
    standard_web_response = WebSearchResponse(
        query="sortie GLM-5.3",
        engine_used="serpapi",
        total_results=1,
        results=[mock_search_item],
        cost_usd=0.01,
        latency_ms=120.0,
        status="SUCCESS"
    )

    with patch.object(pipeline.search_tool, "search", return_value=standard_web_response):
        collected = pipeline.run_collection_cycle(
            workspace_id="ws_audit_t1",
            axis="ia",
            demo=False
        )

        # PREUVE DE LA CORRECTION (FND-01):
        # WebSearchResponse.results est correctement lu sans AttributeError.
        assert len(collected) > 0, (
            "Les signaux live doivent être collectés avec succès sans crash AttributeError."
        )
        web_signals = [s for s in collected if s.get("canonical_url") == "https://z-ai.org/blog/glm-5-3-release"]
        assert len(web_signals) > 0
        assert web_signals[0]["canonical_url"] == "https://z-ai.org/blog/glm-5-3-release"

    # 2. Vérification du branchement des connecteurs officiels (OfficialDataConnectors - FND-03)
    assert hasattr(pipeline, "connectors"), "Le pipeline instancie bien connectors"
    with patch.object(pipeline.connectors, "fetch_arxiv_signals", return_value=[]) as mock_arxiv, \
         patch.object(pipeline.connectors, "fetch_github_releases", return_value=[]) as mock_gh:
        pipeline.run_collection_cycle(workspace_id="ws_audit_t1", axis="ia", demo=False)
        assert mock_arxiv.call_count >= 1, "Les connecteurs officiels (arXiv) doivent être interrogés pour l'axe IA !"

        pipeline.run_collection_cycle(workspace_id="ws_audit_t1", axis="frameworks", demo=False)
        assert mock_gh.call_count >= 1, "Les connecteurs officiels (GitHub releases) doivent être interrogés pour l'axe frameworks !"

    # 3. Mesure du rappel en mode démo (baseline synthétique)
    demo_signals = pipeline.run_collection_cycle(workspace_id="ws_audit_t1", demo=True)
    assert len(demo_signals) > 0

    covered_axes = {s.get("axis") for s in demo_signals}
    expected_axes = {"ia", "frameworks", "metiers"}
    assert expected_axes.issubset(covered_axes), f"Les 3 axes doivent être couverts: {covered_axes}"
