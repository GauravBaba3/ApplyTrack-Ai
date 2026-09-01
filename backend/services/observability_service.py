"""
Observability and Telemetry Service for ApplyTrack AI.

Provides metrics on:
- Gmail sync success / failure metrics
- Queue depth (P1, P2, P3, In-Progress, Retrying, Dead-Letter)
- Classification tier distribution (Rule Engine, HF, Groq, Gemini, OpenRouter, Review)
- LLM Provider rate limiter usage and circuit breaker states
- Average processing duration & error rates

Strict Privacy Policy:
- Never records API keys, OAuth tokens, or private email bodies.
"""
import logging
from typing import Dict, Any
from django.db.models import Count, Avg
from apps.gmail_integration.models import (
    ProcessedEmail,
    EmailProcessingJob,
    JobStatus,
    TriagePriority,
    ProcessingStatus,
    ProviderUsageLog
)
from apps.applications.models import Application, StatusHistory
from services.pipeline.circuit_breaker import CircuitBreaker, CircuitState
from services.pipeline.rate_limiter import ProviderRateLimiter

logger = logging.getLogger(__name__)


class ObservabilityService:
    """
    Central service for gathering real-time telemetry and health metrics.
    """

    @classmethod
    def get_system_metrics(cls, user=None) -> Dict[str, Any]:
        """
        Compute high-level system telemetry and health statistics.
        """
        email_qs = ProcessedEmail.objects.all()
        job_qs = EmailProcessingJob.objects.all()
        history_qs = StatusHistory.objects.all()
        usage_qs = ProviderUsageLog.objects.all()

        if user:
            email_qs = email_qs.filter(user=user)
            job_qs = job_qs.filter(user=user)
            history_qs = history_qs.filter(application__user=user)
            usage_qs = usage_qs.filter(user=user)

        # 1. Queue Depths
        queue_stats = job_qs.values('status').annotate(count=Count('id'))
        queue_map = {item['status']: item['count'] for item in queue_stats}

        priority_stats = job_qs.filter(status=JobStatus.PENDING).values('priority').annotate(count=Count('id'))
        priority_map = {item['priority']: item['count'] for item in priority_stats}

        # 2. Classification Tier Breakdown
        tier_stats = history_qs.values('source').annotate(count=Count('id'))
        tier_map = {item['source']: item['count'] for item in tier_stats}

        # 3. Provider Quota & Circuit Breaker Health
        providers = ['gmail', 'huggingface', 'groq', 'gemini', 'openrouter']
        provider_health = {}
        for p in providers:
            cb_state = CircuitBreaker.get_state(p)
            provider_health[p] = {
                'circuit_state': cb_state.value if hasattr(cb_state, 'value') else str(cb_state),
                'is_in_cooldown': ProviderRateLimiter.is_in_cooldown(p),
                'current_in_flight': ProviderRateLimiter.get_in_flight(p)
            }

        # 4. Usage summary (Tokens & Latencies)
        provider_usage = usage_qs.values('provider').annotate(
            total_tokens=Avg('total_tokens'),
            avg_latency_ms=Avg('latency_ms'),
            call_count=Count('id')
        )

        return {
            'queue_metrics': {
                'pending_p1': priority_map.get(TriagePriority.P1, 0),
                'pending_p2': priority_map.get(TriagePriority.P2, 0),
                'pending_p3': priority_map.get(TriagePriority.P3, 0),
                'in_progress': queue_map.get(JobStatus.IN_PROGRESS, 0),
                'retrying': queue_map.get(JobStatus.RETRY, 0),
                'completed': queue_map.get(JobStatus.COMPLETED, 0),
                'dead_letter': queue_map.get(JobStatus.DEAD_LETTER, 0),
            },
            'tier_distribution': tier_map,
            'provider_health': provider_health,
            'provider_usage_summary': list(provider_usage),
            'total_emails_ingested': email_qs.count(),
            'needs_review_count': email_qs.filter(processing_status=ProcessingStatus.NEEDS_REVIEW).count(),
        }
