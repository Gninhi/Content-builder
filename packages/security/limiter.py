import logging
import os
from typing import Any, Dict
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from packages.security.auth import decode_access_token

logger = logging.getLogger("security.limiter")

# Global diagnostics for storage status
_storage_diagnostic: Dict[str, Any] = {
    "configured_uri": None,
    "effective_uri": "memory://",
    "status": "uninitialized",
    "degraded": False,
    "environment": os.getenv("ENVIRONMENT", os.getenv("APP_ENV", "development")).lower(),
}


def get_client_ip(request: Request) -> str:
    """
    Safely resolves client IP respecting configured trusted reverse proxies,
    preventing IP spoofing attacks via arbitrary X-Forwarded-For injection.
    """
    trusted_env = os.getenv("TRUSTED_PROXIES", "127.0.0.1,::1").split(",")
    trusted_proxies = {p.strip() for p in trusted_env if p.strip()}
    trust_all = os.getenv("TRUST_ALL_PROXIES", "false").lower() in ("true", "1", "yes")

    direct_ip = request.client.host if request.client else "127.0.0.1"

    if trust_all or direct_ip in trusted_proxies:
        forwarded_for = request.headers.get("x-forwarded-for") or request.headers.get("X-Forwarded-For")
        if forwarded_for:
            ips = [ip.strip() for ip in forwarded_for.split(",")]
            if ips:
                return ips[0]
        real_ip = request.headers.get("x-real-ip") or request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip.strip()

    return direct_ip


def get_rate_limit_key(request: Request) -> str:
    """
    Computes rate limit key prioritizing tenant workspace_id from verified JWT claims,
    falling back to verified remote client IP for unauthenticated calls.
    """
    auth_header = request.headers.get("authorization") or request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ", 1)[1]
        try:
            claims = decode_access_token(token)
            ws = claims.get("workspace_id")
            if ws:
                return f"ws:{ws}"
        except Exception:
            pass
    return get_client_ip(request)


def check_redis_connectivity(url: str, timeout: float = 0.5) -> bool:
    """Checks whether the specified Redis URL is reachable within a strict timeout."""
    try:
        import redis
        client = redis.from_url(url, socket_timeout=timeout, socket_connect_timeout=timeout)
        client.ping()
        client.close()
        return True
    except Exception as exc:
        logger.debug(f"[RateLimiter] Redis ping failed on {url}: {exc}")
        return False


def get_storage_status() -> Dict[str, Any]:
    """Returns current rate limiter storage health diagnostics."""
    return dict(_storage_diagnostic)


def _init_limiter() -> Limiter:
    """
    Initializes SlowAPI Limiter with robust storage resolution and clear diagnostic logging.
    Guarantees that uncontactable Redis instances do not silently break or cause crash cascades.
    """
    env = os.getenv("ENVIRONMENT", os.getenv("APP_ENV", "development")).lower()
    candidate = os.getenv("RATE_LIMIT_STORAGE_URI") or os.getenv("REDIS_URL")
    allow_memory_fallback = os.getenv("RATE_LIMIT_ALLOW_MEMORY_FALLBACK", "true").lower() in ("true", "1", "yes")
    default_limits: list[Any] = [os.getenv("RATE_LIMIT_DEFAULT", "200/minute")]

    _storage_diagnostic["configured_uri"] = candidate
    _storage_diagnostic["environment"] = env

    effective_uri = "memory://"

    if candidate and candidate.startswith(("redis://", "rediss://")):
        is_up = check_redis_connectivity(candidate, timeout=0.8)
        if is_up:
            effective_uri = candidate
            _storage_diagnostic["status"] = "connected"
            _storage_diagnostic["degraded"] = False
            logger.info(f"[RateLimiter] Connected to Redis rate limit storage: {candidate}")
        else:
            if env in ("production", "prod") and not allow_memory_fallback:
                _storage_diagnostic["status"] = "redis_unreachable_fail_closed"
                _storage_diagnostic["degraded"] = True
                logger.critical(
                    f"[RateLimiter] CRITICAL: Redis storage '{candidate}' is unreachable in {env} "
                    "and memory fallback is disabled. Rate limiting will reject or report degraded status."
                )
                effective_uri = candidate
            else:
                _storage_diagnostic["status"] = "degraded_memory"
                _storage_diagnostic["degraded"] = True
                logger.warning(
                    f"[RateLimiter] Redis storage '{candidate}' is unreachable in {env} environment. "
                    "Gracefully activating controlled in-memory rate limiting fallback."
                )
                effective_uri = "memory://"
    else:
        _storage_diagnostic["status"] = "memory_default"
        _storage_diagnostic["degraded"] = False
        effective_uri = "memory://"

    _storage_diagnostic["effective_uri"] = effective_uri

    try:
        return Limiter(
            key_func=get_rate_limit_key,
            default_limits=default_limits,
            storage_uri=effective_uri,
        )
    except Exception as exc:
        logger.error(f"[RateLimiter] Error initializing Limiter with '{effective_uri}': {exc}. Falling back to memory://")
        _storage_diagnostic["status"] = "degraded_memory_fallback"
        _storage_diagnostic["degraded"] = True
        _storage_diagnostic["effective_uri"] = "memory://"
        return Limiter(
            key_func=get_rate_limit_key,
            default_limits=default_limits,
            storage_uri="memory://",
        )


limiter = _init_limiter()


def safe_rate_limit_exceeded_handler(request: Request, exc: Exception) -> Response:
    """
    Resilient exception handler for SlowAPI.
    Properly handles both authentic RateLimitExceeded events and any storage ConnectionErrors
    forwarded by SlowAPI's middleware without crashing into AttributeError.
    """
    if isinstance(exc, RateLimitExceeded):
        detail = getattr(exc, "detail", "Quota exceeded")
        return JSONResponse(
            {"error": f"Rate limit exceeded: {detail}"},
            status_code=429,
        )

    # If an unexpected network or storage exception was intercepted by SlowAPI
    logger.error(
        f"[RateLimiter] Storage failure during rate limit check on '{request.url.path}': {exc}",
        exc_info=True,
    )
    _storage_diagnostic["degraded"] = True
    _storage_diagnostic["status"] = "runtime_storage_error"

    # Distinguish sensitive security endpoints (e.g. auth login) from regular traffic
    sensitive_prefixes = ("/v1/auth/login", "/v1/auth/token")
    if request.url.path.startswith(sensitive_prefixes) and _storage_diagnostic["environment"] in ("production", "prod"):
        return JSONResponse(
            {"error": "Authentication temporarily unavailable: rate limiting backend connection lost"},
            status_code=503,
        )

    # For general routes, return 503 with clear error payload rather than crashing with 500
    return JSONResponse(
        {"error": "Rate limit service temporarily unavailable"},
        status_code=503,
    )
