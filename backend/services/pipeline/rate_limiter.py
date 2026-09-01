"""
Per-Provider Rate Limiter and Quota Management for ApplyTrack AI.

Implements token bucket and sliding window rate limiting across:
- Requests Per Minute (RPM)
- Requests Per Day (RPD)
- Tokens Per Minute (TPM)
- Tokens Per Day (TPD)
- Provider-specific in-flight concurrency limits
- Dynamic header-based adjustments (Retry-After, x-ratelimit-*)
"""
import time
import threading
import logging
from typing import Dict, Any, Tuple, Optional
from django.conf import settings

logger = logging.getLogger(__name__)


class ProviderQuota:
    """Configured rate and token limits for a specific provider."""
    def __init__(
        self,
        max_rpm: int = 30,
        max_rpd: int = 14400,
        max_tpm: int = 40000,
        max_tpd: int = 1000000,
        max_concurrent_requests: int = 2
    ):
        self.max_rpm = max_rpm
        self.max_rpd = max_rpd
        self.max_tpm = max_tpm
        self.max_tpd = max_tpd
        self.max_concurrent_requests = max_concurrent_requests


class ProviderRateLimiter:
    """
    Thread-safe rate limiter tracking RPM, RPD, TPM, TPD, and in-flight concurrency.
    """

    _lock = threading.Lock()

    # Default provider quotas (conservative defaults)
    DEFAULT_QUOTAS: Dict[str, ProviderQuota] = {
        'gmail': ProviderQuota(max_rpm=60, max_rpd=50000, max_tpm=100000, max_tpd=5000000, max_concurrent_requests=3),
        'huggingface': ProviderQuota(max_rpm=30, max_rpd=5000, max_tpm=30000, max_tpd=500000, max_concurrent_requests=2),
        'groq': ProviderQuota(max_rpm=30, max_rpd=14400, max_tpm=40000, max_tpd=1000000, max_concurrent_requests=2),
        'gemini': ProviderQuota(max_rpm=15, max_rpd=1500, max_tpm=32000, max_tpd=1000000, max_concurrent_requests=1),
        'openrouter': ProviderQuota(max_rpm=20, max_rpd=5000, max_tpm=40000, max_tpd=1000000, max_concurrent_requests=2),
    }

    # In-memory sliding window counters: {provider: [(timestamp, tokens)]}
    _minute_requests: Dict[str, list] = {}
    _day_requests: Dict[str, list] = {}
    _in_flight: Dict[str, int] = {}
    _header_retry_after_until: Dict[str, float] = {}

    @classmethod
    def get_quota(cls, provider: str) -> ProviderQuota:
        """Get configured quota for provider."""
        return cls.DEFAULT_QUOTAS.get(provider.lower(), ProviderQuota())

    @classmethod
    def can_acquire(cls, provider: str, estimated_tokens: int = 100) -> Tuple[bool, str]:
        """
        Check if request can be made without exceeding RPM, RPD, TPM, TPD, or in-flight concurrency.
        """
        p = provider.lower()
        now = time.time()

        with cls._lock:
            # 1. Check Retry-After cooldown from headers
            retry_until = cls._header_retry_after_until.get(p, 0.0)
            if now < retry_until:
                wait_sec = int(retry_until - now)
                return False, f"Provider [{p}] Retry-After header cooldown active ({wait_sec}s remaining)"

            quota = cls.get_quota(p)

            # 2. Check in-flight active concurrency
            active = cls._in_flight.get(p, 0)
            if active >= quota.max_concurrent_requests:
                return False, f"Provider [{p}] at max in-flight concurrency ({active}/{quota.max_concurrent_requests})"

            # 3. Clean sliding windows
            minute_cutoff = now - 60.0
            day_cutoff = now - 86400.0

            cls._minute_requests[p] = [e for e in cls._minute_requests.get(p, []) if e[0] >= minute_cutoff]
            cls._day_requests[p] = [e for e in cls._day_requests.get(p, []) if e[0] >= day_cutoff]

            # 4. Check RPM & TPM
            rpm_count = len(cls._minute_requests[p])
            tpm_count = sum(e[1] for e in cls._minute_requests[p])

            if rpm_count >= quota.max_rpm:
                return False, f"Provider [{p}] exceeded RPM limit ({rpm_count}/{quota.max_rpm})"
            if (tpm_count + estimated_tokens) > quota.max_tpm:
                return False, f"Provider [{p}] exceeded TPM limit ({tpm_count + estimated_tokens}/{quota.max_tpm})"

            # 5. Check RPD & TPD
            rpd_count = len(cls._day_requests[p])
            tpd_count = sum(e[1] for e in cls._day_requests[p])

            if rpd_count >= quota.max_rpd:
                return False, f"Provider [{p}] exceeded RPD limit ({rpd_count}/{quota.max_rpd})"
            if (tpd_count + estimated_tokens) > quota.max_tpd:
                return False, f"Provider [{p}] exceeded TPD limit ({tpd_count + estimated_tokens}/{quota.max_tpd})"

            return True, "OK"

    @classmethod
    def acquire(cls, provider: str, estimated_tokens: int = 100) -> bool:
        """
        Record a request start and increment in-flight concurrency.
        """
        p = provider.lower()
        now = time.time()
        with cls._lock:
            cls._in_flight[p] = cls._in_flight.get(p, 0) + 1
            if p not in cls._minute_requests:
                cls._minute_requests[p] = []
            if p not in cls._day_requests:
                cls._day_requests[p] = []
            cls._minute_requests[p].append((now, estimated_tokens))
            cls._day_requests[p].append((now, estimated_tokens))
            return True

    @classmethod
    def release(cls, provider: str) -> None:
        """
        Decrement active in-flight concurrency for provider.
        """
        p = provider.lower()
        with cls._lock:
            current = cls._in_flight.get(p, 0)
            if current > 0:
                cls._in_flight[p] = current - 1

    @classmethod
    def update_from_headers(cls, provider: str, headers: Dict[str, Any]) -> None:
        """
        Parse HTTP rate-limit response headers dynamically.
        Supports: Retry-After, x-ratelimit-remaining-requests, x-ratelimit-remaining-tokens, etc.
        """
        if not headers:
            return

        p = provider.lower()
        now = time.time()

        # Check Retry-After (seconds or date)
        retry_after = headers.get('retry-after') or headers.get('Retry-After')
        if retry_after:
            try:
                delay = float(retry_after)
                with cls._lock:
                    cls._header_retry_after_until[p] = now + delay
                    logger.warning(f"ProviderRateLimiter: [{p}] Retry-After header received ({delay}s). Cooldown set.")
            except (ValueError, TypeError):
                pass

        # Check remaining requests header (only if retry-after was not already explicitly provided)
        if not retry_after:
            rem_req = headers.get('x-ratelimit-remaining-requests') or headers.get('ratelimit-remaining')
            if rem_req is not None:
                try:
                    rem_count = int(rem_req)
                    if rem_count == 0:
                        with cls._lock:
                            cls._header_retry_after_until[p] = now + 60.0
                            logger.warning(f"ProviderRateLimiter: [{p}] Remaining requests = 0. Cooldown set for 60s.")
                except (ValueError, TypeError):
                    pass

    @classmethod
    def is_in_cooldown(cls, provider: str) -> bool:
        """Check if provider is in active Retry-After cooldown."""
        p = provider.lower()
        with cls._lock:
            return time.time() < cls._header_retry_after_until.get(p, 0.0)

    @classmethod
    def get_in_flight(cls, provider: str) -> int:
        """Get active in-flight request count for provider."""
        p = provider.lower()
        with cls._lock:
            return cls._in_flight.get(p, 0)

    @classmethod
    def configure_provider(
        cls,
        provider: str,
        rpm: int = 30,
        rpd: int = 14400,
        tpm: int = 40000,
        tpd: int = 1000000,
        max_concurrent: int = 2
    ) -> None:
        """Dynamically configure quota for a provider (useful in tests/custom overrides)."""
        with cls._lock:
            cls.DEFAULT_QUOTAS[provider.lower()] = ProviderQuota(
                max_rpm=rpm,
                max_rpd=rpd,
                max_tpm=tpm,
                max_tpd=tpd,
                max_concurrent_requests=max_concurrent
            )

    @classmethod
    def reset(cls) -> None:
        """Reset rate limiter state (for testing)."""
        with cls._lock:
            cls._minute_requests = {}
            cls._day_requests = {}
            cls._in_flight = {}
            cls._header_retry_after_until = {}

    reset_all = reset
