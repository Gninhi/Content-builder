import hashlib
import json
import os
from typing import Any, Dict, Optional
from packages.cache.base import BaseLLMCache
from packages.cache.sqlite_cache import SQLiteLLMCache
from packages.cache.redis_cache import RedisLLMCache

_CACHE_INSTANCE: Optional[BaseLLMCache] = None


def compute_cache_key(prefix: str, payload: Dict[str, Any]) -> str:
    """Computes a deterministic SHA-256 cache key from sorted payload attributes."""
    serialized = json.dumps(payload, sort_keys=True, ensure_ascii=True)
    digest = hashlib.sha256(serialized.encode("utf-8")).hexdigest()[:24]
    return f"{prefix}:{digest}"


def get_llm_cache(force_new: bool = False) -> BaseLLMCache:
    """
    Returns the configured LLM cache instance based on environment variables.
    Supported backends: 'sqlite' (default), 'redis', 'memory'.
    """
    global _CACHE_INSTANCE
    if _CACHE_INSTANCE is not None and not force_new:
        return _CACHE_INSTANCE

    backend = os.getenv("LLM_CACHE_BACKEND", "sqlite").lower()
    default_ttl = int(os.getenv("LLM_CACHE_TTL_SECONDS", "86400"))  # 24h default

    if backend == "redis":
        redis_url = os.getenv("REDIS_URL")
        _CACHE_INSTANCE = RedisLLMCache(redis_url=redis_url, default_ttl_seconds=default_ttl)
    elif backend == "memory":
        _CACHE_INSTANCE = SQLiteLLMCache(db_path=":memory:", default_ttl_seconds=default_ttl)
    else:  # sqlite default
        sqlite_path = os.getenv("LLM_CACHE_SQLITE_PATH", "artifacts/cache/llm_cache.sqlite")
        _CACHE_INSTANCE = SQLiteLLMCache(db_path=sqlite_path, default_ttl_seconds=default_ttl)

    return _CACHE_INSTANCE
