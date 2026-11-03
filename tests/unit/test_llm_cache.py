import time
from packages.cache.base import BaseLLMCache
from unittest.mock import patch
from packages.cache.sqlite_cache import SQLiteLLMCache
from packages.cache.redis_cache import RedisLLMCache
from packages.cache.factory import (
    compute_cache_key,
    build_llm_cache_key,
    is_cacheable_llm_output,
    get_llm_cache,
)
from services.orchestration.llm import GeneratedIdeasBatch, GeneratedIdea
from services.orchestration.resolver import ResolvedLLMContext
from services.orchestration.nodes.research import ideation_and_scoring_node


def test_sqlite_llm_cache_lifecycle():
    """Tests basic CRUD, TTL expiration, and invalidation in SQLiteLLMCache."""
    cache = SQLiteLLMCache(db_path=":memory:", default_ttl_seconds=1)
    assert isinstance(cache, BaseLLMCache)

    # 1. Set and Get
    key = "test_key_1"
    data = {"ideas": ["Idea A", "Idea B"], "score": 9.5}
    cache.set(key, data, ttl_seconds=2)

    retrieved = cache.get(key)
    assert retrieved is not None
    assert retrieved["ideas"] == ["Idea A", "Idea B"]
    assert retrieved["score"] == 9.5

    # 2. Invalidate
    assert cache.invalidate(key) is True
    assert cache.get(key) is None
    assert cache.invalidate(key) is False

    # 3. Expiration / TTL
    cache.set("short_lived", {"foo": "bar"}, ttl_seconds=1)
    assert cache.get("short_lived") is not None
    time.sleep(1.1)
    assert cache.get("short_lived") is None

    # 4. Clear
    cache.set("k1", {"val": 1})
    cache.set("k2", {"val": 2})
    cache.clear()
    assert cache.get("k1") is None
    assert cache.get("k2") is None


def test_redis_llm_cache_fallback():
    """Tests Redis cache fallback behavior without crashing when Redis is not running."""
    redis_cache = RedisLLMCache(redis_url="redis://localhost:6379/15", default_ttl_seconds=5)
    key = "redis_test_key"
    data = {"platform": "linkedin", "status": "draft"}

    redis_cache.set(key, data, ttl_seconds=5)
    assert redis_cache.get(key) == data

    assert redis_cache.invalidate(key) is True
    assert redis_cache.get(key) is None


def test_compute_cache_key_deterministic():
    """Tests that cache keys are deterministic irrespective of dict key ordering."""
    payload1 = {"topic": "ai", "pillars": ["b", "a"], "target": 5}
    payload2 = {"target": 5, "pillars": ["b", "a"], "topic": "ai"}

    key1 = compute_cache_key("test", payload1)
    key2 = compute_cache_key("test", payload2)
    assert key1 == key2
    assert key1.startswith("test:")


def test_cache_never_stores_demo_or_degraded_or_no_data():
    cache = SQLiteLLMCache(db_path=":memory:", default_ttl_seconds=60)
    non_cacheable_samples = [
        {"status": "DEMO", "generated_ideas": [{"title": "Demo", "is_demo": True}]},
        {"status": "DEGRADED", "variants": [{"platform": "linkedin", "degraded": True}]},
        {"status": "NO_DATA", "generated_ideas": []},
        {"status": "SUCCESS", "is_demo": True, "generated_ideas": [{"title": "Fake"}]},
        {"status": "SUCCESS", "llm_provider_used": "fallback_local", "variants": []},
    ]
    for idx, sample in enumerate(non_cacheable_samples):
        assert is_cacheable_llm_output(sample) is False
        key = f"non_cacheable_{idx}"
        cache.set(key, sample)
        assert cache.get(key) is None


def test_build_llm_cache_key_isolation_and_secret_stripping():
    k_ws1 = build_llm_cache_key(
        node="idea_research",
        workspace_id="ws_alpha",
        provider_id="nvidia",
        model_id="z-ai/glm5",
        params={"topic": "ai", "api_key": "nvapi-secret-1"},
    )
    k_ws1_diff_secret = build_llm_cache_key(
        node="idea_research",
        workspace_id="ws_alpha",
        provider_id="nvidia",
        model_id="z-ai/glm5",
        params={"topic": "ai", "api_key": "nvapi-secret-2"},
    )
    k_ws2 = build_llm_cache_key(
        node="idea_research",
        workspace_id="ws_beta",
        provider_id="nvidia",
        model_id="z-ai/glm5",
        params={"topic": "ai"},
    )
    k_diff_model = build_llm_cache_key(
        node="idea_research",
        workspace_id="ws_alpha",
        provider_id="gemini",
        model_id="gemini-2.5-flash",
        params={"topic": "ai"},
    )
    assert k_ws1 == k_ws1_diff_secret
    assert k_ws1 != k_ws2
    assert k_ws1 != k_diff_model


def test_idea_research_node_caching_integration():
    """Verifies that valid LLM outputs hit the cache while DEMO/error/NO_DATA are never cached."""
    cache = get_llm_cache()
    cache.clear()

    state = {
        "workspace_id": "test_ws_cache",
        "topic_or_brief": "Agentic Caching Benchmark",
        "pillars": ["Performance", "Architecture"],
        "target_count": 2,
        "audience": ["Engineers"],
        "raw_sources": [
            {
                "url": "https://digital-strategy.ec.europa.eu/en/policies/regulatory-framework-ai",
                "title": "EU AI Act",
                "content": "Obligations de gouvernance et de transparence pour les modèles GPAI en Europe.",
            }
        ],
    }

    # 1. DEMO mode is NEVER cached
    demo_state = dict(state, demo=True)
    res_demo = ideation_and_scoring_node(demo_state)  # type: ignore
    assert res_demo["status"] == "DEMO"
    assert res_demo.get("cached") is False

    # 2. LLM error fallback is NEVER cached
    fake_ctx = ResolvedLLMContext(
        model=object(),
        provider_id="nvidia",
        model_id="z-ai/glm5",
        temperature=0.3,
        resolution_source="environment",
        run_id="run_test_cache_1",
    )
    with patch("services.orchestration.nodes.research.resolve_and_get_llm", return_value=(object(), fake_ctx)), \
         patch("services.orchestration.nodes.research.invoke_structured_output", side_effect=RuntimeError("API timeout")):
        res_err = ideation_and_scoring_node(state)  # type: ignore
        assert res_err["status"] == "DEMO"
        assert res_err.get("cached") is False

    # 3. Valid LLM output IS cached and second invocation hits cache
    valid_batch = GeneratedIdeasBatch(
        ideas=[
            GeneratedIdea(
                title="Gouvernance GPAI en entreprise européenne",
                angle="Mettre en place la traçabilité documentaire exigée par l'AI Act.",
                target_audience="Engineers",
                recommended_formats=["linkedin", "x"],
                evidence=[{"source_id": "https://digital-strategy.ec.europa.eu/en/policies/regulatory-framework-ai", "claim": "Obligations GPAI"}],
                novelty_score=88.0,
                relevance_score=94.0,
                effort_score=45.0,
                priority="high",
                risks=[],
            )
        ]
    )
    with patch("services.orchestration.nodes.research.resolve_and_get_llm", return_value=(object(), fake_ctx)), \
         patch("services.orchestration.nodes.research.invoke_structured_output", return_value=valid_batch) as mock_invoke:
        res1 = ideation_and_scoring_node(state)  # type: ignore
        assert res1["status"] == "SUCCESS"
        assert "generated_ideas" in res1
        assert res1.get("cached") is not True
        assert mock_invoke.call_count == 1

        # Second invocation with same inputs -> cache hit
        res2 = ideation_and_scoring_node(state)  # type: ignore
        assert "generated_ideas" in res2
        assert res2.get("cached") is True
        assert len(res2["generated_ideas"]) == len(res1["generated_ideas"])
        assert mock_invoke.call_count == 1

