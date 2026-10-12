import os
import time
import random
import logging
import threading
from typing import Callable, Any, Type, Tuple, Optional
from enum import Enum

logger = logging.getLogger(__name__)


class CircuitState(str, Enum):
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"


class CircuitBreakerOpenException(Exception):
    """Raised when a call is blocked because the circuit breaker is OPEN."""
    pass


class BudgetExceededException(Exception):
    """Raised when the cycle exceeds its token or duration budget."""
    pass


class CircuitBreaker:
    """
    Production-grade Circuit Breaker pattern for protecting LLM and external service calls.
    Prevents cascading failures on 429 / 5xx rate limits and outages.
    """

    def __init__(
        self,
        failure_threshold: int = 3,
        recovery_timeout: float = 30.0,
        name: str = "llm_circuit_breaker"
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.name = name
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time: Optional[float] = None

    def can_execute(self) -> bool:
        if self.state == CircuitState.CLOSED:
            return True
        if self.state == CircuitState.OPEN:
            if self.last_failure_time and (time.time() - self.last_failure_time >= self.recovery_timeout):
                logger.info(f"[{self.name}] Recovery timeout elapsed. Transitioning OPEN -> HALF_OPEN")
                self.state = CircuitState.HALF_OPEN
                return True
            return False
        if self.state == CircuitState.HALF_OPEN:
            return True
        return False

    def record_success(self) -> None:
        if self.state in (CircuitState.HALF_OPEN, CircuitState.OPEN):
            logger.info(f"[{self.name}] Call succeeded in {self.state.value}. Resetting to CLOSED.")
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time = None

    def record_failure(self, exc: Exception) -> None:
        self.failure_count += 1
        self.last_failure_time = time.time()
        logger.warning(f"[{self.name}] Failure #{self.failure_count}: {exc}")
        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN
            logger.error(f"[{self.name}] Threshold {self.failure_threshold} reached. Tripping circuit to OPEN.")

    def execute(self, fn: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        if not self.can_execute():
            raise CircuitBreakerOpenException(
                f"[{self.name}] Circuit is OPEN. Calls are blocked until recovery timeout ({self.recovery_timeout}s)."
            )
        try:
            result = fn(*args, **kwargs)
            self.record_success()
            return result
        except Exception as exc:
            self.record_failure(exc)
            raise


def retry_with_backoff(
    fn: Callable[..., Any],
    *args: Any,
    max_retries: int = 3,
    initial_delay: float = 0.1,
    max_delay: float = 2.0,
    backoff_factor: float = 2.0,
    jitter: bool = True,
    retryable_exceptions: Tuple[Type[Exception], ...] = (Exception,),
    **kwargs: Any
) -> Any:
    """
    Executes a function with exponential backoff and jitter on transient errors (429, 5xx).
    """
    last_exc = None
    delay = initial_delay

    for attempt in range(max_retries + 1):
        try:
            return fn(*args, **kwargs)
        except retryable_exceptions as exc:
            last_exc = exc
            if attempt == max_retries:
                logger.error(f"Function {fn.__name__ if hasattr(fn, '__name__') else str(fn)} failed after {max_retries} retries: {exc}")
                raise exc

            sleep_time = min(max_delay, delay * (backoff_factor ** attempt))
            if jitter:
                sleep_time += random.uniform(0.01, 0.05)

            logger.info(f"Retry {attempt + 1}/{max_retries} after {sleep_time:.3f}s due to: {exc}")
            time.sleep(sleep_time)

    if last_exc:
        raise last_exc


class CycleBudget:
    """
    Enforces maximum token budget and execution duration per agentic cycle.
    """

    def __init__(
        self,
        max_tokens: int = 50_000,
        max_duration_seconds: float = 60.0
    ):
        self.max_tokens = max_tokens
        self.max_duration_seconds = max_duration_seconds
        self.start_time = time.time()
        self.used_tokens = 0

    def add_tokens(self, count: int) -> None:
        self.used_tokens += count
        self.check_budget()

    def check_budget(self) -> None:
        elapsed = time.time() - self.start_time
        if elapsed > self.max_duration_seconds:
            raise BudgetExceededException(
                f"Cycle exceeded maximum duration limit ({elapsed:.1f}s > {self.max_duration_seconds}s)"
            )
        if self.used_tokens > self.max_tokens:
            raise BudgetExceededException(
                f"Cycle exceeded maximum token budget ({self.used_tokens} > {self.max_tokens})"
            )

    def track_in_langfuse(self, trace_id: Optional[str] = None) -> bool:
        """
        Records cycle tokens, execution duration, and estimated USD cost as scores in Langfuse.
        """
        if not trace_id:
            return False

        try:
            from packages.observability.tracing import ObservabilityTracer
            from packages.observability.metrics import CostAndTokenEstimator

            elapsed = round(time.time() - self.start_time, 2)
            ObservabilityTracer.record_score("cycle_tokens", float(self.used_tokens), trace_id=trace_id)
            ObservabilityTracer.record_score("cycle_duration_seconds", float(elapsed), trace_id=trace_id)

            rates = CostAndTokenEstimator.get_rates_for_model(os.getenv("GEMINI_MODEL", "gemini-3.8-flash"))
            cost = (self.used_tokens / 1000.0) * rates["input_per_1k"]
            ObservabilityTracer.record_score("cycle_cost_usd", float(round(cost, 6)), trace_id=trace_id)
            return True
        except Exception as e:
            logger.warning(f"Failed to track cycle budget metrics in Langfuse: {e}")
            return False


_CIRCUIT_BREAKERS: dict[str, CircuitBreaker] = {}
_CB_LOCK = threading.Lock()


def get_circuit_breaker(
    provider_id: str,
    model_id: Optional[str] = None,
    failure_threshold: int = 3,
    recovery_timeout: float = 30.0
) -> CircuitBreaker:
    """
    Returns or creates a circuit breaker instance scoped per provider or per (provider, model).
    """
    key = f"{provider_id}:{model_id}" if model_id else provider_id
    with _CB_LOCK:
        if key not in _CIRCUIT_BREAKERS:
            _CIRCUIT_BREAKERS[key] = CircuitBreaker(
                failure_threshold=failure_threshold,
                recovery_timeout=recovery_timeout,
                name=f"cb_{key}"
            )
        return _CIRCUIT_BREAKERS[key]

