import pytest
from unittest.mock import MagicMock, patch

from packages.tools.web_search import WebSearchTool, _SEARCH_CACHE
from packages.resilience import CircuitBreaker
from services.publisher.worker import PublisherWorker
from packages.domain.state_machine import ContentStatus


def test_t6_search_resilience_and_circuit_breakers():
    """
    T6 AUDIT TEST: Résilience face aux pannes d'outils.
    Vérifie la bascule SerpAPI -> DuckDuckGo -> Réponse NO_DATA propre
    et le comportement du circuit breaker.
    """
    tool = WebSearchTool()

    # 1. SerpAPI échoue -> Bascule automatique vers DuckDuckGo
    from packages.tools.schemas import WebSearchResultItem
    mock_item = WebSearchResultItem(
        title="Article de repli",
        url="https://ddg-fallback.com/article",
        snippet="Contenu trouvé via DuckDuckGo",
        source_name="ddg-fallback.com",
        engine="duckduckgo:ddgs",
        score=0.85
    )
    with patch.object(_SEARCH_CACHE, "get", return_value=None), \
         patch.object(tool, "_query_serpapi", return_value=[]), \
         patch.object(tool, "_query_duckduckgo", return_value=[mock_item]):
        resp = tool.search(query="unique fallback query audit t6", workspace_id="ws_audit_t6")
        assert resp.engine_used == "duckduckgo"
        assert resp.status == "SUCCESS"

    # 2. SerpAPI ET DuckDuckGo échouent -> Retour déterministe NO_DATA (Zéro contenu inventé)
    with patch.object(_SEARCH_CACHE, "get", return_value=None), \
         patch.object(tool, "_query_serpapi", return_value=[]), \
         patch.object(tool, "_query_duckduckgo", return_value=[]):
        resp_empty = tool.search(query="query total failure audit t6", workspace_id="ws_audit_t6")
        assert resp_empty.status == "NO_DATA"
        assert len(resp_empty.results) == 0

    # 3. Déclenchement du Circuit Breaker après pannes successives
    cb = CircuitBreaker(failure_threshold=2, recovery_timeout=60.0, name="test_serpapi_cb")
    assert cb.can_execute() is True
    cb.record_failure(Exception("HTTP 500 Internal Error"))
    assert cb.can_execute() is True
    cb.record_failure(Exception("HTTP 500 Internal Error"))
    # Le circuit s'ouvre
    assert cb.can_execute() is False


def test_t7_worker_concurrency_locking_and_idempotency():
    """
    T7 AUDIT TEST: Idempotence et verrouillage strict contre les courses de workers.
    Vérifie le respect de la règle 'Au plus une fois' et la détection d'exécution concurrente.
    """
    mock_db = MagicMock()
    worker = PublisherWorker(db_session=mock_db)

    # 1. Idempotence : un job déjà PUBLISHED renvoie son reçu sans re-publier
    mock_job_published = MagicMock()
    mock_job_published.id = "job_already_done"
    mock_job_published.status = ContentStatus.PUBLISHED.value
    mock_job_published.published_post.external_post_id = "ext_12345"
    mock_job_published.published_post.permalink = "https://linkedin.com/post/12345"
    mock_db.query.return_value.filter.return_value.first.return_value = mock_job_published

    res = worker.execute_job("job_already_done")
    assert res["status"] == "ALREADY_PUBLISHED"
    assert res["external_post_id"] == "ext_12345"

    # 2. Concurrence : deux workers attaquent le même job en statut PUBLISHING
    mock_job_in_flight = MagicMock()
    mock_job_in_flight.id = "job_in_flight"
    mock_job_in_flight.status = ContentStatus.PUBLISHING.value
    mock_db.query.return_value.filter.return_value.first.return_value = mock_job_in_flight

    with pytest.raises(RuntimeError, match="Concurrent execution detected: Job 'job_in_flight' is already in PUBLISHING status."):
        worker.execute_job("job_in_flight")
