import hashlib
import json
import os
from typing import Any, Dict, List, Optional
from packages.cache.base import BaseLLMCache
from packages.cache.sqlite_cache import SQLiteLLMCache
from packages.cache.redis_cache import RedisLLMCache

_CACHE_INSTANCE: Optional[BaseLLMCache] = None

CACHE_KEY_VERSION = "v2"

_NON_CACHEABLE_STATUSES = {
    "DEMO",
    "DEGRADED",
    "FAILED",
    "ERROR",
    "FALLBACK",
    "NO_DATA",
    "PENDING_LLM",
    "LEXICAL_FALLBACK",
    "DETERMINISTIC_ONLY",
}


def is_cacheable_llm_output(value: Any) -> bool:
    """
    Ensure fallback, DEMO, degraded, synthetic, or error responses are never cached.
    Only validated structured outputs produced by an active LLM provider may be cached.
    """
    if not isinstance(value, dict) or not value:
        return False

    status = str(value.get("status", "")).strip().upper()
    if status in _NON_CACHEABLE_STATUSES:
        return False

    if (
        value.get("is_demo") is True
        or value.get("is_degraded") is True
        or value.get("degraded") is True
        or value.get("fallback") is True
        or value.get("error")
    ):
        return False

    provider = str(value.get("llm_provider_used", "")).strip().lower()
    if provider in {"fallback_local", "demo", "offline", "degraded", "none"}:
        return False

    for list_key in ("ideas", "variants", "insights"):
        items = value.get(list_key)
        if isinstance(items, list):
            if status and not items:
                return False
            for item in items:
                if isinstance(item, dict):
                    if (
                        item.get("is_demo") is True
                        or item.get("degraded") is True
                        or item.get("is_degraded") is True
                    ):
                        return False
                    score_bd = item.get("score_breakdown")
                    if isinstance(score_bd, dict) and score_bd.get("synthetic") is True:
                        return False

    return True


def _strip_secrets(payload: Dict[str, Any]) -> Dict[str, Any]:
    cleaned: Dict[str, Any] = {}
    for k, v in sorted(payload.items()):
        k_lower = str(k).lower()
        if any(sec in k_lower for sec in ("api_key", "secret", "token", "password", "credential")):
            continue
        if isinstance(v, dict):
            cleaned[k] = _strip_secrets(v)
        else:
            cleaned[k] = v
    return cleaned


def compute_cache_key(prefix: str, payload: Dict[str, Any]) -> str:
    """Computes a deterministic SHA-256 cache key from sorted payload attributes, excluding secrets."""
    safe_payload = _strip_secrets(payload) if isinstance(payload, dict) else payload
    serialized = json.dumps(safe_payload, sort_keys=True, ensure_ascii=True, default=str)
    digest = hashlib.sha256(serialized.encode("utf-8")).hexdigest()[:24]
    return f"{prefix}:{digest}"


def build_llm_cache_key(
    *,
    node: str,
    workspace_id: str,
    provider_id: str,
    model_id: str,
    prompt_version: str = "v1",
    schema_version: str = "v1",
    params: Optional[Dict[str, Any]] = None,
    sources_fingerprint: Optional[List[Any]] = None,
) -> str:
    """
    Builds a deterministic, tenant-isolated SHA-256 cache key for LLM node outputs.
    Strictly excludes any API keys or secrets.
    """
    safe_params = _strip_secrets(params) if isinstance(params, dict) else {}
    payload = {
        "cache_version": CACHE_KEY_VERSION,
        "node": str(node or "default"),
        "workspace_id": str(workspace_id or "default"),
        "provider_id": str(provider_id or "unknown"),
        "model_id": str(model_id or "unknown"),
        "prompt_version": str(prompt_version or "v1"),
        "schema_version": str(schema_version or "v1"),
        "params": safe_params,
        "sources_fingerprint": sources_fingerprint or [],
    }
    serialized = json.dumps(payload, sort_keys=True, ensure_ascii=True, default=str)
    digest = hashlib.sha256(serialized.encode("utf-8")).hexdigest()[:24]
    return f"{CACHE_KEY_VERSION}:{workspace_id or 'default'}:{node}:{digest}"


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
