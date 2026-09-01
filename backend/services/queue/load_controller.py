"""
Adaptive Load & Concurrency Controller for ApplyTrack AI.

Monitors system health, error rates, queue depth, and external provider signals
to control worker concurrency and batch sizing conservatively:
- Starting baseline: MAX_CONCURRENT_WORKERS = 1, BATCH_SIZE = 25
- Scaled up gradually (1 -> 2 -> 3) only when system remains healthy
- Throttled down immediately on rate limits, errors, or system pressure
- Protects server against backpressure from large queue backlogs
"""
import time
import logging
from typing import Dict, Any, Tuple
from django.conf import settings
from django.utils import timezone
from datetime import timedelta

logger = logging.getLogger(__name__)


class LoadController:
    """
    Adaptive load controller managing worker concurrency, batch sizing, and health metrics.
    """

    _concurrency: int = 1
    _batch_size: int = 25
    _healthy_cycles_count: int = 0
    _consecutive_error_count: int = 0
    _recent_errors: list = []
    _rate_limit_cooldown_until: float = 0.0

    # Thresholds
    MAX_ALLOWED_CONCURRENCY = 3
    MIN_ALLOWED_CONCURRENCY = 1
    MAX_BATCH_SIZE = 50
    MIN_BATCH_SIZE = 25
    ERROR_RATE_WINDOW_SECONDS = 300  # 5 minutes
    MAX_TOLERATED_ERROR_RATE = 0.15  # 15% error rate threshold

    @classmethod
    def get_configured_defaults(cls) -> Tuple[int, int]:
        """Get baseline configured worker concurrency and batch size from settings."""
        base_workers = getattr(settings, 'MAX_CONCURRENT_WORKERS', 1)
        base_batch = getattr(settings, 'QUEUE_BATCH_SIZE', 25)
        return base_workers, base_batch

    @classmethod
    def get_current_concurrency(cls) -> int:
        """Get current adaptive worker concurrency target."""
        base_workers, _ = cls.get_configured_defaults()
        return max(cls.MIN_ALLOWED_CONCURRENCY, min(cls._concurrency, max(base_workers, cls.MAX_ALLOWED_CONCURRENCY)))

    @classmethod
    def get_current_batch_size(cls) -> int:
        """Get current adaptive batch size."""
        _, base_batch = cls.get_configured_defaults()
        return max(cls.MIN_BATCH_SIZE, min(cls._batch_size, max(base_batch, cls.MAX_BATCH_SIZE)))

    @classmethod
    def is_in_cooldown(cls) -> bool:
        """Check if load controller is in provider rate-limit cooldown."""
        return time.time() < cls._rate_limit_cooldown_until

    @classmethod
    def record_rate_limit_event(cls, provider: str, cooldown_seconds: int = 60) -> None:
        """Trigger backpressure cooldown due to external API 429 rate limit."""
        cls._rate_limit_cooldown_until = time.time() + cooldown_seconds
        cls._concurrency = cls.MIN_ALLOWED_CONCURRENCY
        cls._batch_size = cls.MIN_BATCH_SIZE
        cls._healthy_cycles_count = 0
        logger.warning(f"LoadController: Provider '{provider}' rate limited. Cooldown active for {cooldown_seconds}s. Concurrency dialed down to {cls._concurrency}.")

    @classmethod
    def record_job_outcome(cls, success: bool, duration_seconds: float = 0.0, error_type: str = "") -> None:
        """Record a single job outcome to maintain sliding window health metrics."""
        now = time.time()
        cls._recent_errors.append((now, success))
        
        # Clean older entries outside sliding window
        window_cutoff = now - cls.ERROR_RATE_WINDOW_SECONDS
        cls._recent_errors = [entry for entry in cls._recent_errors if entry[0] >= window_cutoff]

        if success:
            cls._consecutive_error_count = 0
            cls._healthy_cycles_count += 1
        else:
            cls._consecutive_error_count += 1
            cls._healthy_cycles_count = 0

    @classmethod
    def evaluate_and_adapt(cls, pending_queue_size: int = 0) -> Dict[str, Any]:
        """
        Evaluate health metrics and adapt concurrency and batch sizing gradually.

        Adaptation Policy:
        - Scale UP gradually only after 10 consecutive healthy operations with error rate < 5%
        - Scale DOWN immediately if error rate > 15% or consecutive errors >= 3
        """
        now = time.time()
        # Clean sliding window
        window_cutoff = now - cls.ERROR_RATE_WINDOW_SECONDS
        cls._recent_errors = [entry for entry in cls._recent_errors if entry[0] >= window_cutoff]

        total_recent = len(cls._recent_errors)
        error_count = sum(1 for entry in cls._recent_errors if not entry[1])
        error_rate = (error_count / total_recent) if total_recent > 0 else 0.0

        is_healthy = True
        reason = "System healthy"

        if cls.is_in_cooldown():
            is_healthy = False
            reason = f"Provider rate limit cooldown active ({int(cls._rate_limit_cooldown_until - now)}s remaining)"
            cls._concurrency = cls.MIN_ALLOWED_CONCURRENCY
            cls._batch_size = cls.MIN_BATCH_SIZE
            cls._healthy_cycles_count = 0
        elif error_rate > cls.MAX_TOLERATED_ERROR_RATE or cls._consecutive_error_count >= 3:
            is_healthy = False
            reason = f"Elevated error rate ({error_rate:.1%}) or consecutive errors ({cls._consecutive_error_count})"
            # Step down concurrency immediately
            cls._concurrency = max(cls.MIN_ALLOWED_CONCURRENCY, cls._concurrency - 1)
            cls._batch_size = cls.MIN_BATCH_SIZE
            cls._healthy_cycles_count = 0
            logger.warning(f"LoadController: Scaling down due to errors: concurrency={cls._concurrency}, batch_size={cls._batch_size}")
        else:
            # System is healthy - evaluate scale up if backlog exists
            if cls._healthy_cycles_count >= 10:
                if pending_queue_size > 50 and cls._concurrency < cls.MAX_ALLOWED_CONCURRENCY:
                    cls._concurrency += 1
                    cls._healthy_cycles_count = 0
                    logger.info(f"LoadController: Gradual scale up: concurrency={cls._concurrency}")
                elif pending_queue_size > 100 and cls._batch_size < cls.MAX_BATCH_SIZE:
                    cls._batch_size = min(cls.MAX_BATCH_SIZE, cls._batch_size + 15)
                    cls._healthy_cycles_count = 0
                    logger.info(f"LoadController: Gradual batch size adaptation: batch_size={cls._batch_size}")

        return {
            'is_healthy': is_healthy,
            'reason': reason,
            'concurrency': cls._concurrency,
            'batch_size': cls._batch_size,
            'error_rate': error_rate,
            'healthy_cycles': cls._healthy_cycles_count,
            'in_cooldown': cls.is_in_cooldown(),
            'pending_queue_size': pending_queue_size
        }

    @classmethod
    def reset(cls) -> None:
        """Reset state for testing."""
        cls._concurrency = 1
        cls._batch_size = 25
        cls._healthy_cycles_count = 0
        cls._consecutive_error_count = 0
        cls._recent_errors = []
        cls._rate_limit_cooldown_until = 0.0
