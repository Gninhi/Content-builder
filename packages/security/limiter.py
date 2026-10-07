import os
from fastapi import Request
from slowapi import Limiter
from packages.security.auth import decode_access_token


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


def _resolve_storage_uri() -> str:
    candidate = os.getenv("RATE_LIMIT_STORAGE_URI") or os.getenv("REDIS_URL")
    if candidate and candidate.startswith("redis"):
        try:
            import redis  # type: ignore # noqa: F401
            return candidate
        except (ImportError, Exception):
            return "memory://"
    return candidate or "memory://"


_storage_uri = _resolve_storage_uri()

try:
    limiter = Limiter(
        key_func=get_rate_limit_key,
        default_limits=[os.getenv("RATE_LIMIT_DEFAULT", "200/minute")],
        storage_uri=_storage_uri,
    )
except Exception:
    # Graceful fallback to memory limiter if Redis storage initialization fails
    limiter = Limiter(
        key_func=get_rate_limit_key,
        default_limits=[os.getenv("RATE_LIMIT_DEFAULT", "200/minute")],
        storage_uri="memory://",
    )
