import os
import time
import threading
from collections import OrderedDict
from typing import Optional, Tuple, Any


class AuthSessionCache:
    """
    Thread-safe in-memory TTL cache with bounded LRU eviction for session validation
    and RBAC role checks (ANOM-22 / CODE-08).
    Eliminates redundant sequential database hits (3 to 4 per request) during authenticated API traffic
    while preventing out-of-memory (OOM) risks with bounded OrderedDict LRU eviction.
    """
    _lock = threading.Lock()
    MAX_ENTRIES: int = int(os.getenv("AUTH_CACHE_MAX_ENTRIES", "10000"))
    DEFAULT_TTL: float = float(os.getenv("AUTH_CACHE_TTL_SECONDS", "60.0"))

    _user_status_cache: OrderedDict[str, Tuple[bool, Optional[float], float]] = OrderedDict()  # user_id -> (is_active, tokens_valid_after, expires_at)
    _session_revoked_cache: OrderedDict[str, Tuple[bool, float]] = OrderedDict()  # jti -> (is_revoked, expires_at)
    _member_role_cache: OrderedDict[Tuple[str, str], Tuple[Optional[str], float]] = OrderedDict()  # (ws_id, user_id) -> (role_or_none, expires_at)

    @classmethod
    def _set_bounded(cls, cache: OrderedDict, key: Any, value: Any) -> None:
        if key in cache:
            cache.move_to_end(key)
        elif len(cache) >= cls.MAX_ENTRIES:
            cache.popitem(last=False)
        cache[key] = value

    @classmethod
    def get_user_status(cls, user_id: str) -> Optional[Tuple[bool, Optional[float]]]:
        now = time.monotonic()
        with cls._lock:
            entry = cls._user_status_cache.get(user_id)
            if entry and entry[2] > now:
                cls._user_status_cache.move_to_end(user_id)
                return entry[0], entry[1]
            if entry:
                cls._user_status_cache.pop(user_id, None)
            return None

    @classmethod
    def set_user_status(cls, user_id: str, is_active: bool, tokens_valid_after: Optional[float] = None, ttl: Optional[float] = None) -> None:
        expires_at = time.monotonic() + (ttl if ttl is not None else cls.DEFAULT_TTL)
        with cls._lock:
            cls._set_bounded(cls._user_status_cache, user_id, (is_active, tokens_valid_after, expires_at))

    @classmethod
    def is_session_revoked(cls, jti: str) -> Optional[bool]:
        now = time.monotonic()
        with cls._lock:
            entry = cls._session_revoked_cache.get(jti)
            if entry and entry[1] > now:
                cls._session_revoked_cache.move_to_end(jti)
                return entry[0]
            if entry:
                cls._session_revoked_cache.pop(jti, None)
            return None

    @classmethod
    def set_session_revoked(cls, jti: str, is_revoked: bool, ttl: Optional[float] = None) -> None:
        expires_at = time.monotonic() + (ttl if ttl is not None else cls.DEFAULT_TTL)
        with cls._lock:
            cls._set_bounded(cls._session_revoked_cache, jti, (is_revoked, expires_at))

    @classmethod
    def get_member_role(cls, workspace_id: str, user_id: str) -> Optional[str]:
        now = time.monotonic()
        key = (workspace_id, user_id)
        with cls._lock:
            entry = cls._member_role_cache.get(key)
            if entry and entry[1] > now:
                cls._member_role_cache.move_to_end(key)
                return entry[0]
            if entry:
                cls._member_role_cache.pop(key, None)
            return None

    @classmethod
    def set_member_role(cls, workspace_id: str, user_id: str, role: Optional[str], ttl: Optional[float] = None) -> None:
        expires_at = time.monotonic() + (ttl if ttl is not None else cls.DEFAULT_TTL)
        key = (workspace_id, user_id)
        with cls._lock:
            cls._set_bounded(cls._member_role_cache, key, (role, expires_at))

    @classmethod
    def invalidate_user(cls, user_id: str) -> None:
        with cls._lock:
            cls._user_status_cache.pop(user_id, None)
            keys_to_del = [k for k in cls._member_role_cache if k[1] == user_id]
            for k in keys_to_del:
                cls._member_role_cache.pop(k, None)

    @classmethod
    def invalidate_session(cls, jti: str) -> None:
        with cls._lock:
            cls._set_bounded(cls._session_revoked_cache, jti, (True, time.monotonic() + cls.DEFAULT_TTL))

    @classmethod
    def invalidate_member_role(cls, workspace_id: str, user_id: str) -> None:
        with cls._lock:
            cls._member_role_cache.pop((workspace_id, user_id), None)

    @classmethod
    def clear_all(cls) -> None:
        with cls._lock:
            cls._user_status_cache.clear()
            cls._session_revoked_cache.clear()
            cls._member_role_cache.clear()
