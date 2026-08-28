"""
Sync service for processing Gmail emails and updating applications.
"""
import logging
from django.utils import timezone
from django.db import transaction

from apps.applications.models import Application, StatusHistory, ApplicationStatus
from apps.gmail_integration.models import ProcessedEmail, ProcessingStatus, EmailEventType
from apps.ai_processing.models import AIRequestLog

from .gmail_service import GmailService
from .email_classifier import EmailClassifier
from .groq_service import GroqService
from .application_matcher import ApplicationMatcher

logger = logging.getLogger(__name__)


from django.conf import settings
from datetime import timedelta
from apps.gmail_integration.models import SyncLog


class SyncService:
    """Service for syncing Gmail and processing emails incrementally in batches."""
    
    @classmethod
    def get_sync_status(cls, user):
        """Get the current sync status for a user."""
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
            }
        }

    @classmethod
    def sync_gmail_batch(cls, user, reset=False, page_size=None):
        """
        Process a single bounded page/batch of Gmail messages.
        
        Args:
            user: CustomUser instance
            reset: If True, resets any existing sync session and starts a new cycle
            page_size: Optional page size override
            
        Returns:
            Dictionary with batch results, has_more flag, and cumulative statistics.
        """
        user.refresh_from_db()
        page_limit = page_size or getattr(settings, 'GMAIL_SYNC_PAGE_SIZE', 25)
        initial_days = getattr(settings, 'GMAIL_SYNC_INITIAL_DAYS', 30)
        
        # Check active concurrency lock (avoid duplicate running syncs)
        now = timezone.now()
        is_stale_lock = user.gmail_sync_started_at and (now - user.gmail_sync_started_at > timedelta(minutes=5))
        
        if user.gmail_sync_status == 'running' and not reset and not is_stale_lock:
            # Continuing actively running multi-page batch session
            logger.info(f"Sync running for user {user.email}, page {user.gmail_sync_page + 1}")
        elif reset or is_stale_lock or user.gmail_sync_status in ('idle', 'failed'):
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
            
            # Determine sync mode: Initial (bounded historical days) vs Incremental (after last sync)
            after_timestamp = user.gmail_last_sync if user.gmail_last_sync else None
            
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
                
                # Fetch full details and process only new, unprocessed messages
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
        """Process a single email message."""
        gmail_message_id = message.get('gmail_message_id')
        
        # Check if already processed
        existing_email = ProcessedEmail.objects.filter(
            user=user,
            gmail_message_id=gmail_message_id
        ).first()
        
        if existing_email:
            logger.debug(f"Message {gmail_message_id} already processed")
            return
        
        # Step 1: Rule-based classification
        is_job_related, rule_confidence = EmailClassifier.is_job_related(message)
        
        company = ''
        job_title = ''
        detected_status = ApplicationStatus.UNKNOWN
        event_type = EmailEventType.OTHER
        interview_date = None
        final_confidence = rule_confidence

        # Step 2: AI classification (consult Groq for intelligent classification)
        if rule_confidence >= 0.15 or is_job_related:
            ai_result = GroqService.classify_email(message, user)
            
            # Log AI request
            AIRequestLog.objects.create(
                user=user,
                request_type='email_classification',
                tokens_used=ai_result.get('tokens', 0),
                success=ai_result.get('is_job_related') is not None
            )
            
            ai_is_job = ai_result.get('is_job_related', False)
            ai_conf = ai_result.get('confidence', 0.0)
            
            if ai_is_job:
                is_job_related = True
                final_confidence = max(rule_confidence, ai_conf)
                company = ai_result.get('company') or ''
                job_title = ai_result.get('job_title') or ''
                detected_status = ai_result.get('status') or ApplicationStatus.APPLIED
                event_type = ai_result.get('event_type') or EmailEventType.OTHER
                interview_date = ai_result.get('interview_date')
            else:
                if rule_confidence < 0.6:
                    is_job_related = False
                    final_confidence = min(rule_confidence, 0.3)
        
        final_is_job_related = is_job_related and (final_confidence >= 0.35)
        
        if not final_is_job_related:
            # Store as ignored
            ProcessedEmail.objects.create(
                user=user,
                gmail_message_id=gmail_message_id,
                thread_id=message.get('thread_id', ''),
                sender=message.get('sender', ''),
                sender_domain=message.get('sender_domain', ''),
                subject=message.get('subject', ''),
                received_at=message.get('received_at', timezone.now()),
                snippet=message.get('snippet', '')[:500],
                is_job_related=False,
                processing_status=ProcessingStatus.IGNORED,
                ai_confidence=final_confidence,
                company=company,
                job_title=job_title,
                detected_status=detected_status,
                event_type=event_type
            )
            return
        
        # Increment job-related counter
        result['job_related_emails'] += 1
        
        # Map detected status to ApplicationStatus
        if detected_status:
            try:
                detected_status = ApplicationStatus(detected_status)
            except ValueError:
                detected_status = ApplicationStatus.UNKNOWN
        else:
            detected_status = ApplicationStatus.UNKNOWN
        
        # Map event type
        if event_type:
            try:
                event_type = EmailEventType(event_type)
            except ValueError:
                event_type = EmailEventType.OTHER
        else:
            event_type = EmailEventType.OTHER
        
        # Parse interview_date safely
        parsed_interview_date = None
        if interview_date:
            try:
                if isinstance(interview_date, str):
                    from dateutil.parser import parse as parse_dt
                    dt = parse_dt(interview_date)
                    parsed_interview_date = timezone.make_aware(dt) if timezone.is_naive(dt) else dt
                elif hasattr(interview_date, 'strftime'):
                    parsed_interview_date = timezone.make_aware(interview_date) if timezone.is_naive(interview_date) else interview_date
            except Exception:
                parsed_interview_date = None

        # Create processed email record
        processed_email = ProcessedEmail.objects.create(
            user=user,
            gmail_message_id=gmail_message_id,
            thread_id=message.get('thread_id', ''),
            sender=message.get('sender', ''),
            sender_domain=message.get('sender_domain', ''),
            subject=message.get('subject', ''),
            received_at=message.get('received_at', timezone.now()),
            snippet=message.get('snippet', '')[:500],
            is_job_related=True,
            company=company or '',
            job_title=job_title or '',
            detected_status=detected_status,
            event_type=event_type,
            interview_date=parsed_interview_date,
            ai_confidence=final_confidence,
            processing_status=ProcessingStatus.DETECTED
        )
        
        # Match to existing application or create new one
        application, match_confidence, is_new = ApplicationMatcher.match_email_to_application(
            {
                'company': company or '',
                'job_title': job_title or '',
                'detected_status': detected_status,
                'confidence': final_confidence,
                'sender': message.get('sender', ''),
                'sender_domain': message.get('sender_domain', ''),
                'subject': message.get('subject', ''),
                'thread_id': message.get('thread_id', ''),
                'received_at': message.get('received_at', timezone.now())
            },
            user
        )
        
        if is_new and match_confidence >= 0.5:
            # Create new application
            try:
                application = ApplicationMatcher.create_application_from_email(
                    {
                        'company': company or '',
                        'job_title': job_title or '',
                        'detected_status': detected_status,
                        'confidence': final_confidence,
                        'received_at': message.get('received_at', timezone.now())
                    },
                    user
                )
                result['new_applications'] += 1
                
                # Link email to application
                processed_email.application_id = application.id
                processed_email.save()
                
                # Create status history
                StatusHistory.objects.create(
                    application=application,
                    previous_status=None,
                    new_status=application.current_status,
                    source='ai',
                    related_email_id=processed_email.id
                )
                
            except Exception as e:
                logger.error(f"Failed to create new application: {str(e)}")
                processed_email.processing_status = ProcessingStatus.NEEDS_REVIEW
                processed_email.save()
                result['needs_review'] += 1
        elif application:
            # Update existing application
            old_status = application.current_status
            
            # Only update if AI confidence is reasonable or it's a clear status change
            if final_confidence >= 0.6 or detected_status != ApplicationStatus.UNKNOWN:
                # Update application status
                application.current_status = detected_status
                application.last_email_date = message.get('received_at', timezone.now())
                application.last_activity_date = timezone.now()
                application.confidence = max(application.confidence, final_confidence)
                application.save()
                
                # Link email to application
                processed_email.application_id = application.id
                processed_email.save()
                
                # Create status history if status changed
                if old_status != detected_status:
                    StatusHistory.objects.create(
                        application=application,
                        previous_status=old_status,
                        new_status=detected_status,
                        source='ai',
                        related_email_id=processed_email.id
                    )
                    result['applications_updated'] += 1
            else:
                # Low confidence, mark as needs review
                processed_email.processing_status = ProcessingStatus.NEEDS_REVIEW
                processed_email.save()
                result['needs_review'] += 1
                
                # Mark application as needs review
                application.needs_review = True
                application.save()
        else:
            # No match and not a new application, mark as needs review
            processed_email.processing_status = ProcessingStatus.NEEDS_REVIEW
            processed_email.save()
            result['needs_review'] += 1
        
        # If confidence is low, mark as needs review
        if final_confidence < 0.7 and processed_email.processing_status != ProcessingStatus.NEEDS_REVIEW:
            processed_email.processing_status = ProcessingStatus.NEEDS_REVIEW
            processed_email.save()
            result['needs_review'] += 1
    
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
