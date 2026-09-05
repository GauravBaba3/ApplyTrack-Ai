"""
Email Processing Worker for ApplyTrack AI.

Executes claimed email processing jobs:
- Fetches compressed canonical payload from Cloudflare R2
- Losslessly decompresses via CanonicalEmail
- Runs tiered AI classification pipeline (Rules -> HF -> LLM Fallbacks)
- Matches / updates Application models and status history
- Updates durable job states and handles transient retries with jitter
- Reports outcomes to LoadController for backpressure management
"""
import time
import logging
from typing import Dict, Any, List, Optional
from django.utils import timezone
from django.db import transaction, close_old_connections
from django.db.models import F

from apps.gmail_integration.models import (
    EmailProcessingJob,
    ProcessedEmail,
    ProcessingStatus,
    EmailEventType,
    JobStatus,
    TriagePriority,
    GmailSyncJob,
)
from apps.applications.models import Application, StatusHistory, ApplicationStatus
from services.canonical_email import CanonicalEmail
from services.storage.object_storage_service import ObjectStorageService
from services.storage.b2_service import B2StorageService
from services.pipeline.classifier_pipeline import ClassifierPipeline
from services.application_matcher import ApplicationMatcher
from .job_scheduler import JobScheduler
from .load_controller import LoadController

logger = logging.getLogger(__name__)


class EmailWorker:
    """
    Worker executing durable email processing jobs.
    """

    def __init__(self, worker_id: str = "worker-default"):
        self.worker_id = worker_id
        self._should_stop = False

    def stop(self) -> None:
        """Signal worker to stop after current batch completes."""
        self._should_stop = True

    def process_job(self, job: EmailProcessingJob) -> Dict[str, Any]:
        """
        Process a single claimed email processing job.
        """
        start_time = time.time()
        email = job.email
        user = job.user

        try:
            # 1. Fetch canonical email from Backblaze B2 (canonical source of full email body)
            canonical_obj: Optional[CanonicalEmail] = None
            if email.r2_object_key and ObjectStorageService.is_configured():
                compressed_bytes = ObjectStorageService.download_compressed_email(email.r2_object_key)
                if compressed_bytes:
                    try:
                        canonical_obj = CanonicalEmail.from_compressed_bytes(compressed_bytes)
                    except Exception as e:
                        logger.error(f"Error decompressing B2 payload for job {job.id}: {e}")
                        JobScheduler.retry_job(job, error_msg=f"B2 decompression corruption: {str(e)}")
                        return {'success': False, 'error': f"Decompression error: {str(e)}", 'job_id': job.id}
                else:
                    # B2 is configured in environment but object download failed (outage / network error)
                    # Do NOT fabricate full email body from Neon metadata; schedule recoverable retry with backoff.
                    logger.warning(f"Backblaze B2 object {email.r2_object_key} unreachable for job {job.id}. Scheduling retry.")
                    JobScheduler.retry_job(job, error_msg="Backblaze B2 object temporarily unavailable for download")
                    LoadController.record_job_outcome(success=False, error_type="b2_storage_unavailable")
                    return {'success': False, 'error': "Backblaze B2 payload download failed (scheduled retry)", 'job_id': job.id}

            elif canonical_obj is None:
                # Fallback only when Object Storage is unconfigured in local dev/testing environment
                canonical_obj = CanonicalEmail(
                    gmail_message_id=email.gmail_message_id,
                    thread_id=email.thread_id,
                    sender=email.sender,
                    sender_domain=email.sender_domain or '',
                    recipient='',
                    subject=email.subject,
                    received_at=email.received_at.isoformat() if email.received_at else timezone.now().isoformat(),
                    snippet=email.snippet or '',
                    plain_text_content=email.snippet or '',
                )

            # 2. Run Tiered Classification Pipeline (Rules -> HF -> Groq -> Gemini -> OpenRouter)
            email_payload = {
                'subject': canonical_obj.subject,
                'snippet': canonical_obj.snippet,
                'body': canonical_obj.plain_text_content,
                'sender': canonical_obj.sender,
                'sender_domain': canonical_obj.sender_domain,
                'thread_id': canonical_obj.thread_id,
                'gmail_message_id': canonical_obj.gmail_message_id,
                'received_at': email.received_at,
            }
            pipeline_result = ClassifierPipeline.process_email(email_payload)

            is_job = pipeline_result.get('is_job_related', False)
            confidence = float(pipeline_result.get('confidence', 0.0))
            company = pipeline_result.get('company', '')
            job_title = pipeline_result.get('job_title', '')
            detected_status_str = pipeline_result.get('status', 'Applied')
            event_type_str = pipeline_result.get('event_type', 'other')
            interview_date = pipeline_result.get('interview_date')
            needs_review = pipeline_result.get('needs_review', False)
            tier_used = pipeline_result.get('tier_used', 'rule_engine')

            # Map status choices safely
            try:
                detected_status = ApplicationStatus(detected_status_str)
            except ValueError:
                detected_status = ApplicationStatus.UNKNOWN

            try:
                event_type = EmailEventType(event_type_str)
            except ValueError:
                event_type = EmailEventType.OTHER

            parsed_interview_dt = None
            if interview_date:
                try:
                    if isinstance(interview_date, str):
                        from dateutil.parser import parse as parse_dt
                        dt = parse_dt(interview_date)
                        parsed_interview_dt = timezone.make_aware(dt) if timezone.is_naive(dt) else dt
                    elif hasattr(interview_date, 'strftime'):
                        parsed_interview_dt = timezone.make_aware(interview_date) if timezone.is_naive(interview_date) else interview_date
                except Exception:
                    parsed_interview_dt = None

            # 3. Update ProcessedEmail with AI classification results
            with transaction.atomic():
                email.is_job_related = is_job
                email.ai_confidence = confidence
                email.company = company
                email.job_title = job_title
                email.detected_status = detected_status
                email.event_type = event_type
                email.interview_date = parsed_interview_dt

                if not is_job:
                    email.processing_status = ProcessingStatus.IGNORED
                    email.save()
                    JobScheduler.complete_job(job)
                    duration = time.time() - start_time
                    LoadController.record_job_outcome(success=True, duration_seconds=duration)
                    return {'success': True, 'is_job_related': False, 'job_id': job.id}

                # Set initial processing status based on review flag
                email.processing_status = ProcessingStatus.NEEDS_REVIEW if needs_review else ProcessingStatus.PROCESSED

                # 4. Match or Create Application using Multi-Signal ApplicationMatcher
                app_match_payload = {
                    'company': company or '',
                    'job_title': job_title or '',
                    'detected_status': detected_status,
                    'status': detected_status_str,
                    'confidence': confidence,
                    'sender': email.sender,
                    'sender_domain': email.sender_domain or '',
                    'subject': email.subject,
                    'thread_id': email.thread_id,
                    'received_at': email.received_at,
                    'tier_used': tier_used,
                    'needs_review': needs_review,
                    'review_reason': pipeline_result.get('review_reason', '')
                }
                app, match_score, is_new = ApplicationMatcher.match_email_to_application(app_match_payload, user)

                if is_new and match_score >= 0.40:
                    created_app = ApplicationMatcher.create_application_from_email(app_match_payload, user)
                    email.application_id = created_app.id
                    if job.sync_job_id:
                        GmailSyncJob.objects.filter(id=job.sync_job_id).update(
                            applications_updated=F('applications_updated') + 1,
                            new_applications=F('new_applications') + 1
                        )
                elif app:
                    old_status = app.current_status
                    email.application_id = app.id

                    # Only auto-update status if match is high confidence and not flagged for review
                    if match_score >= ApplicationMatcher.AUTO_ATTACH_THRESHOLD and not needs_review:
                        if old_status != detected_status and detected_status != ApplicationStatus.UNKNOWN:
                            app.current_status = detected_status
                            app.last_email_date = email.received_at
                            app.last_activity_date = timezone.now()
                            app.confidence = max(app.confidence, confidence)
                            app.save()

                            StatusHistory.objects.create(
                                application=app,
                                previous_status=old_status,
                                new_status=detected_status,
                                source=tier_used,
                                confidence=confidence,
                                evidence=f"Matched with score {match_score:.2f}. Status updated from email: {email.subject}",
                                related_email_id=email.id
                            )
                        else:
                            app.last_activity_date = timezone.now()
                            app.save(update_fields=['last_activity_date'])

                        if job.sync_job_id:
                            GmailSyncJob.objects.filter(id=job.sync_job_id).update(
                                applications_updated=F('applications_updated') + 1
                            )
                    else:
                        # Ambiguous match or low confidence -> Flag for human review
                        email.processing_status = ProcessingStatus.NEEDS_REVIEW
                        app.needs_review = True
                        app.review_reason = f"Ambiguous match (score {match_score:.2f}) or low confidence ({confidence:.2f})"
                        app.save(update_fields=['needs_review', 'review_reason'])
                        if job.sync_job_id:
                            GmailSyncJob.objects.filter(id=job.sync_job_id).update(
                                needs_review=F('needs_review') + 1
                            )

                email.save()

                # 5. Complete or Flag Job
                job.processing_stage = tier_used
                if needs_review or email.processing_status == ProcessingStatus.NEEDS_REVIEW:
                    JobScheduler.mark_needs_review(job, reason=pipeline_result.get('review_reason', 'Ambiguous match or low confidence'))
                else:
                    JobScheduler.complete_job(job)

            duration = time.time() - start_time
            LoadController.record_job_outcome(success=True, duration_seconds=duration)
            return {'success': True, 'is_job_related': True, 'job_id': job.id, 'company': company}

        except Exception as e:
            duration = time.time() - start_time
            error_msg = str(e)
            logger.error(f"Worker {self.worker_id} failed processing job {job.id}: {error_msg}")
            LoadController.record_job_outcome(success=False, duration_seconds=duration)
            JobScheduler.retry_job(job, error_msg=error_msg)
            return {'success': False, 'job_id': job.id, 'error': error_msg}

    def process_batch(self, batch_size: Optional[int] = None) -> Dict[str, Any]:
        """
        Claim and execute a single batch of jobs across P1/P2/P3 queues.
        """
        close_old_connections()
        size = batch_size or LoadController.get_current_batch_size()
        claimed_jobs = JobScheduler.claim_batch(worker_id=self.worker_id, batch_size=size)

        if not claimed_jobs:
            return {'processed': 0, 'successful': 0, 'failed': 0, 'needs_review': 0}

        successful = 0
        failed = 0
        needs_review = 0

        for job in claimed_jobs:
            res = self.process_job(job)
            if res.get('success'):
                successful += 1
            else:
                failed += 1

        # Evaluate adaptive load after batch
        pending_count = EmailProcessingJob.objects.filter(status__in=[JobStatus.PENDING, JobStatus.RETRY]).count()
        load_state = LoadController.evaluate_and_adapt(pending_queue_size=pending_count)

        logger.info(f"Worker {self.worker_id} batch completed: {successful} success, {failed} failed out of {len(claimed_jobs)}. Adaptive concurrency: {load_state['concurrency']}, batch_size: {load_state['batch_size']}")

        return {
            'processed': len(claimed_jobs),
            'successful': successful,
            'failed': failed,
            'needs_review': needs_review,
            'load_state': load_state
        }

    def run_loop(self, poll_interval_seconds: int = 5, max_batches: Optional[int] = None) -> None:
        """
        Long-running worker polling loop.
        """
        logger.info(f"Starting EmailWorker [{self.worker_id}] loop (poll_interval={poll_interval_seconds}s, max_batches={max_batches})...")
        batches_processed = 0

        while not self._should_stop:
            try:
                close_old_connections()
                res = self.process_batch()
                if res['processed'] > 0:
                    batches_processed += 1
                    if max_batches and batches_processed >= max_batches:
                        logger.info(f"Worker [{self.worker_id}] reached max batches ({max_batches}). Exiting loop.")
                        break
                else:
                    # Queue is empty, sleep for poll interval
                    time.sleep(poll_interval_seconds)

            except Exception as e:
                logger.error(f"Worker [{self.worker_id}] loop encountered unexpected error: {str(e)}")
                time.sleep(poll_interval_seconds)

        logger.info(f"EmailWorker [{self.worker_id}] stopped gracefully.")
