import time
import asyncio
import threading
import random
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class RateLimiter:
    """
    Thread-safe and asyncio-compatible token-bucket rate limiter.
    Ensures client-side calls do not exceed provider RPM quotas (e.g. 40 RPM for NVIDIA).
    Supports dynamic Retry-After backoff with jitter.
    """

    def __init__(self, requests_per_minute: int = 40, name: str = "default_limiter"):
        self.name = name
        self.rpm = max(1, requests_per_minute)
        self.rate = self.rpm / 60.0  # tokens added per second
        self.capacity = float(self.rpm)
        self.tokens = self.capacity
        self.last_refill = time.time()
        self._lock = threading.Lock()
        self._retry_after_until: Optional[float] = None

    def record_retry_after(self, seconds: float) -> None:
        """Enforces a mandatory cooldown period following an HTTP 429 response."""
        with self._lock:
            base_cooldown = max(0.1, seconds)
            jitter = random.uniform(0.01, 0.05)
            cooldown = base_cooldown + jitter
            self._retry_after_until = time.time() + cooldown
            logger.warning(f"[{self.name}] Rate limit 429 encountered. Cooldown active for {cooldown:.2f}s.")

    def _refill(self, now: float) -> None:
        elapsed = now - self.last_refill
        if elapsed > 0:
            self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)
            self.last_refill = now

    def acquire(self, timeout: float = 30.0) -> bool:
        """
        Synchronously acquires a token, sleeping if necessary up to timeout seconds.
        Returns True if token acquired, False if timeout exceeded.
        """
        start = time.time()
        while True:
            now = time.time()
            if now - start > timeout:
                logger.error(f"[{self.name}] Rate limit acquire timeout ({timeout}s exceeded)")
                return False

            with self._lock:
                # Handle Retry-After pause
                if self._retry_after_until and now < self._retry_after_until:
                    sleep_needed = self._retry_after_until - now
                else:
                    self._retry_after_until = None
                    self._refill(now)
                    if self.tokens >= 1.0:
                        self.tokens -= 1.0
                        return True
                    # Time needed until at least 1 token is available
                    tokens_needed = 1.0 - self.tokens
                    sleep_needed = max(0.05, tokens_needed / self.rate)

            # Sleep outside lock
            sleep_time = min(sleep_needed + random.uniform(0.01, 0.05), timeout - (now - start))
            if sleep_time > 0:
                time.sleep(sleep_time)

    async def acquire_async(self, timeout: float = 30.0) -> bool:
        """
        Asynchronously acquires a token, awaiting if necessary up to timeout seconds.
        """
        start = time.time()
        while True:
            now = time.time()
            if now - start > timeout:
                logger.error(f"[{self.name}] Async rate limit acquire timeout ({timeout}s exceeded)")
                return False

            with self._lock:
                if self._retry_after_until and now < self._retry_after_until:
                    sleep_needed = self._retry_after_until - now
                else:
                    self._retry_after_until = None
                    self._refill(now)
                    if self.tokens >= 1.0:
                        self.tokens -= 1.0
                        return True
                    tokens_needed = 1.0 - self.tokens
                    sleep_needed = max(0.05, tokens_needed / self.rate)

            sleep_time = min(sleep_needed + random.uniform(0.01, 0.05), timeout - (now - start))
            if sleep_time > 0:
                await asyncio.sleep(sleep_time)


# Global singleton registry for rate limiters
_RATE_LIMITERS: dict[str, RateLimiter] = {}
_REGISTRY_LOCK = threading.Lock()


def get_rate_limiter(name: str, requests_per_minute: int = 40) -> RateLimiter:
    with _REGISTRY_LOCK:
        if name not in _RATE_LIMITERS:
            _RATE_LIMITERS[name] = RateLimiter(requests_per_minute=requests_per_minute, name=name)
        return _RATE_LIMITERS[name]
