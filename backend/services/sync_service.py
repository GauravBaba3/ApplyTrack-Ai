"""
Sync service for processing Gmail emails, canonical compression to B2, and tiered AI classification.

Key design:
- start_background_sync() launches a server-side daemon thread so Gmail ingestion is
  completely independent of the browser session (survives refresh / navigation / tab close).
- _run_full_sync_loop() commits one DB transaction per Gmail page, so the durable worker
  queue receives jobs immediately — workers can process emails while Gmail keeps fetching.
- get_sync_status() returns granular pipeline counters derived from actual DB state so the
  frontend always shows authoritative numbers (correct after refresh/reconnect/multiple tabs).
"""
import logging
import time as _time
from datetime import timedelta
from django.utils import timezone
from django.db import transaction
from django.conf import settings

from apps.applications.models import Application, StatusHistory, ApplicationStatus
from apps.gmail_integration.models import (
    ProcessedEmail,
    ProcessingStatus,
    EmailEventType,
    TriagePriority,
    R2StorageStatus,
    SyncLog,
    EmailProcessingJob,
    JobStatus,
    GmailSyncJob,
    SyncJobStatus,
)
from apps.ai_processing.models import AIRequestLog

from .gmail_service import GmailService
from .email_classifier import EmailClassifier
from .groq_service import GroqService
from .application_matcher import ApplicationMatcher
from .canonical_email import CanonicalEmail
from .storage.object_storage_service import ObjectStorageService
from .storage.b2_service import B2StorageService, StorageStatus
from .storage.retention_service import RetentionService
from .queue.job_scheduler import JobScheduler
from .pipeline.classifier_pipeline import ClassifierPipeline
from .pipeline.triage_service import TriageService

logger = logging.getLogger(__name__)


class SyncService:
    """Service for syncing Gmail and processing emails via a concurrent background pipeline."""

    # ------------------------------------------------------------------
    # Public API — durable background sync management
    # ------------------------------------------------------------------

    @classmethod
    def start_background_sync(cls, user, reset: bool = False) -> dict:
        """
        Start (or report) a durable server-side background Gmail sync for this user.

        Persists a durable GmailSyncJob in Neon PostgreSQL and returns immediately.
        Execution is handled by the dedicated background worker service (applytrack-worker)
        and/or scheduled cron (applytrack-sync-gmail).
        Completely eliminates web-process daemon thread dependencies.

        Duplicate prevention & lease recovery:
        - Atomic server-side lock: only 1 active sync job per user.
        - Stale lease recovery: automatically recovers abandoned worker jobs.
        """
        from .queue.gmail_sync_coordinator import GmailSyncCoordinator
        job = GmailSyncCoordinator.request_sync(user=user, reset=reset)
        logger.info(
            f"[SYNC_DURABLE_REQUEST] User {user.id} ({user.email}) durable sync job #{job.id} "
            f"status={job.status} reset={reset}"
        )
        return cls.get_sync_status(user)

    @classmethod
    def _run_full_sync_loop(cls, user_id: int, reset: bool) -> None:
        """
        Full Gmail sync loop executed inside a background daemon thread.

        Per-page pipeline:
            Fetch Gmail page → persist emails → create jobs → COMMIT → advance cursor → next page

        Workers can claim jobs from the committed page WHILE this loop continues
        fetching the next Gmail page — this is the core concurrent producer/consumer design.

        Cursor is advanced ONLY after the commit succeeds (crash-safe checkpoint).
        """
        import django.db
        django.db.close_old_connections()

        from django.contrib.auth import get_user_model
        User = get_user_model()

        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            logger.error(f"[SYNC_THREAD_ERROR] User {user_id} not found — aborting.")
            return

        logger.info(f"[SYNC_THREAD_RUNNING] User {user_id} ({user.email}) thread is running.")

        page_limit = getattr(settings, "GMAIL_SYNC_PAGE_SIZE", 25)
        initial_days = getattr(settings, "GMAIL_INITIAL_SYNC_DAYS",
                               getattr(settings, "GMAIL_SYNC_INITIAL_DAYS", 365))
        backpressure_threshold = getattr(settings, "SYNC_BACKPRESSURE_QUEUE_SIZE", 200)
        backpressure_sleep = getattr(settings, "SYNC_BACKPRESSURE_SLEEP_SECONDS", 5)

        total_pages = 0
        total_emails_stored = 0

        try:
            gmail_service = GmailService(user)

            after_timestamp = None
            if not reset and user.gmail_last_sync:
                after_timestamp = user.gmail_last_sync - timedelta(days=1)

            while True:
                user.refresh_from_db()

                # Backpressure: pause if worker is falling behind
                pending_count = EmailProcessingJob.objects.filter(
                    user=user,
                    status__in=[JobStatus.PENDING, JobStatus.RETRY],
                ).count()
                if pending_count > backpressure_threshold:
                    logger.info(
                        f"[SYNC_BACKPRESSURE] User {user_id}: {pending_count} pending jobs. "
                        f"Pausing {backpressure_sleep}s to let worker catch up."
                    )
                    _time.sleep(backpressure_sleep)
                    django.db.close_old_connections()

                # Fetch one Gmail page
                try:
                    message_stubs, next_page_token = gmail_service.get_message_page(
                        page_token=user.gmail_sync_cursor,
                        max_results=page_limit,
                        days_back=initial_days,
                        after_timestamp=after_timestamp,
                    )
                except Exception as e:
                    logger.error(
                        f"[SYNC_PAGE_FETCH_ERROR] User {user_id} page {user.gmail_sync_page + 1}: {e}"
                    )
                    user.gmail_sync_status = "failed"
                    user.save(update_fields=["gmail_sync_status"])
                    return

                total_pages += 1
                logger.info(
                    f"[GMAIL_PAGE_FETCHED] User {user_id} page {user.gmail_sync_page + 1}: "
                    f"{len(message_stubs)} messages has_more={bool(next_page_token)}"
                )

                page_emails_stored = 0
                page_batch_result = {
                    "emails_scanned": len(message_stubs),
                    "job_related_emails": 0,
                    "applications_updated": 0,
                    "new_applications": 0,
                    "needs_review": 0,
                }

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
                                active_sync_job = GmailSyncJob.objects.filter(user=user, status__in=[SyncJobStatus.PENDING, SyncJobStatus.RUNNING]).order_by('-created_at').first()
                                cls._process_message(full_msg, user, page_batch_result, sync_job=active_sync_job)
                                page_emails_stored += 1
                        except Exception as e:
                            # One email failure must NOT stop the pipeline
                            logger.error(f"[EMAIL_PROCESS_ERROR] User {user_id} msg={msg_id}: {e}")
                            continue

                total_emails_stored += page_emails_stored

                # --- Commit per-page stats + cursor AFTER successful persist ---
                # Cursor is only advanced here, so a crash before this point means
                # we re-process this page on resume (safe due to deduplication).
                user.refresh_from_db()
                cumulative = user.gmail_sync_batch_stats or {}
                cumulative["emails_scanned"] = cumulative.get("emails_scanned", 0) + page_batch_result["emails_scanned"]
                cumulative["job_related_emails"] = cumulative.get("job_related_emails", 0) + page_batch_result["job_related_emails"]
                cumulative["applications_updated"] = cumulative.get("applications_updated", 0) + page_batch_result["applications_updated"]
                cumulative["new_applications"] = cumulative.get("new_applications", 0) + page_batch_result["new_applications"]
                cumulative["needs_review"] = cumulative.get("needs_review", 0) + page_batch_result["needs_review"]
                cumulative["pages_processed"] = cumulative.get("pages_processed", 0) + 1

                user.gmail_sync_page += 1
                user.gmail_sync_cursor = next_page_token
                user.gmail_sync_batch_stats = cumulative
                user.save(
                    update_fields=[
                        "gmail_sync_page",
                        "gmail_sync_cursor",
                        "gmail_sync_batch_stats",
                    ]
                )

                logger.info(
                    f"[SYNC_CURSOR_ADVANCED] User {user_id} page={user.gmail_sync_page} "
                    f"stored={page_emails_stored} cumulative_scanned={cumulative['emails_scanned']}"
                )

                if not next_page_token:
                    break

            # Sync complete
            user.refresh_from_db()
            cumulative = user.gmail_sync_batch_stats or {}
            user.gmail_sync_status = "completed"
            user.gmail_last_sync = timezone.now()
            user.gmail_sync_cursor = None
            user.save(update_fields=["gmail_sync_status", "gmail_last_sync", "gmail_sync_cursor"])

            SyncLog.objects.create(
                user=user,
                completed_at=timezone.now(),
                emails_scanned=cumulative.get("emails_scanned", 0),
                job_related_emails=cumulative.get("job_related_emails", 0),
                applications_updated=cumulative.get("applications_updated", 0),
                new_applications=cumulative.get("new_applications", 0),
                needs_review=cumulative.get("needs_review", 0),
            )

            logger.info(
                f"[SYNC_COMPLETED] User {user_id} ({user.email}) "
                f"pages={total_pages} emails_stored={total_emails_stored} cumulative={cumulative}"
            )

        except Exception as e:
            logger.error(
                f"[SYNC_FAILED] User {user_id} unexpected error in sync thread: {e}",
                exc_info=True,
            )
            try:
                user.refresh_from_db()
                user.gmail_sync_status = "failed"
                user.save(update_fields=["gmail_sync_status"])
            except Exception:
                pass
        finally:
            with _sync_threads_lock:
                _sync_threads.pop(user_id, None)
            try:
                import django.db
                django.db.close_old_connections()
            except Exception:
                pass

    # ------------------------------------------------------------------
    # Public API — status (authoritative DB-derived counters)
    # ------------------------------------------------------------------

    @classmethod
    def get_sync_status(cls, user) -> dict:
        """
        Return the authoritative, real-time pipeline state for this user.

        Separates:
        1. CURRENT SYNC SCOPE:
           Dedicated to the active (or latest) GmailSyncJob.
           Internal consistency guaranteed:
           processed + processing + pending <= queued <= stored <= fetched.
        2. GLOBAL MAILBOX TOTALS:
           Lifetime database totals (all emails, historical processing, applications).
        """
        user.refresh_from_db()
        now = timezone.now()

        # ------------------------------------------------------------------
        # GLOBAL / MAILBOX TOTALS (Lifetime database state across all time)
        # ------------------------------------------------------------------
        global_stored = ProcessedEmail.objects.filter(user=user).count()
        global_completed = EmailProcessingJob.objects.filter(user=user, status=JobStatus.COMPLETED).count()
        global_processing = EmailProcessingJob.objects.filter(user=user, status=JobStatus.PROCESSING).count()
        global_pending = EmailProcessingJob.objects.filter(user=user, status__in=[JobStatus.PENDING, JobStatus.RETRY]).count()
        global_failed = EmailProcessingJob.objects.filter(user=user, status=JobStatus.DEAD_LETTER).count()
        global_job_related = ProcessedEmail.objects.filter(user=user, is_job_related=True).count()
        global_app_count = Application.objects.filter(user=user).count()

        # ------------------------------------------------------------------
        # CURRENT SYNC SCOPE (Active or latest GmailSyncJob)
        # ------------------------------------------------------------------
        active_job = GmailSyncJob.objects.filter(user=user).order_by('-created_at').first()
        cumulative_stats = user.gmail_sync_batch_stats or {}

        if active_job:
            sync_fetched = active_job.emails_fetched
            sync_stored = active_job.emails_stored

            # Query email jobs specifically linked to this GmailSyncJob
            job_qs = active_job.email_jobs.all()
            sync_job_count = job_qs.count()
            sync_queued = max(active_job.emails_queued, sync_job_count)
            sync_processing = job_qs.filter(status=JobStatus.PROCESSING).count()
            sync_processed = job_qs.filter(status=JobStatus.COMPLETED).count()
            sync_pending = job_qs.filter(status__in=[JobStatus.PENDING, JobStatus.RETRY]).count()
            sync_failed = job_qs.filter(status=JobStatus.DEAD_LETTER).count()

            # Handle transition / completion where job records may have been pruned or legacy
            if sync_job_count == 0 and active_job.status == SyncJobStatus.COMPLETED:
                sync_processed = active_job.emails_stored
                sync_queued = active_job.emails_stored
                sync_pending = 0
                sync_processing = 0

            # Job-related emails detected during this sync
            detected_job_related = job_qs.filter(email__is_job_related=True).count()
            sync_job_related = max(active_job.job_related_emails, detected_job_related)

            # Applications updated or created during this sync
            linked_apps_count = job_qs.filter(email__application_id__isnull=False).values('email__application_id').distinct().count()
            sync_apps_updated = max(active_job.applications_updated, linked_apps_count)
            sync_new_apps = active_job.new_applications
            sync_needs_rev = active_job.needs_review
            page_num = active_job.page
            pages_done = active_job.pages_processed
            has_more_flag = bool(active_job.cursor) if active_job.status in (SyncJobStatus.PENDING, SyncJobStatus.RUNNING) else False
            sync_started_at = active_job.started_at
            sync_id = active_job.id
            is_sync_queue_active = sync_pending > 0 or sync_processing > 0
        else:
            sync_id = None
            sync_fetched = cumulative_stats.get("emails_scanned", 0)
            sync_stored = 0
            sync_queued = 0
            sync_processing = 0
            sync_processed = 0
            sync_pending = 0
            sync_failed = 0
            sync_job_related = cumulative_stats.get("job_related_emails", 0)
            sync_apps_updated = cumulative_stats.get("applications_updated", 0)
            sync_new_apps = cumulative_stats.get("new_applications", 0)
            sync_needs_rev = cumulative_stats.get("needs_review", 0)
            page_num = user.gmail_sync_page or 0
            pages_done = cumulative_stats.get("pages_processed", 0)
            has_more_flag = bool(user.gmail_sync_cursor)
            sync_started_at = user.gmail_sync_started_at
            is_sync_queue_active = False

        # Compute authoritative sync lifecycle status
        actual_status = user.gmail_sync_status or "idle"

        if active_job:
            if active_job.status in (SyncJobStatus.PENDING, SyncJobStatus.RUNNING):
                stale_threshold = timedelta(seconds=active_job.lease_timeout_seconds)
                is_stale_lease = (
                    active_job.status == SyncJobStatus.RUNNING
                    and active_job.last_heartbeat_at
                    and (now - active_job.last_heartbeat_at) > stale_threshold
                )
                if is_stale_lease and not is_sync_queue_active:
                    actual_status = "idle"
                else:
                    actual_status = "running"
            elif active_job.status == SyncJobStatus.COMPLETED:
                actual_status = "running" if is_sync_queue_active else "completed"
            elif active_job.status == SyncJobStatus.FAILED:
                actual_status = "running" if is_sync_queue_active else "failed"
        elif actual_status == "running" and not is_sync_queue_active:
            if user.gmail_sync_started_at and (now - user.gmail_sync_started_at) > timedelta(minutes=15):
                actual_status = "idle"

        sync_metrics = {
            "status": actual_status,
            "job_id": sync_id,
            "fetched": sync_fetched,
            "stored": sync_stored,
            "queued": sync_queued,
            "processing": sync_processing,
            "processed": sync_processed,
            "pending": sync_pending,
            "failed": sync_failed,
            "job_related": sync_job_related,
            "applications_updated": sync_apps_updated,
            "new_applications": sync_new_apps,
            "page": page_num,
            "has_more": has_more_flag,
        }

        global_totals = {
            "stored": global_stored,
            "processed": global_completed,
            "queued": global_pending + global_processing,
            "processing": global_processing,
            "pending": global_pending,
            "failed": global_failed,
            "job_related": global_job_related,
            "applications": global_app_count,
        }

        return {
            "status": actual_status,
            "page": page_num,
            "has_more": has_more_flag,
            "last_sync": user.gmail_last_sync,
            "started_at": sync_started_at,

            # Dedicated current sync vs global scopes
            "sync": sync_metrics,
            "global": global_totals,

            # Top-level counters strictly scoped to CURRENT SYNC
            "emails_fetched": sync_fetched,
            "emails_stored": sync_stored,
            "emails_queued": sync_queued,
            "emails_processing": sync_processing,
            "emails_processed": sync_processed,
            "emails_pending": sync_pending,
            "emails_failed": sync_failed,
            "job_related": sync_job_related,
            "applications_updated": sync_apps_updated,
            "new_applications": sync_new_apps,
            "total_applications": global_app_count,

            # Legacy stats dict (backward compat)
            "stats": {
                "emails_scanned": sync_fetched,
                "job_related_emails": sync_job_related,
                "applications_updated": sync_apps_updated,
                "new_applications": sync_new_apps,
                "needs_review": sync_needs_rev,
                "pages_processed": pages_done,
            },
            "queue": {
                "pending": sync_pending,
                "processing": sync_processing,
                "completed": sync_processed,
                "failed": sync_failed,
                "is_active": is_sync_queue_active,
                "total_applications": global_app_count,
            },
        }

    # ------------------------------------------------------------------
    # Backward compat — sync_gmail_batch (used by cron / legacy view)
    # ------------------------------------------------------------------

    @classmethod
    def sync_gmail_batch(cls, user, reset=False, page_size=None):
        """
        Process a SINGLE Gmail page synchronously with resumable checkpointing.

        Used by:
        - The cron management command (sync_gmail_incremental), which loops this
          until has_more=False in the absence of a background thread.
        - The legacy POST /gmail/sync/ endpoint (kept for backward compat).

        The background thread version uses _run_full_sync_loop instead, which
        commits per-page and runs continuously without blocking an HTTP request.
        """
        user.refresh_from_db()
        page_limit = page_size or getattr(settings, 'GMAIL_SYNC_PAGE_SIZE', 25)
        initial_days = getattr(settings, 'GMAIL_INITIAL_SYNC_DAYS',
                               getattr(settings, 'GMAIL_SYNC_INITIAL_DAYS', 365))

        now = timezone.now()
        is_stale_lock = user.gmail_sync_started_at and (now - user.gmail_sync_started_at > timedelta(minutes=10))

        if reset:
            user.gmail_sync_status = 'running'
            user.gmail_sync_started_at = now
            user.gmail_sync_page = 0
            user.gmail_sync_cursor = None
            user.gmail_sync_batch_stats = {
                'emails_scanned': 0, 'job_related_emails': 0,
                'applications_updated': 0, 'new_applications': 0,
                'needs_review': 0, 'pages_processed': 0
            }
            user.save(update_fields=[
                'gmail_sync_status', 'gmail_sync_started_at', 'gmail_sync_page',
                'gmail_sync_cursor', 'gmail_sync_batch_stats'
            ])
        elif user.gmail_sync_cursor:
            logger.info(f"Resuming sync for user {user.email} from checkpoint page {user.gmail_sync_page + 1}")
            user.gmail_sync_status = 'running'
            user.gmail_sync_started_at = now
            user.save(update_fields=['gmail_sync_status', 'gmail_sync_started_at'])
        elif user.gmail_sync_status == 'running' and not is_stale_lock:
            logger.info(f"Sync running for user {user.email}, page {user.gmail_sync_page + 1}")
        elif user.gmail_sync_status in ('idle', 'failed') or is_stale_lock:
            user.gmail_sync_status = 'running'
            user.gmail_sync_started_at = now
            user.gmail_sync_page = 0
            user.gmail_sync_cursor = None
            user.gmail_sync_batch_stats = {
                'emails_scanned': 0, 'job_related_emails': 0,
                'applications_updated': 0, 'new_applications': 0,
                'needs_review': 0, 'pages_processed': 0
            }
            user.save(update_fields=[
                'gmail_sync_status', 'gmail_sync_started_at', 'gmail_sync_page',
                'gmail_sync_cursor', 'gmail_sync_batch_stats'
            ])
        else:
            return {
                'emails_scanned': 0, 'job_related_emails': 0,
                'applications_updated': 0, 'new_applications': 0, 'needs_review': 0,
                'page': user.gmail_sync_page or 1, 'has_more': False,
                'status': 'completed', 'cumulative': user.gmail_sync_batch_stats or {},
                'message': 'Sync already completed', 'error': None
            }

        batch_result = {
            'emails_scanned': 0, 'job_related_emails': 0,
            'applications_updated': 0, 'new_applications': 0, 'needs_review': 0,
            'page': user.gmail_sync_page + 1, 'has_more': False,
            'status': 'running', 'error': None
        }

        try:
            gmail_service = GmailService(user)
            after_timestamp = None
            if not reset and user.gmail_last_sync:
                after_timestamp = user.gmail_last_sync - timedelta(days=1)

            message_stubs, next_page_token = gmail_service.get_message_page(
                page_token=user.gmail_sync_cursor,
                max_results=page_limit,
                days_back=initial_days,
                after_timestamp=after_timestamp,
            )

            batch_result['emails_scanned'] = len(message_stubs)
            batch_result['has_more'] = bool(next_page_token)

            if message_stubs:
                stub_ids = [m['id'] for m in message_stubs if 'id' in m]
                existing_ids = set(
                    ProcessedEmail.objects.filter(
                        user=user, gmail_message_id__in=stub_ids
                    ).values_list('gmail_message_id', flat=True)
                )
                for stub in message_stubs:
                    msg_id = stub.get('id')
                    if not msg_id or msg_id in existing_ids:
                        continue
                    try:
                        full_msg = gmail_service.fetch_and_parse_message(msg_id)
                        if full_msg:
                            active_sync_job = GmailSyncJob.objects.filter(user=user, status__in=[SyncJobStatus.PENDING, SyncJobStatus.RUNNING]).order_by('-created_at').first()
                            cls._process_message(full_msg, user, batch_result, sync_job=active_sync_job)
                    except Exception as e:
                        logger.error(f"Failed to process message {msg_id}: {str(e)}")
                        continue

            logger.info(
                f"[GMAIL_PAGE_FETCHED] User {user.id} page {user.gmail_sync_page + 1}: "
                f"{batch_result['emails_scanned']} messages has_more={batch_result['has_more']}"
            )

            # Commit per-page stats + cursor
            cumulative = user.gmail_sync_batch_stats or {}
            cumulative['emails_scanned'] = cumulative.get('emails_scanned', 0) + batch_result['emails_scanned']
            cumulative['job_related_emails'] = cumulative.get('job_related_emails', 0) + batch_result['job_related_emails']
            cumulative['applications_updated'] = cumulative.get('applications_updated', 0) + batch_result['applications_updated']
            cumulative['new_applications'] = cumulative.get('new_applications', 0) + batch_result['new_applications']
            cumulative['needs_review'] = cumulative.get('needs_review', 0) + batch_result['needs_review']
            cumulative['pages_processed'] = cumulative.get('pages_processed', 0) + 1

            user.gmail_sync_page += 1
            user.gmail_sync_cursor = next_page_token  # cursor advances only after successful persist
            user.gmail_sync_batch_stats = cumulative

            if not next_page_token:
                user.gmail_sync_status = 'completed'
                user.gmail_last_sync = timezone.now()
                user.gmail_sync_cursor = None
                batch_result['status'] = 'completed'
                SyncLog.objects.create(
                    user=user, completed_at=timezone.now(),
                    emails_scanned=cumulative['emails_scanned'],
                    job_related_emails=cumulative['job_related_emails'],
                    applications_updated=cumulative['applications_updated'],
                    new_applications=cumulative['new_applications'],
                    needs_review=cumulative['needs_review'],
                )
                logger.info(f"[SYNC_COMPLETED] User {user.id} sync complete via sync_gmail_batch.")

            user.save(update_fields=[
                'gmail_sync_status', 'gmail_sync_page', 'gmail_sync_cursor',
                'gmail_sync_batch_stats', 'gmail_last_sync'
            ])

            logger.info(
                f"[SYNC_CURSOR_ADVANCED] User {user.id} page={user.gmail_sync_page} "
                f"cumulative_scanned={cumulative['emails_scanned']}"
            )

            batch_result['cumulative'] = cumulative
            return batch_result

        except Exception as e:
            logger.error(f"[SYNC_FAILED] Gmail batch sync failed for {user.email}: {str(e)}")
            user.gmail_sync_status = 'failed'
            user.save(update_fields=['gmail_sync_status'])
            batch_result['status'] = 'failed'
            batch_result['error'] = str(e)
            return batch_result

    @classmethod
    def sync_gmail(cls, user, max_emails=50, days_back=30):
        """Backward-compatible full sync helper."""
        return cls.sync_gmail_batch(user, reset=True, page_size=max_emails)

    # ------------------------------------------------------------------
    # Internal — single-message ingestion (logic unchanged)
    # ------------------------------------------------------------------

    @classmethod
    @transaction.atomic
    def _process_message(cls, message, user, result, sync_job=None):
        """
        Process a single email message:
        1. Canonical normalisation + gzip compression
        2. Backblaze B2 upload
        3. Deterministic triage (P1/P2/P3)
        4. Persist ProcessedEmail metadata in Neon PostgreSQL
        5. Enqueue EmailProcessingJob for the durable worker

        Called from within a per-page transaction: all persistence commits together
        per page so workers can start processing after each page, not after the full sync.
        """
        gmail_message_id = message.get('gmail_message_id')
        if not gmail_message_id:
            return

        if ProcessedEmail.objects.filter(user=user, gmail_message_id=gmail_message_id).exists():
            logger.debug(f"[EMAIL_DUPLICATE] Message {gmail_message_id} already stored — skipping.")
            return

        raw_msg_data = message.get('raw') or {}
        canonical = CanonicalEmail.from_raw_gmail_message(raw_msg_data, message)
        compressed_bytes, content_sha256, compressed_size = canonical.to_compressed_payload()

        received_at_val = message.get('received_at') or timezone.now()
        raw_retention_expires_at = RetentionService.calculate_expiration_date(received_at_val)

        r2_key = CanonicalEmail.generate_object_key(
            user_id=user.id,
            received_dt=received_at_val,
            message_id=gmail_message_id,
        )

        r2_uploaded = ObjectStorageService.upload_compressed_email(
            object_key=r2_key,
            data_bytes=compressed_bytes,
            sha256_hash=content_sha256,
            metadata={
                'user_id': str(user.id),
                'gmail_message_id': str(gmail_message_id),
                'sender': str(message.get('sender', ''))[:100],
            }
        )
        r2_storage_status = StorageStatus.UPLOADED if r2_uploaded else StorageStatus.FAILED

        triage_info = TriageService.triage_email(message)
        triage_priority = triage_info.get('priority', TriagePriority.P2)
        triage_score = float(triage_info.get('triage_score', 0.5))

        is_job_likely = triage_priority in [TriagePriority.P1, TriagePriority.P2]
        processed_email = ProcessedEmail.objects.create(
            user=user,
            gmail_message_id=gmail_message_id,
            thread_id=message.get('thread_id', ''),
            r2_object_key=r2_key,
            r2_storage_status=r2_storage_status,
            r2_content_sha256=content_sha256,
            r2_compression_version=canonical.COMPRESSION_VERSION,
            compressed_size_bytes=compressed_size,
            raw_retention_expires_at=raw_retention_expires_at,
            triage_priority=triage_priority,
            sender=message.get('sender', ''),
            sender_domain=message.get('sender_domain', ''),
            subject=message.get('subject', ''),
            received_at=received_at_val,
            snippet=message.get('snippet', '')[:500],
            is_job_related=is_job_likely,
            processing_status=ProcessingStatus.DETECTED,
            ai_confidence=triage_score,
        )
        logger.debug(f"[EMAIL_PERSISTED] User {user.id} msg={gmail_message_id} priority={triage_priority}")

        JobScheduler.enqueue_email_job(processed_email, user, message, sync_job=sync_job)
        logger.debug(f"[PROCESSING_JOB_CREATED] User {user.id} msg={gmail_message_id}")

        if is_job_likely:
            result['job_related_emails'] = result.get('job_related_emails', 0) + 1

    # ------------------------------------------------------------------
    # Needs-review helper (unchanged)
    # ------------------------------------------------------------------

    @classmethod
    def get_needs_review_items(cls, user):
        """Get all items that need review for a user."""
        emails = ProcessedEmail.objects.filter(
            user=user,
            processing_status=ProcessingStatus.NEEDS_REVIEW,
        ).order_by('-received_at')
        applications = Application.objects.filter(
            user=user, needs_review=True
        ).order_by('-updated_at')
        return {'emails': emails, 'applications': applications}
