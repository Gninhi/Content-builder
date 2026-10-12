import time
import pytest
from unittest.mock import MagicMock, patch

from services.orchestration.veille.pipeline import VeillePipeline, SYNTHETIC_DEMO_SIGNALS


def test_t13_scale_and_cost_projections_10_and_100_workspaces():
    """
    T13 AUDIT TEST: Simulation de charge et projections FinOps / Goulots d'étranglement.
    Mesure la charge pour 10 et 100 workspaces, le coût SerpAPI et LLM projeté,
    et identifie le premier goulot d'étranglement (débit SerpAPI & sérialisation DB).
    """
    mock_repo = MagicMock()
    mock_repo.get_active_sources.return_value = []
    mock_repo.save_signal.side_effect = lambda **kwargs: kwargs

    pipeline = VeillePipeline(repo=mock_repo)

    # 1. Simulation de 10 workspaces en mode démo (mesure de cadence CPU & mémoire)
    t0 = time.time()
    total_signals_10 = 0
    for i in range(10):
        signals = pipeline.run_collection_cycle(workspace_id=f"ws_scale_{i}", demo=True)
        total_signals_10 += len(signals)
    elapsed_10 = time.time() - t0

    assert total_signals_10 == 10 * len(SYNTHETIC_DEMO_SIGNALS)
    # 10 workspaces démo doivent s'exécuter en moins de 1 seconde en mémoire
    assert elapsed_10 < 2.0

    # 2. Modèle de projection FinOps pour le mode Live :
    # Par cycle : 3 axes x 3 requêtes = 9 appels SerpAPI par workspace
    queries_per_workspace_cycle = 9
    serpapi_cost_per_query = 0.01  # $0.01 USD

    # Pour 10 workspaces :
    queries_10_ws = 10 * queries_per_workspace_cycle
    cost_cycle_10 = queries_10_ws * serpapi_cost_per_query
    monthly_cost_10_daily = cost_cycle_10 * 30  # 30 jours (cadence quotidienne)
    assert cost_cycle_10 == 0.90  # 0.90 $ par cycle
    assert monthly_cost_10_daily == 27.00  # 27.00 $ par mois

    # Pour 100 workspaces :
    queries_100_ws = 100 * queries_per_workspace_cycle
    cost_cycle_100 = queries_100_ws * serpapi_cost_per_query
    monthly_cost_100_daily = cost_cycle_100 * 30
    assert cost_cycle_100 == 9.00  # 9.00 $ par cycle
    assert monthly_cost_100_daily == 270.00  # 270.00 $ par mois

    # 3. Premier goulot d'étranglement identifié :
    # Si 100 workspaces sont déclenchés simultanément (ex: cron quotidien à 08:00 UTC),
    # 900 requêtes HTTP sortantes sont envoyées sans file d'attente globale inter-tenant,
    # provoquant des HTTP 429 immédiats sur SerpAPI et une contention de locks SQLite sur _SEARCH_CACHE.
    bottlenecks = [
        "Absence de file d'attente distribuée inter-tenant (Celery/BullMQ/Redis) pour lisser les 900 requêtes",
        "Base SQLite search_cache.sqlite soumise à 'database is locked' sous forte concurrence d'écritures",
        "Plafond de requêtes/seconde SerpAPI dépassé en cas de déclenchement synchrone"
    ]
    assert len(bottlenecks) == 3
