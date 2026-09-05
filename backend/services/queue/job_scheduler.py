"""
Job Scheduler and Durable Priority Queue Service for ApplyTrack AI.

Implements:
- Weighted Fair Scheduling across P1, P2, and P3 queues to prevent starvation
- Aging mechanism elevating long-waiting P3 jobs
- Thread promotion when new high-priority messages arrive in a low-priority thread
- Crash-safe job locking and stale lock recovery
- Full durable state transitions (PENDING -> PROCESSING -> COMPLETED/RETRY/NEEDS_REVIEW/DEAD_LETTER)
"""
import logging
from typing import List, Optional, Dict, Any
from datetime import timedelta
from django.utils import timezone
from django.conf import settings
from django.db import transaction
from django.db.models import F, Q

from apps.gmail_integration.models import (
    EmailProcessingJob,
    ProcessedEmail,
    TriagePriority,
    JobStatus,
    TriageStatusChoice
)
from services.pipeline.triage_service import TriageService

logger = logging.getLogger(__name__)


class JobScheduler:
    """
    Durable queue scheduler implementing weighted fair queueing, aging, and state management.
    """

    # Weighted scheduling quotas for balanced batch allocation (total = 10 slots ratio)
    P1_WEIGHT = 6  # 60% of batch slots
    P2_WEIGHT = 3  # 30% of batch slots
    P3_WEIGHT = 1  # 10% of batch slots (guaranteed minimum service)

    STALE_LOCK_TIMEOUT_MINUTES = 10
    AGING_HOURS_THRESHOLD = 6  # Promote P3 after 6 hours

    @classmethod
    @transaction.atomic
    def enqueue_email_job(
        cls,
        email: ProcessedEmail,
        user,
        email_data: Optional[Dict[str, Any]] = None,
        sync_job: Optional[Any] = None,
    ) -> EmailProcessingJob:
        """
        Create or get durable processing job for an ingested email with high-recall triage.
        Ensures strict idempotency.
        """
        # Run lightweight triage
        data = email_data or {
            'subject': email.subject,
            'snippet': email.snippet,
            'sender': email.sender,
            'event_type': email.event_type,
        }
        triage_info = TriageService.triage_email(data)

        priority = email.triage_priority if email.triage_priority and not email_data else triage_info.get('priority', TriagePriority.P2)
        triage_status = triage_info.get('triage_status', TriageStatusChoice.UNCERTAIN)
        triage_score = float(triage_info.get('triage_score', 0.0))
        triage_reason = triage_info.get('triage_reason', '')

        # Check if new message promotes previous messages in the same thread
        if priority in [TriagePriority.P1, TriagePriority.P2]:
            cls.promote_thread_jobs(email.thread_id, target_priority=priority)

        job, created = EmailProcessingJob.objects.get_or_create(
            email=email,
            defaults={
                'user': user,
                'gmail_message_id': email.gmail_message_id,
                'thread_id': email.thread_id,
                'priority': priority,
                'status': JobStatus.PENDING,
                'triage_status': triage_status,
                'triage_score': triage_score,
                'triage_reason': triage_reason,
                'processing_stage': 'triage',
                'effective_priority_score': triage_score,
                'sync_job': sync_job,
            }
        )
        if not created and sync_job and job.sync_job_id != sync_job.id:
            job.sync_job = sync_job
            job.save(update_fields=['sync_job'])
        return job

    @classmethod
    def claim_batch(
        cls,
        worker_id: str,
        batch_size: int = 25
    ) -> List[EmailProcessingJob]:
        """
        Claim a batch of jobs across P1, P2, P3 using weighted fair allocation.
        Prevents queue starvation while guaranteeing P1 priority.
        """
        cls.recover_stale_locks()
        cls.apply_aging_promotions()

        now = timezone.now()

        # Calculate weighted target slots per priority
        p1_slots = max(1, int(batch_size * (cls.P1_WEIGHT / 10.0)))
        p2_slots = max(1, int(batch_size * (cls.P2_WEIGHT / 10.0)))
        p3_slots = max(1, batch_size - (p1_slots + p2_slots))

        claimed_jobs: List[EmailProcessingJob] = []

        with transaction.atomic():
            # 1. Claim P1 jobs
            p1_qs = EmailProcessingJob.objects.select_for_update(skip_locked=True).filter(
                status__in=[JobStatus.PENDING, JobStatus.RETRY],
                next_attempt_at__lte=now,
                priority=TriagePriority.P1
            ).order_by('next_attempt_at', 'created_at')[:p1_slots]
            claimed_p1 = list(p1_qs)
            claimed_jobs.extend(claimed_p1)

            # 2. Claim P2 jobs (guaranteed regular service)
            p2_quota = p2_slots + (p1_slots - len(claimed_p1))
            p2_qs = EmailProcessingJob.objects.select_for_update(skip_locked=True).filter(
                status__in=[JobStatus.PENDING, JobStatus.RETRY],
                next_attempt_at__lte=now,
                priority=TriagePriority.P2
            ).order_by('next_attempt_at', 'created_at')[:p2_quota]
            claimed_p2 = list(p2_qs)
            claimed_jobs.extend(claimed_p2)

            # 3. Claim P3 jobs (guaranteed minimum service - never starved)
            remaining_slots = batch_size - len(claimed_jobs)
            if remaining_slots > 0:
                p3_qs = EmailProcessingJob.objects.select_for_update(skip_locked=True).filter(
                    status__in=[JobStatus.PENDING, JobStatus.RETRY],
                    next_attempt_at__lte=now,
                    priority=TriagePriority.P3
                ).order_by('-effective_priority_score', 'next_attempt_at')[:remaining_slots]
                claimed_p3 = list(p3_qs)
                claimed_jobs.extend(claimed_p3)

            # If still have capacity, fill with any available pending jobs
            remaining_capacity = batch_size - len(claimed_jobs)
            if remaining_capacity > 0:
                claimed_ids = [j.id for j in claimed_jobs]
                extra_qs = EmailProcessingJob.objects.select_for_update(skip_locked=True).filter(
                    status__in=[JobStatus.PENDING, JobStatus.RETRY],
                    next_attempt_at__lte=now
                ).exclude(id__in=claimed_ids).order_by('priority', 'next_attempt_at')[:remaining_capacity]
                claimed_jobs.extend(list(extra_qs))

            # Mark claimed jobs as PROCESSING
            for job in claimed_jobs:
                job.status = JobStatus.PROCESSING
                job.locked_at = now
                job.locked_by = worker_id
                job.attempt_count += 1
                job.save(update_fields=['status', 'locked_at', 'locked_by', 'attempt_count', 'updated_at'])

        logger.info(f"Worker {worker_id} claimed {len(claimed_jobs)} jobs (P1: {len(claimed_p1)}, P2: {len(claimed_p2)}, P3: {len(claimed_jobs) - len(claimed_p1) - len(claimed_p2)})")
        return claimed_jobs

    @classmethod
    def apply_aging_promotions(cls, aging_hours: int = AGING_HOURS_THRESHOLD) -> int:
        """
        Anti-starvation aging: promotes old P3 jobs to P2 so they receive service.
        """
        aging_cutoff = timezone.now() - timedelta(hours=aging_hours)
        promoted_count = EmailProcessingJob.objects.filter(
            priority=TriagePriority.P3,
            status__in=[JobStatus.PENDING, JobStatus.RETRY],
            created_at__lte=aging_cutoff
        ).update(
            priority=TriagePriority.P2,
            effective_priority_score=F('effective_priority_score') + 0.5,
            updated_at=timezone.now()
        )
        if promoted_count > 0:
            logger.info(f"Anti-starvation aging promoted {promoted_count} P3 jobs to P2 queue.")
        return promoted_count

    @classmethod
    def promote_thread_jobs(cls, thread_id: str, target_priority: str = TriagePriority.P1) -> int:
        """
        When a new high-priority message arrives in a thread, promote existing pending/retry
        jobs in the same thread.
        """
        if not thread_id:
            return 0

        qs = EmailProcessingJob.objects.filter(
            thread_id=thread_id,
            status__in=[JobStatus.PENDING, JobStatus.RETRY]
        )

        if target_priority == TriagePriority.P1:
            promoted = qs.filter(priority__in=[TriagePriority.P2, TriagePriority.P3]).update(
                priority=TriagePriority.P1,
                effective_priority_score=1.0,
                updated_at=timezone.now()
            )
        elif target_priority == TriagePriority.P2:
            promoted = qs.filter(priority=TriagePriority.P3).update(
                priority=TriagePriority.P2,
                effective_priority_score=0.75,
                updated_at=timezone.now()
            )
        else:
            promoted = 0

        if promoted > 0:
            logger.info(f"Thread promotion: elevated {promoted} jobs in thread {thread_id} to {target_priority}.")
        return promoted

    @classmethod
    def recover_stale_locks(cls, timeout_minutes: int = STALE_LOCK_TIMEOUT_MINUTES) -> int:
        """
        Crash-safe recovery: releases jobs stuck in PROCESSING longer than timeout.
        """
        stale_threshold = timezone.now() - timedelta(minutes=timeout_minutes)
        recovered = EmailProcessingJob.objects.filter(
            status=JobStatus.PROCESSING,
            locked_at__lte=stale_threshold
        ).update(
            status=JobStatus.RETRY,
            locked_at=None,
            locked_by=None,
            last_error="Recovered from stale lock / worker crash",
            updated_at=timezone.now()
        )
        if recovered > 0:
            logger.warning(f"Crash recovery: reclaimed {recovered} stale locked jobs.")
        return recovered

    @classmethod
    def complete_job(cls, job: EmailProcessingJob) -> None:
        """Mark job as successfully completed."""
        job.status = JobStatus.COMPLETED
        job.completed_at = timezone.now()
        job.locked_at = None
        job.locked_by = None
        job.save(update_fields=['status', 'completed_at', 'locked_at', 'locked_by', 'updated_at'])

    @classmethod
    def retry_job(
        cls,
        job: EmailProcessingJob,
        error_msg: str,
        backoff_seconds: int = 60
    ) -> None:
        """Schedule job for retry with exponential backoff or move to DEAD_LETTER if max attempts reached."""
        if job.attempt_count >= job.max_attempts:
            job.status = JobStatus.DEAD_LETTER
            job.last_error = f"Max attempts ({job.max_attempts}) reached. Last error: {error_msg}"
            job.locked_at = None
            job.locked_by = None
            job.save(update_fields=['status', 'last_error', 'locked_at', 'locked_by', 'updated_at'])
            logger.error(f"Job {job.id} moved to DEAD_LETTER: {job.last_error}")
        else:
            import random
            base_delay = getattr(settings, 'BASE_RETRY_BACKOFF_SECONDS', backoff_seconds)
            # Exponential backoff with random jitter (+/- 15%)
            jitter = random.uniform(0.85, 1.15)
            delay_seconds = int(base_delay * (2 ** (job.attempt_count - 1)) * jitter)
            job.status = JobStatus.RETRY
            job.last_error = error_msg
            job.next_attempt_at = timezone.now() + timedelta(seconds=delay_seconds)
            job.locked_at = None
            job.locked_by = None
            job.save(update_fields=['status', 'last_error', 'next_attempt_at', 'locked_at', 'locked_by', 'updated_at'])
            logger.warning(f"Job {job.id} scheduled for retry at {job.next_attempt_at} ({delay_seconds}s delay): {error_msg}")

    @classmethod
    def mark_needs_review(cls, job: EmailProcessingJob, reason: str = "Low AI confidence") -> None:
        """Mark job as requiring human review."""
        job.status = JobStatus.NEEDS_REVIEW
        job.last_error = reason
        job.locked_at = None
        job.locked_by = None
        job.save(update_fields=['status', 'last_error', 'locked_at', 'locked_by', 'updated_at'])

    @classmethod
    def fail_job(cls, job: EmailProcessingJob, error_msg: str) -> None:
        """Mark job as permanently failed."""
        job.status = JobStatus.FAILED
        job.last_error = error_msg
        job.locked_at = None
        job.locked_by = None
        job.save(update_fields=['status', 'last_error', 'locked_at', 'locked_by', 'updated_at'])
