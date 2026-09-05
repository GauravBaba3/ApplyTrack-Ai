"""
Gmail Sync Coordinator for ApplyTrack AI.

Durable producer service executing server-side Gmail ingestion:
- Manages durable GmailSyncJob lifecycle stored in Neon PostgreSQL
- Atomic lease acquisition (select_for_update) and stale lease recovery
- Safe cursor progression (fetch page -> persist emails -> queue jobs -> COMMIT -> advance checkpoint)
- Independent from Django web-process and browser lifetimes
- Coordinates backpressure with the downstream EmailWorker queue
"""
import time
import logging
from datetime import timedelta
from typing import Optional, Dict, Any, Callable
from django.utils import timezone
from django.db import transaction
from django.db.models import Q
from django.conf import settings

from apps.gmail_integration.models import (
    GmailSyncJob,
    SyncJobStatus,
    ProcessedEmail,
    EmailProcessingJob,
    JobStatus,
    SyncLog,
)
from services.gmail_service import GmailService
from services.sync_service import SyncService

logger = logging.getLogger(__name__)


class GmailSyncCoordinator:
    """
    Coordinates durable background Gmail ingestion jobs across worker processes.
    """

    STALE_LEASE_SECONDS = 300  # 5 minutes

    @classmethod
    def request_sync(cls, user, reset: bool = False) -> GmailSyncJob:
        """
        Atomically request or activate a durable server-side Gmail sync job for the user.

        Locking / De-duplication rules:
        - If an active job (PENDING or non-stale RUNNING) exists:
          return that existing job immediately (enforcing 1 active sync per user).
        - If a RUNNING job has an expired lease (> 5 min heartbeat):
          reclaim it, reset its status to PENDING, and return it.
        - If reset=True:
          reset cursor, page, and counter checkpoints, and set status to PENDING.
        - Otherwise, create a new PENDING GmailSyncJob in Neon.
        """
        now = timezone.now()
        stale_threshold = now - timedelta(seconds=cls.STALE_LEASE_SECONDS)

        with transaction.atomic():
            active_job = GmailSyncJob.objects.select_for_update().filter(
                user=user,
                status__in=[SyncJobStatus.PENDING, SyncJobStatus.RUNNING],
            ).order_by('-created_at').first()

            if active_job:
                is_stale = (
                    active_job.status == SyncJobStatus.RUNNING
                    and active_job.last_heartbeat_at
                    and active_job.last_heartbeat_at < stale_threshold
                )

                if is_stale or reset:
                    logger.warning(
                        f"[SYNC_JOB_RESET] User {user.id} job #{active_job.id} "
                        f"(stale={is_stale}, reset={reset}). Resetting to PENDING."
                    )
                    active_job.status = SyncJobStatus.PENDING
                    active_job.worker_id = None
                    active_job.last_heartbeat_at = now
                    active_job.started_at = now
                    if reset:
                        active_job.cursor = None
                        active_job.page = 0
                        active_job.pages_processed = 0
                        active_job.emails_fetched = 0
                        active_job.emails_stored = 0
                        active_job.emails_queued = 0
                        active_job.job_related_emails = 0
                        active_job.applications_updated = 0
                        active_job.new_applications = 0
                        active_job.needs_review = 0
                    active_job.save()

                    # Also update user mirror state
                    user.gmail_sync_status = 'running'
                    user.gmail_sync_started_at = now
                    if reset:
                        user.gmail_sync_page = 0
                        user.gmail_sync_cursor = None
                        user.gmail_sync_batch_stats = {
                            "emails_scanned": 0,
                            "job_related_emails": 0,
                            "applications_updated": 0,
                            "new_applications": 0,
                            "needs_review": 0,
                            "pages_processed": 0,
                        }
                    user.save(update_fields=[
                        'gmail_sync_status', 'gmail_sync_started_at',
                        'gmail_sync_page', 'gmail_sync_cursor', 'gmail_sync_batch_stats'
                    ])
                    return active_job

                # Active, non-stale job already running
                logger.info(
                    f"[SYNC_LOCK_ACTIVE] User {user.id} already has active sync job #{active_job.id} "
                    f"({active_job.status}, worker={active_job.worker_id}). Returning existing job."
                )
                return active_job

            # No active job — check if user has previous cursor checkpoint to resume from
            cursor = None if reset else user.gmail_sync_cursor
            page = 0 if reset else user.gmail_sync_page

            job = GmailSyncJob.objects.create(
                user=user,
                status=SyncJobStatus.PENDING,
                cursor=cursor,
                page=page,
                last_heartbeat_at=now,
                started_at=now,
            )

            user.gmail_sync_status = 'running'
            user.gmail_sync_started_at = now
            if reset:
                user.gmail_sync_cursor = None
                user.gmail_sync_page = 0
                user.gmail_sync_batch_stats = {
                    "emails_scanned": 0,
                    "job_related_emails": 0,
                    "applications_updated": 0,
                    "new_applications": 0,
                    "needs_review": 0,
                    "pages_processed": 0,
                }
            user.save(update_fields=[
                'gmail_sync_status', 'gmail_sync_started_at',
                'gmail_sync_cursor', 'gmail_sync_page', 'gmail_sync_batch_stats'
            ])

            logger.info(
                f"[SYNC_JOB_CREATED] User {user.id} created durable GmailSyncJob #{job.id} (reset={reset})"
            )
            return job

    @classmethod
    def claim_next_job(cls, worker_id: str) -> Optional[GmailSyncJob]:
        """
        Atomically claim the next PENDING or stale RUNNING GmailSyncJob.
        Uses select_for_update(skip_locked=True) for race-free multi-worker concurrency.
        """
        now = timezone.now()
        stale_threshold = now - timedelta(seconds=cls.STALE_LEASE_SECONDS)

        with transaction.atomic():
            job = GmailSyncJob.objects.select_for_update(skip_locked=True).filter(
                Q(status=SyncJobStatus.PENDING) |
                Q(status=SyncJobStatus.RUNNING, last_heartbeat_at__lt=stale_threshold)
            ).order_by('created_at').first()

            if not job:
                return None

            was_stale = job.status == SyncJobStatus.RUNNING
            job.status = SyncJobStatus.RUNNING
            job.worker_id = worker_id
            job.last_heartbeat_at = now
            if not job.started_at:
                job.started_at = now
            job.save(update_fields=['status', 'worker_id', 'last_heartbeat_at', 'started_at'])

            if was_stale:
                logger.warning(
                    f"[SYNC_LEASE_RECOVERED] Worker {worker_id} reclaimed stale GmailSyncJob #{job.id} "
                    f"for user {job.user_id} (resuming from cursor '{job.cursor}', page {job.page})"
                )
            else:
                logger.info(
                    f"[SYNC_JOB_CLAIMED] Worker {worker_id} claimed GmailSyncJob #{job.id} "
                    f"for user {job.user_id} (cursor '{job.cursor}', page {job.page})"
                )
            return job

    @classmethod
    def execute_sync_job(
        cls,
        job_id: int,
        worker_id: str,
        should_stop_callable: Optional[Callable[[], bool]] = None,
        max_pages: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Execute a claimed GmailSyncJob page by page until complete, stopped, or error.

        CRITICAL COMMIT ORDERING (Requirement 6):
        1. Fetch Gmail page
        2. Persist email data + queue jobs in atomic transaction
        3. Transaction COMMITS
        4. Advance cursor checkpoint + update heartbeat
        5. Continue next Gmail page
        """
        try:
            job = GmailSyncJob.objects.get(id=job_id)
        except GmailSyncJob.DoesNotExist:
            logger.error(f"[SYNC_JOB_NOT_FOUND] Job #{job_id} does not exist.")
            return {'success': False, 'error': f'Job #{job_id} not found'}

        user = job.user
        logger.info(
            f"[SYNC_EXEC_START] Worker {worker_id} starting GmailSyncJob #{job.id} "
            f"for user {user.id} ({user.email}) page={job.page} cursor='{job.cursor}'"
        )

        page_limit = getattr(settings, "GMAIL_SYNC_PAGE_SIZE", 25)
        initial_days = getattr(settings, "GMAIL_INITIAL_SYNC_DAYS",
                               getattr(settings, "GMAIL_SYNC_INITIAL_DAYS", 365))
        backpressure_threshold = getattr(settings, "SYNC_BACKPRESSURE_QUEUE_SIZE", 200)
        backpressure_sleep = getattr(settings, "SYNC_BACKPRESSURE_SLEEP_SECONDS", 5)

        pages_in_this_run = 0

        try:
            gmail_service = GmailService(user)
            after_timestamp = None
            if not job.cursor and user.gmail_last_sync and job.page == 0:
                after_timestamp = user.gmail_last_sync - timedelta(days=1)

            while True:
                if should_stop_callable and should_stop_callable():
                    logger.info(f"[SYNC_STOP_REQUESTED] Worker {worker_id} stopping job #{job.id} cleanly.")
                    # Keep as RUNNING or PENDING so it can be resumed
                    job.status = SyncJobStatus.PENDING
                    job.last_heartbeat_at = timezone.now()
                    job.save(update_fields=['status', 'last_heartbeat_at'])
                    return {'success': True, 'stopped': True, 'pages': pages_in_this_run}

                if max_pages and pages_in_this_run >= max_pages:
                    logger.info(f"[SYNC_MAX_PAGES_REACHED] Job #{job.id} reached run limit ({max_pages}).")
                    break

                # Backpressure: pause ingestion if email worker is lagging behind
                pending_jobs_count = EmailProcessingJob.objects.filter(
                    user=user,
                    status__in=[JobStatus.PENDING, JobStatus.RETRY],
                ).count()
                if pending_jobs_count > backpressure_threshold:
                    logger.info(
                        f"[SYNC_BACKPRESSURE] User {user.id} has {pending_jobs_count} pending jobs. "
                        f"Pausing {backpressure_sleep}s for EmailWorker to consume..."
                    )
                    time.sleep(backpressure_sleep)

                # Fetch one Gmail page
                try:
                    message_stubs, next_page_token = gmail_service.get_message_page(
                        page_token=job.cursor,
                        max_results=page_limit,
                        days_back=initial_days,
                        after_timestamp=after_timestamp,
                    )
                except Exception as e:
                    logger.error(
                        f"[GMAIL_PAGE_FETCH_ERROR] User {user.id} page {job.page + 1}: {e}",
                        exc_info=True
                    )
                    job.last_error = f"Gmail fetch error: {str(e)}"
                    job.retry_count += 1
                    if job.retry_count >= job.max_retries:
                        job.status = SyncJobStatus.FAILED
                        user.gmail_sync_status = 'failed'
                        user.save(update_fields=['gmail_sync_status'])
                    else:
                        job.status = SyncJobStatus.PENDING
                    job.last_heartbeat_at = timezone.now()
                    job.save(update_fields=['status', 'last_error', 'retry_count', 'last_heartbeat_at'])
                    return {'success': False, 'error': str(e)}

                logger.info(
                    f"[GMAIL_PAGE_FETCHED] User {user.id} page {job.page + 1}: "
                    f"{len(message_stubs)} messages, has_more={bool(next_page_token)}"
                )

                page_emails_stored = 0
                page_batch_result = {
                    "emails_scanned": len(message_stubs),
                    "job_related_emails": 0,
                    "applications_updated": 0,
                    "new_applications": 0,
                    "needs_review": 0,
                }

                # --- STEP 2: Persist emails & queue jobs in transaction ---
                if message_stubs:
                    stub_ids = [m["id"] for m in message_stubs if "id" in m]
                    existing_ids = set(
                        ProcessedEmail.objects.filter(
                            user=user,
                            gmail_message_id__in=stub_ids,
                        ).values_list("gmail_message_id", flat=True)
                    )

                    for stub in message_stubs:
                        msg_id = stub.get("id")
                        if not msg_id or msg_id in existing_ids:
                            continue
                        try:
                            full_msg = gmail_service.fetch_and_parse_message(msg_id)
                            if full_msg:
                                SyncService._process_message(full_msg, user, page_batch_result, sync_job=job)
                                page_emails_stored += 1
                        except Exception as e:
                            # A single email failure must NOT crash the page pipeline
                            logger.error(f"[EMAIL_INGEST_ERROR] User {user.id} msg={msg_id}: {e}")
                            continue

                # --- STEP 3 & 4: Transaction committed -> Advance cursor checkpoint ---
                now_dt = timezone.now()
                job.cursor = next_page_token
                job.page += 1
                job.pages_processed += 1
                job.emails_fetched += len(message_stubs)
                job.emails_stored += page_emails_stored
                job.emails_queued += page_emails_stored
                job.job_related_emails += page_batch_result["job_related_emails"]
                job.last_heartbeat_at = now_dt
                job.last_error = None
                job.save(update_fields=[
                    'cursor', 'page', 'pages_processed', 'emails_fetched',
                    'emails_stored', 'emails_queued', 'job_related_emails',
                    'last_heartbeat_at', 'last_error', 'updated_at'
                ])

                # Mirror progress to CustomUser model for backward-compatibility
                user.refresh_from_db()
                cumulative = user.gmail_sync_batch_stats or {}
                cumulative["emails_scanned"] = cumulative.get("emails_scanned", 0) + len(message_stubs)
                cumulative["job_related_emails"] = cumulative.get("job_related_emails", 0) + page_batch_result["job_related_emails"]
                cumulative["applications_updated"] = cumulative.get("applications_updated", 0) + page_batch_result["applications_updated"]
                cumulative["new_applications"] = cumulative.get("new_applications", 0) + page_batch_result["new_applications"]
                cumulative["needs_review"] = cumulative.get("needs_review", 0) + page_batch_result["needs_review"]
                cumulative["pages_processed"] = cumulative.get("pages_processed", 0) + 1

                user.gmail_sync_page = job.page
                user.gmail_sync_cursor = next_page_token
                user.gmail_sync_batch_stats = cumulative
                user.save(update_fields=[
                    'gmail_sync_page', 'gmail_sync_cursor', 'gmail_sync_batch_stats'
                ])

                pages_in_this_run += 1
                logger.info(
                    f"[SYNC_PAGE_COMMITTED] Job #{job.id} user {user.id} page={job.page} "
                    f"stored={page_emails_stored} fetched={len(message_stubs)} "
                    f"has_more={bool(next_page_token)}"
                )

                if not next_page_token:
                    break

            # Sync complete
            job.status = SyncJobStatus.COMPLETED
            job.completed_at = timezone.now()
            job.cursor = None
            job.save(update_fields=['status', 'completed_at', 'cursor', 'updated_at'])

            user.refresh_from_db()
            user.gmail_sync_status = 'completed'
            user.gmail_last_sync = timezone.now()
            user.gmail_sync_cursor = None
            user.save(update_fields=['gmail_sync_status', 'gmail_last_sync', 'gmail_sync_cursor'])

            SyncLog.objects.create(
                user=user,
                completed_at=timezone.now(),
                emails_scanned=job.emails_fetched,
                job_related_emails=job.job_related_emails,
                applications_updated=job.applications_updated,
                new_applications=job.new_applications,
                needs_review=job.needs_review,
            )

            logger.info(
                f"[SYNC_JOB_COMPLETED] Job #{job.id} completed successfully for user {user.id}: "
                f"pages={job.pages_processed}, fetched={job.emails_fetched}, stored={job.emails_stored}"
            )
            return {'success': True, 'job_id': job.id, 'pages': pages_in_this_run}

        except Exception as e:
            logger.error(f"[SYNC_JOB_UNEXPECTED_ERROR] Job #{job.id} error: {e}", exc_info=True)
            try:
                job.last_error = str(e)
                job.retry_count += 1
                job.status = SyncJobStatus.FAILED if job.retry_count >= job.max_retries else SyncJobStatus.PENDING
                job.last_heartbeat_at = timezone.now()
                job.save(update_fields=['status', 'last_error', 'retry_count', 'last_heartbeat_at'])
            except Exception:
                pass
            return {'success': False, 'error': str(e)}

    @classmethod
    def run_loop(
        cls,
        worker_id: str,
        poll_interval_seconds: int = 5,
        should_stop_callable: Optional[Callable[[], bool]] = None,
        max_jobs: Optional[int] = None,
    ) -> None:
        """
        Long-running producer polling loop. Runs inside the background worker process.
        Continuously claims and executes pending/stale GmailSyncJobs.
        """
        logger.info(
            f"[GMAIL_SYNC_WORKER] Starting GmailSyncCoordinator loop on worker [{worker_id}] "
            f"(poll_interval={poll_interval_seconds}s)..."
        )
        jobs_processed = 0

        while True:
            if should_stop_callable and should_stop_callable():
                logger.info(f"[GMAIL_SYNC_WORKER] Worker [{worker_id}] received stop signal. Exiting.")
                break

            try:
                job = cls.claim_next_job(worker_id=worker_id)
                if job:
                    cls.execute_sync_job(
                        job_id=job.id,
                        worker_id=worker_id,
                        should_stop_callable=should_stop_callable,
                    )
                    jobs_processed += 1
                    if max_jobs and jobs_processed >= max_jobs:
                        logger.info(f"[GMAIL_SYNC_WORKER] Worker [{worker_id}] reached max jobs ({max_jobs}).")
                        break
                else:
                    time.sleep(poll_interval_seconds)

            except Exception as e:
                logger.error(f"[GMAIL_SYNC_WORKER_ERROR] Worker [{worker_id}] unexpected loop error: {e}", exc_info=True)
                time.sleep(poll_interval_seconds)

        logger.info(f"[GMAIL_SYNC_WORKER] Worker [{worker_id}] stopped gracefully.")
