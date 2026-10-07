from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class BaseLLMCache(ABC):
    """Abstract Base Class for LLM deterministic response caching."""

    @abstractmethod
    def get(self, key: str) -> Optional[Dict[str, Any]]:
        """Retrieves cached item if present and not expired."""
        pass

    @abstractmethod
    def set(self, key: str, value: Dict[str, Any], ttl_seconds: Optional[int] = None) -> None:
        """Stores an item with an optional TTL in seconds."""
        pass

    @abstractmethod
    def invalidate(self, key: str) -> bool:
        """Removes a specific cache entry. Returns True if removed."""
        pass

    @abstractmethod
    def clear(self) -> None:
        """Clears all entries in the cache."""
        pass
