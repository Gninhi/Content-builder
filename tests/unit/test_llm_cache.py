import time
from packages.cache.base import BaseLLMCache
from packages.cache.sqlite_cache import SQLiteLLMCache
from packages.cache.redis_cache import RedisLLMCache
from packages.cache.factory import compute_cache_key, get_llm_cache
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


def test_idea_research_node_caching_integration():
    """Verifies that subsequent calls to ideation_and_scoring_node hit the cache."""
    cache = get_llm_cache()
    cache.clear()

    state = {
        "workspace_id": "test_ws_cache",
        "topic_or_brief": "Agentic Caching Benchmark",
        "pillars": ["Performance", "Architecture"],
        "target_count": 10,
        "audience": ["Engineers"]
    }

    # First invocation -> cache miss & store
    res1 = ideation_and_scoring_node(state)  # type: ignore
    assert "generated_ideas" in res1
    assert res1.get("cached") is not True

    # Second invocation with same inputs -> cache hit
    res2 = ideation_and_scoring_node(state)  # type: ignore
    assert "generated_ideas" in res2
    assert res2.get("cached") is True
    assert len(res2["generated_ideas"]) == len(res1["generated_ideas"])
