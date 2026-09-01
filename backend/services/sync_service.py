"""
Sync service for processing Gmail emails, canonical compression to R2, and tiered AI classification.
"""
import logging
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
    SyncLog
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
    """Service for syncing Gmail and processing emails incrementally in batches."""
    
    @classmethod
    def get_sync_status(cls, user):
        """Get the current sync and background processing status for a user."""
        from apps.gmail_integration.models import EmailProcessingJob, JobStatus
        from apps.applications.models import Application
        
        pending_jobs = EmailProcessingJob.objects.filter(
            user=user,
            status__in=[JobStatus.PENDING, JobStatus.RETRY]
        ).count()
        processing_jobs = EmailProcessingJob.objects.filter(
            user=user,
            status=JobStatus.PROCESSING
        ).count()
        completed_jobs = EmailProcessingJob.objects.filter(
            user=user,
            status=JobStatus.COMPLETED
        ).count()
        failed_jobs = EmailProcessingJob.objects.filter(
            user=user,
            status=JobStatus.DEAD_LETTER
        ).count()
        
        is_queue_active = (pending_jobs > 0 or processing_jobs > 0)
        app_count = Application.objects.filter(user=user).count()

        return {
            'status': user.gmail_sync_status or 'idle',
            'page': user.gmail_sync_page or 0,
            'has_more': bool(user.gmail_sync_cursor),
            'last_sync': user.gmail_last_sync,
            'stats': user.gmail_sync_batch_stats or {
                'emails_scanned': 0,
                'job_related_emails': 0,
                'applications_updated': 0,
                'new_applications': 0,
                'needs_review': 0,
                'pages_processed': 0
            },
            'queue': {
                'pending': pending_jobs,
                'processing': processing_jobs,
                'completed': completed_jobs,
                'failed': failed_jobs,
                'is_active': is_queue_active,
                'total_applications': app_count,
            }
        }

    @classmethod
    def sync_gmail_batch(cls, user, reset=False, page_size=None):
        """
        Process a single bounded page/batch of Gmail messages with resumable checkpointing.
        
        Args:
            user: CustomUser instance
            reset: If True, resets any existing sync session and starts a new cycle from page 1
            page_size: Optional page size override
            
        Returns:
            Dictionary with batch results, has_more flag, and cumulative statistics.
        """
        user.refresh_from_db()
        page_limit = page_size or getattr(settings, 'GMAIL_SYNC_PAGE_SIZE', 25)
        initial_days = getattr(settings, 'GMAIL_INITIAL_SYNC_DAYS', getattr(settings, 'GMAIL_SYNC_INITIAL_DAYS', 365))
        
        # Check active concurrency lock (avoid duplicate running syncs)
        now = timezone.now()
        is_stale_lock = user.gmail_sync_started_at and (now - user.gmail_sync_started_at > timedelta(minutes=5))
        
        if reset:
            # Explicit user request to start fresh sync cycle
            user.gmail_sync_status = 'running'
            user.gmail_sync_started_at = now
            user.gmail_sync_page = 0
            user.gmail_sync_cursor = None
            user.gmail_sync_batch_stats = {
                'emails_scanned': 0,
                'job_related_emails': 0,
                'applications_updated': 0,
                'new_applications': 0,
                'needs_review': 0,
                'pages_processed': 0
            }
            user.save(update_fields=[
                'gmail_sync_status', 'gmail_sync_started_at', 'gmail_sync_page',
                'gmail_sync_cursor', 'gmail_sync_batch_stats'
            ])
        elif user.gmail_sync_cursor:
            # Resuming from persisted checkpoint cursor after interruption / pause
            logger.info(f"Resuming sync for user {user.email} from checkpoint page {user.gmail_sync_page + 1}")
            user.gmail_sync_status = 'running'
            user.gmail_sync_started_at = now
            user.save(update_fields=['gmail_sync_status', 'gmail_sync_started_at'])
        elif user.gmail_sync_status == 'running' and not is_stale_lock:
            # Continuing actively running multi-page batch session
            logger.info(f"Sync running for user {user.email}, page {user.gmail_sync_page + 1}")
        elif user.gmail_sync_status in ('idle', 'failed') or is_stale_lock:
            # Initialize fresh sync cycle
            user.gmail_sync_status = 'running'
            user.gmail_sync_started_at = now
            user.gmail_sync_page = 0
            user.gmail_sync_cursor = None
            user.gmail_sync_batch_stats = {
                'emails_scanned': 0,
                'job_related_emails': 0,
                'applications_updated': 0,
                'new_applications': 0,
                'needs_review': 0,
                'pages_processed': 0
            }
            user.save(update_fields=[
                'gmail_sync_status', 'gmail_sync_started_at', 'gmail_sync_page',
                'gmail_sync_cursor', 'gmail_sync_batch_stats'
            ])
        else:
            # Already completed and no reset requested
            return {
                'emails_scanned': 0,
                'job_related_emails': 0,
                'applications_updated': 0,
                'new_applications': 0,
                'needs_review': 0,
                'page': user.gmail_sync_page or 1,
                'has_more': False,
                'status': 'completed',
                'cumulative': user.gmail_sync_batch_stats or {},
                'message': 'Sync already completed',
                'error': None
            }
            
        batch_result = {
            'emails_scanned': 0,
            'job_related_emails': 0,
            'applications_updated': 0,
            'new_applications': 0,
            'needs_review': 0,
            'page': user.gmail_sync_page + 1,
            'has_more': False,
            'status': 'running',
            'error': None
        }

        try:
            gmail_service = GmailService(user)
            
            # Determine sync mode: Initial (bounded historical days) vs Incremental (after last sync with lookback buffer)
            if reset or not user.gmail_last_sync:
                after_timestamp = None
            else:
                # 1-day safety buffer before last sync to ensure no timezone edge cases or delayed emails are missed
                after_timestamp = user.gmail_last_sync - timedelta(days=1)
            
            message_stubs, next_page_token = gmail_service.get_message_page(
                page_token=user.gmail_sync_cursor,
                max_results=page_limit,
                days_back=initial_days,
                after_timestamp=after_timestamp
            )
            
            batch_result['emails_scanned'] = len(message_stubs)
            batch_result['has_more'] = bool(next_page_token)
            
            if message_stubs:
                # Pre-filter deduplication: query known message IDs in one query
                stub_ids = [m['id'] for m in message_stubs if 'id' in m]
                existing_message_ids = set(
                    ProcessedEmail.objects.filter(
                        user=user,
                        gmail_message_id__in=stub_ids
                    ).values_list('gmail_message_id', flat=True)
                )
                
                # Fetch full details and ingest only new, unprocessed messages
                for stub in message_stubs:
                    msg_id = stub.get('id')
                    if not msg_id or msg_id in existing_message_ids:
                        continue
                    
                    try:
                        full_msg = gmail_service.fetch_and_parse_message(msg_id)
                        if full_msg:
                            cls._process_message(full_msg, user, batch_result)
                    except Exception as e:
                        logger.error(f"Failed to process message {msg_id}: {str(e)}")
                        continue
            


            # Update cumulative batch stats
            cumulative = user.gmail_sync_batch_stats or {}
            cumulative['emails_scanned'] = cumulative.get('emails_scanned', 0) + batch_result['emails_scanned']
            cumulative['job_related_emails'] = cumulative.get('job_related_emails', 0) + batch_result['job_related_emails']
            cumulative['applications_updated'] = cumulative.get('applications_updated', 0) + batch_result['applications_updated']
            cumulative['new_applications'] = cumulative.get('new_applications', 0) + batch_result['new_applications']
            cumulative['needs_review'] = cumulative.get('needs_review', 0) + batch_result['needs_review']
            cumulative['pages_processed'] = cumulative.get('pages_processed', 0) + 1
            
            user.gmail_sync_page += 1
            user.gmail_sync_cursor = next_page_token
            user.gmail_sync_batch_stats = cumulative
            
            if not next_page_token:
                # All pages for this sync cycle finished
                user.gmail_sync_status = 'completed'
                user.gmail_last_sync = timezone.now()
                user.gmail_sync_cursor = None
                batch_result['status'] = 'completed'
                
                # Log final sync in SyncLog
                SyncLog.objects.create(
                    user=user,
                    completed_at=timezone.now(),
                    emails_scanned=cumulative['emails_scanned'],
                    job_related_emails=cumulative['job_related_emails'],
                    applications_updated=cumulative['applications_updated'],
                    new_applications=cumulative['new_applications'],
                    needs_review=cumulative['needs_review']
                )
            
            user.save(update_fields=[
                'gmail_sync_status', 'gmail_sync_page', 'gmail_sync_cursor',
                'gmail_sync_batch_stats', 'gmail_last_sync'
            ])
            
            batch_result['cumulative'] = cumulative
            return batch_result

        except Exception as e:
            logger.error(f"Gmail batch sync failed for {user.email}: {str(e)}")
            user.gmail_sync_status = 'failed'
            user.save(update_fields=['gmail_sync_status'])
            batch_result['status'] = 'failed'
            batch_result['error'] = str(e)
            return batch_result

    @classmethod
    def sync_gmail(cls, user, max_emails=50, days_back=30):
        """Backward-compatible full sync helper."""
        return cls.sync_gmail_batch(user, reset=True, page_size=max_emails)
    
    @classmethod
    @transaction.atomic
    def _process_message(cls, message, user, result):
        """
        Process a single email message through the canonical Backblaze B2 ingestion,
        high-recall deterministic triage (P1/P2/P3), metadata storage in Neon PostgreSQL,
        and durable job queueing for worker processing.
        """
        gmail_message_id = message.get('gmail_message_id')
        if not gmail_message_id:
            return

        # Check if already processed (Idempotency)
        existing_email = ProcessedEmail.objects.filter(
            user=user,
            gmail_message_id=gmail_message_id
        ).first()

        if existing_email:
            logger.debug(f"Message {gmail_message_id} already processed")
            return

        # Step 1: Canonical Email Normalization & Lossless Compression (Strictly No Attachments)
        raw_msg_data = message.get('raw') or {}
        canonical = CanonicalEmail.from_raw_gmail_message(raw_msg_data, message)
        compressed_bytes, content_sha256, compressed_size = canonical.to_compressed_payload()

        # Retention expiration date calculation (default 90 days / 3 months)
        received_at_val = message.get('received_at') or timezone.now()
        raw_retention_expires_at = RetentionService.calculate_expiration_date(received_at_val)

        # Generate standard Object Storage Key (Backblaze B2)
        r2_key = CanonicalEmail.generate_object_key(
            user_id=user.id,
            received_dt=received_at_val,
            message_id=gmail_message_id
        )

        # Step 2: Backblaze B2 Cloud Object Storage Upload
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

        # Step 3: Fast, High-Recall Deterministic Triage (P1 / P2 / P3)
        triage_info = TriageService.triage_email(message)
        triage_priority = triage_info.get('priority', TriagePriority.P2)
        triage_score = float(triage_info.get('triage_score', 0.5))

        # Step 4: Persist metadata in Neon PostgreSQL (Strictly no full email body in DB)
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
            ai_confidence=triage_score
        )

        # Step 5: Enqueue Durable Processing Job in Neon PostgreSQL Queue
        JobScheduler.enqueue_email_job(processed_email, user, message)

        if is_job_likely:
            result['job_related_emails'] += 1
    
    @classmethod
    def get_needs_review_items(cls, user):
        """Get all items that need review for a user."""
        # Get processed emails that need review
        emails = ProcessedEmail.objects.filter(
            user=user,
            processing_status=ProcessingStatus.NEEDS_REVIEW
        ).order_by('-received_at')
        
        # Get applications that need review
        applications = Application.objects.filter(
            user=user,
            needs_review=True
        ).order_by('-updated_at')
        
        return {
            'emails': emails,
            'applications': applications
        }
