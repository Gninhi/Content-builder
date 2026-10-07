import json
import logging
import time
from typing import Any, Dict, Optional
from packages.cache.base import BaseLLMCache

logger = logging.getLogger(__name__)


class RedisLLMCache(BaseLLMCache):
    """
    Redis-backed cache for LLM deterministic calls.
    Falls back gracefully to an in-memory dictionary if Redis is unavailable or unconfigured.
    """

    def __init__(self, redis_url: Optional[str] = None, default_ttl_seconds: int = 86400):
        self.default_ttl = default_ttl_seconds
        self.client = None
        self._memory_fallback: Dict[str, Dict[str, Any]] = {}

        if redis_url:
            try:
                import redis  # type: ignore
                self.client = redis.from_url(redis_url, decode_responses=True)
                self.client.ping()
            except Exception as e:
                logger.warning(f"Failed to connect to Redis at {redis_url}, using in-memory fallback: {e}")
                self.client = None

    def get(self, key: str) -> Optional[Dict[str, Any]]:
        if self.client:
            try:
                val = self.client.get(f"llm_cache:{key}")
                if val:
                    return json.loads(val)
                return None
            except Exception as e:
                logger.warning(f"Redis get failed: {e}")

        # Fallback in-memory
        item = self._memory_fallback.get(key)
        if item:
            if item["expires_at"] < time.time():
                del self._memory_fallback[key]
                return None
            return item["value"]
        return None

    def set(self, key: str, value: Dict[str, Any], ttl_seconds: Optional[int] = None) -> None:
        ttl = ttl_seconds if ttl_seconds is not None else self.default_ttl
        val_str = json.dumps(value, ensure_ascii=False)

        if self.client:
            try:
                self.client.setex(f"llm_cache:{key}", ttl, val_str)
                return
            except Exception as e:
                logger.warning(f"Redis setex failed: {e}")

        # Fallback in-memory
        self._memory_fallback[key] = {
            "value": value,
            "expires_at": time.time() + ttl
        }

    def invalidate(self, key: str) -> bool:
        if self.client:
            try:
                res = self.client.delete(f"llm_cache:{key}")
                return bool(res > 0)
            except Exception as e:
                logger.warning(f"Redis delete failed: {e}")

        return bool(self._memory_fallback.pop(key, None) is not None)

    def clear(self) -> None:
        if self.client:
            try:
                keys = self.client.keys("llm_cache:*")
                if keys:
                    self.client.delete(*keys)
            except Exception as e:
                logger.warning(f"Redis clear failed: {e}")

        self._memory_fallback.clear()
