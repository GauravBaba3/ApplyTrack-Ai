"""
Circuit Breaker Pattern for AI Providers in ApplyTrack AI.

Protects against repeated provider failures and cascading downtime:
- CLOSED: Normal operation (requests pass through).
- OPEN: Provider in failure state (fails fast without network latency).
- HALF_OPEN: Probation state (allows 1 trial request to probe provider recovery).
"""
import time
import threading
import logging
from enum import Enum
from typing import Dict, Any, Tuple

logger = logging.getLogger(__name__)


class CircuitState(str, Enum):
    CLOSED = "CLOSED"      # Normal operation
    OPEN = "OPEN"          # Failing fast, in cooldown
    HALF_OPEN = "HALF_OPEN"# Probation trial request


class CircuitBreaker:
    """
    Thread-safe circuit breaker managing provider failure thresholds and recovery.
    """

    _lock = threading.Lock()

    FAILURE_THRESHOLD = 3         # Consecutive failures before opening circuit
    BASE_COOLDOWN_SECONDS = 60    # Initial cooldown duration in seconds
    MAX_COOLDOWN_SECONDS = 600    # Max cooldown duration (10 minutes)

    # State per provider: {provider: {'state': CircuitState, 'failures': int, 'cooldown_until': float, 'cooldown_duration': float}}
    _circuits: Dict[str, Dict[str, Any]] = {}

    @classmethod
    def _get_or_create(cls, provider: str) -> Dict[str, Any]:
        p = provider.lower()
        if p not in cls._circuits:
            cls._circuits[p] = {
                'state': CircuitState.CLOSED,
                'failures': 0,
                'cooldown_until': 0.0,
                'cooldown_duration': cls.BASE_COOLDOWN_SECONDS,
                'last_error': ''
            }
        return cls._circuits[p]

    @classmethod
    def get_state(cls, provider: str) -> CircuitState:
        """Get current circuit state, transitioning from OPEN to HALF_OPEN if cooldown expired."""
        p = provider.lower()
        now = time.time()
        with cls._lock:
            c = cls._get_or_create(p)
            if c['state'] == CircuitState.OPEN and now >= c['cooldown_until']:
                c['state'] = CircuitState.HALF_OPEN
                logger.info(f"CircuitBreaker: Provider [{p}] cooldown expired. Transitioned to HALF_OPEN probation.")
            return c['state']

    @classmethod
    def is_allowed(cls, provider: str) -> bool:
        """Check if request is permitted by circuit breaker."""
        state = cls.get_state(provider)
        return state in [CircuitState.CLOSED, CircuitState.HALF_OPEN]

    @classmethod
    def record_success(cls, provider: str) -> None:
        """Record successful provider response; resets failures and closes circuit."""
        p = provider.lower()
        with cls._lock:
            c = cls._get_or_create(p)
            if c['state'] == CircuitState.HALF_OPEN:
                logger.info(f"CircuitBreaker: Provider [{p}] probe succeeded! Transitioned back to CLOSED.")
            c['state'] = CircuitState.CLOSED
            c['failures'] = 0
            c['cooldown_duration'] = cls.BASE_COOLDOWN_SECONDS
            c['last_error'] = ''

    @classmethod
    def record_failure(cls, provider: str, reason: str = "") -> None:
        """Record provider error; increments failure count and opens circuit if threshold reached."""
        p = provider.lower()
        now = time.time()
        with cls._lock:
            c = cls._get_or_create(p)
            c['failures'] += 1
            c['last_error'] = reason

            if c['state'] == CircuitState.HALF_OPEN or c['failures'] >= cls.FAILURE_THRESHOLD:
                c['state'] = CircuitState.OPEN
                duration = min(c['cooldown_duration'] * (2 if c['state'] == CircuitState.HALF_OPEN else 1), cls.MAX_COOLDOWN_SECONDS)
                c['cooldown_duration'] = duration
                c['cooldown_until'] = now + duration
                logger.warning(f"CircuitBreaker: Provider [{p}] circuit OPENED for {duration}s. Reason: {reason} (Failures: {c['failures']})")

    @classmethod
    def reset(cls) -> None:
        """Reset all circuit breakers (for testing)."""
        with cls._lock:
            cls._circuits = {}

    reset_all = reset
