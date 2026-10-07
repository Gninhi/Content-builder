import os
from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address
from packages.security.auth import decode_access_token


def get_rate_limit_key(request: Request) -> str:
    """
    Computes rate limit key prioritizing tenant workspace_id from verified JWT claims,
    falling back to remote client IP for unauthenticated calls.
    """
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ", 1)[1]
        try:
            claims = decode_access_token(token)
            ws = claims.get("workspace_id")
            if ws:
                return f"ws:{ws}"
        except Exception:
            pass
    return get_remote_address(request)


limiter = Limiter(
    key_func=get_rate_limit_key,
    default_limits=[os.getenv("RATE_LIMIT_DEFAULT", "200/minute")]
)
