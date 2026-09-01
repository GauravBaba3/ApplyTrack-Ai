"""
Comprehensive Unit Tests for Canonical Email Ingestion, R2 Storage, Retention, Triage, Queues, Workers, and Load Control.
"""
from django.test import TestCase, override_settings
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.db import IntegrityError
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

import json
from services.canonical_email import CanonicalEmail
from services.storage.r2_service import R2StorageService, R2StorageStatus
from services.storage.retention_service import RetentionService
from services.pipeline.rule_engine import RuleEngine, RuleCategory
from services.pipeline.triage_service import TriageService, TriageStatus
from services.pipeline.classifier_pipeline import ClassifierPipeline
from services.pipeline.llm_fallback_service import LLMFallbackService
from services.queue.job_scheduler import JobScheduler
from services.queue.load_controller import LoadController
from services.queue.email_worker import EmailWorker
from apps.gmail_integration.models import (
    ProcessedEmail,
    TriagePriority,
    ProcessingStatus,
    EmailProcessingJob,
    JobStatus,
    TriageStatusChoice
)
from apps.applications.models import Application, StatusHistory, ApplicationStatus

User = get_user_model()


class CanonicalEmailTests(TestCase):
    """Tests for CanonicalEmail normalization, zero-attachment enforcement, SHA-256 digests, and compression."""

    def test_canonical_email_creation_and_compression(self):
        msg = CanonicalEmail(
            gmail_message_id="msg_12345",
            thread_id="thread_999",
            sender="recruiter@techcorp.com",
            sender_domain="techcorp.com",
            recipient="applicant@gmail.com",
            subject="Interview Invitation: Senior Software Engineer",
            received_at="2026-08-31T12:00:00Z",
            labels=["INBOX", "UNREAD"],
            snippet="We would like to invite you for an interview.",
            plain_text_content="Dear candidate, We were impressed with your application and would like to schedule a technical interview.",
            safe_metadata={"message_id_header": "<abc@techcorp.com>"}
        )

        data = msg.to_dict()
        self.assertEqual(data["gmail_message_id"], "msg_12345")
        self.assertEqual(data["sender"], "recruiter@techcorp.com")
        self.assertTrue(data["attachments_omitted"])
        self.assertNotIn("attachments", data)
        self.assertNotIn("pdf", data)

        sha256 = msg.compute_sha256()
        self.assertIsInstance(sha256, str)
        self.assertEqual(len(sha256), 64)

        compressed_bytes, hash_val, size_bytes = msg.to_compressed_payload()
        self.assertIsInstance(compressed_bytes, bytes)
        self.assertTrue(size_bytes > 0)
        self.assertEqual(hash_val, sha256)

        restored = CanonicalEmail.from_compressed_bytes(compressed_bytes)
        self.assertEqual(restored.gmail_message_id, "msg_12345")
        self.assertEqual(restored.sender, "recruiter@techcorp.com")
        self.assertEqual(restored.subject, "Interview Invitation: Senior Software Engineer")
        self.assertEqual(restored.plain_text_content, msg.plain_text_content)
        self.assertEqual(restored.compute_sha256(), sha256)

    def test_generate_r2_key(self):
        dt = datetime(2026, 8, 31, 10, 0, 0)
        key = CanonicalEmail.generate_r2_key(user_id=42, received_dt=dt, message_id="gmail_msg_abc123")
        self.assertEqual(key, "users/42/emails/2026/08/gmail_msg_abc123.json.gz")

    def test_from_raw_gmail_message_strips_attachments(self):
        """Verify binary attachments (PDF, images, etc.) are explicitly stripped."""
        raw_msg = {
            "id": "raw_id_001",
            "threadId": "thread_001",
            "labelIds": ["INBOX"],
            "snippet": "Thank you for applying to Data Engineer role.",
            "payload": {
                "headers": [
                    {"name": "From", "value": "careers@bigdata.io"},
                    {"name": "To", "value": "applicant@test.com"},
                    {"name": "Subject", "value": "Application Received: Data Engineer"},
                    {"name": "Message-ID", "value": "<data123@bigdata.io>"}
                ],
                "parts": [
                    {"mimeType": "application/pdf", "filename": "resume.pdf", "body": {"attachmentId": "att_123"}},
                    {"mimeType": "image/png", "filename": "logo.png", "body": {"attachmentId": "att_456"}}
                ]
            }
        }
        parsed_info = {
            "sender": "careers@bigdata.io",
            "sender_domain": "bigdata.io",
            "subject": "Application Received: Data Engineer",
            "received_at": timezone.now(),
            "body": "Thank you for applying to Data Engineer role."
        }

        canonical = CanonicalEmail.from_raw_gmail_message(raw_msg, parsed_info)
        self.assertEqual(canonical.gmail_message_id, "raw_id_001")
        self.assertEqual(canonical.sender, "careers@bigdata.io")
        self.assertEqual(canonical.subject, "Application Received: Data Engineer")
        self.assertTrue(canonical.to_dict()["attachments_omitted"])


class NeonRelationalStorageAndRetentionTests(TestCase):
    """Tests for Neon PostgreSQL storage, retention lifecycle, duplicate prevention, and R2 operations."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser",
            email="testuser@example.com",
            password="testpassword123"
        )

    def test_duplicate_message_idempotency(self):
        """Ensure duplicate Gmail message ingestion is prevented by database unique constraints."""
        ProcessedEmail.objects.create(
            user=self.user,
            gmail_message_id="unique_msg_001",
            thread_id="thread_001",
            r2_object_key="users/1/emails/2026/08/unique_msg_001.json.gz",
            r2_storage_status=R2StorageStatus.UPLOADED,
            sender="jobs@test.com",
            subject="Job Application",
            received_at=timezone.now(),
            is_job_related=True
        )

        with self.assertRaises(IntegrityError):
            ProcessedEmail.objects.create(
                user=self.user,
                gmail_message_id="unique_msg_001",
                thread_id="thread_001",
                r2_object_key="users/1/emails/2026/08/unique_msg_001.json.gz",
                r2_storage_status=R2StorageStatus.UPLOADED,
                sender="jobs@test.com",
                subject="Duplicate Entry",
                received_at=timezone.now(),
                is_job_related=True
            )

    def test_retention_expiration_calculation(self):
        """Test calculation of raw email retention expiry (default 90 days)."""
        base_time = timezone.now()
        exp_date = RetentionService.calculate_expiration_date(base_time, retention_days=90)
        expected_diff = (exp_date - base_time).days
        self.assertEqual(expected_diff, 90)

    def test_retention_pruning_service(self):
        """Test identifying and pruning expired raw email objects from R2."""
        past_time = timezone.now() - timedelta(days=100)
        expired_email = ProcessedEmail.objects.create(
            user=self.user,
            gmail_message_id="expired_msg_001",
            thread_id="thread_002",
            r2_object_key="users/1/emails/2026/05/expired_msg_001.json.gz",
            r2_storage_status=R2StorageStatus.UPLOADED,
            sender="oldrecruiter@domain.com",
            subject="Old Application",
            received_at=past_time,
            raw_retention_expires_at=past_time + timedelta(days=90),
            is_job_related=True
        )

        fresh_time = timezone.now() - timedelta(days=10)
        fresh_email = ProcessedEmail.objects.create(
            user=self.user,
            gmail_message_id="fresh_msg_001",
            thread_id="thread_003",
            r2_object_key="users/1/emails/2026/08/fresh_msg_001.json.gz",
            r2_storage_status=R2StorageStatus.UPLOADED,
            sender="newrecruiter@domain.com",
            subject="Fresh Application",
            received_at=fresh_time,
            raw_retention_expires_at=fresh_time + timedelta(days=90),
            is_job_related=True
        )

        with patch('services.storage.r2_service.R2StorageService.delete_object', return_value=True) as mock_delete:
            res = RetentionService.prune_expired_raw_objects(dry_run=False)
            self.assertEqual(res['pruned'], 1)
            mock_delete.assert_called_once_with(expired_email.r2_object_key)

        expired_email.refresh_from_db()
        fresh_email.refresh_from_db()

        self.assertEqual(expired_email.r2_storage_status, R2StorageStatus.PRUNED)
        self.assertEqual(expired_email.subject, "Old Application")
        self.assertEqual(fresh_email.r2_storage_status, R2StorageStatus.UPLOADED)


class TriageServiceTests(TestCase):
    """Tests for P1, P2, P3 priority queue classification aligned with finalized spec."""

    def test_p1_interview_classification(self):
        email_data = {
            "subject": "Invitation to Technical Interview - Google",
            "snippet": "We would like to schedule a 45-minute Google Meet call.",
            "event_type": "interview_invitation"
        }
        res = TriageService.triage_email(email_data)
        self.assertEqual(res["priority"], "P1")
        self.assertEqual(res["triage_status"], TriageStatus.JOB_LIKELY)
        self.assertGreaterEqual(res["triage_score"], 0.85)

    def test_p1_offer_classification(self):
        email_data = {
            "subject": "Offer Letter - Stripe Software Engineer",
            "snippet": "Congratulations! We are pleased to offer you the position.",
            "event_type": "offer"
        }
        res = TriageService.triage_email(email_data)
        self.assertEqual(res["priority"], "P1")
        self.assertEqual(res["triage_status"], TriageStatus.JOB_LIKELY)

    def test_p1_rejection_classification(self):
        """Rejections require timely status updates, correctly routed to P1 per spec."""
        email_data = {
            "subject": "Update on your application with Netflix",
            "snippet": "Unfortunately, we have decided to move forward with other candidates.",
            "event_type": "rejection"
        }
        res = TriageService.triage_email(email_data)
        self.assertEqual(res["priority"], "P1")
        self.assertEqual(res["triage_status"], TriageStatus.JOB_LIKELY)

    def test_p2_coding_assessment_classification(self):
        """Technical assessments belong to P2."""
        email_data = {
            "subject": "HackerRank Coding Assessment - Uber",
            "snippet": "Please complete the 90-minute coding assessment on HackerRank within 5 days.",
            "event_type": "assessment"
        }
        res = TriageService.triage_email(email_data)
        self.assertEqual(res["priority"], "P2")
        self.assertEqual(res["triage_status"], TriageStatus.JOB_LIKELY)

    def test_p2_application_confirmation(self):
        email_data = {
            "subject": "Thank you for applying to Meta",
            "snippet": "We received your application for the Frontend Engineer position.",
            "event_type": "application_received"
        }
        res = TriageService.triage_email(email_data)
        self.assertEqual(res["priority"], "P2")
        self.assertEqual(res["triage_status"], TriageStatus.JOB_LIKELY)

    def test_p3_job_alert_and_newsletter(self):
        """Newsletters and generic job alerts belong to P3 (never discarded)."""
        email_data = {
            "subject": "LinkedIn Job Alerts: 10 new software engineer jobs",
            "snippet": "See new opportunities and recommendations matching your profile.",
            "event_type": "newsletter"
        }
        res = TriageService.triage_email(email_data)
        self.assertEqual(res["priority"], "P3")
        self.assertEqual(res["triage_status"], TriageStatus.LOW_PRIORITY)


class DurablePriorityQueueTests(TestCase):
    """Tests for durable queue jobs, weighted fair scheduling, anti-starvation aging, and thread promotion."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="queueuser",
            email="queueuser@example.com",
            password="password123"
        )

    def _create_test_email(self, msg_id, thread_id, subject, priority="P2"):
        return ProcessedEmail.objects.create(
            user=self.user,
            gmail_message_id=msg_id,
            thread_id=thread_id,
            r2_object_key=f"users/1/emails/{msg_id}.json.gz",
            r2_storage_status=R2StorageStatus.UPLOADED,
            sender="recruiter@tech.com",
            subject=subject,
            received_at=timezone.now(),
            triage_priority=priority,
            is_job_related=True
        )

    def test_durable_job_creation_and_idempotency(self):
        """Verify durable job persistence in Neon PostgreSQL and idempotency."""
        email = self._create_test_email("msg_job_001", "thread_job_001", "Interview with Meta", priority="P1")
        job = JobScheduler.enqueue_email_job(email, self.user)
        self.assertIsNotNone(job.id)
        self.assertEqual(job.priority, "P1")
        self.assertEqual(job.status, JobStatus.PENDING)

        job2 = JobScheduler.enqueue_email_job(email, self.user)
        self.assertEqual(job.id, job2.id)
        self.assertEqual(EmailProcessingJob.objects.count(), 1)

    def test_weighted_fair_scheduling_prevents_starvation(self):
        """
        Verify that a batch claim allocates slots across P1, P2, and P3,
        ensuring P2 and P3 receive guaranteed service even when P1 jobs exist.
        """
        for i in range(10):
            email = self._create_test_email(f"p1_msg_{i}", f"thread_p1_{i}", f"Interview invite {i}", priority="P1")
            JobScheduler.enqueue_email_job(email, self.user)

        for i in range(5):
            email = self._create_test_email(f"p2_msg_{i}", f"thread_p2_{i}", f"Application confirmed {i}", priority="P2")
            JobScheduler.enqueue_email_job(email, self.user)

        for i in range(5):
            email = self._create_test_email(f"p3_msg_{i}", f"thread_p3_{i}", f"Weekly newsletter {i}", priority="P3")
            JobScheduler.enqueue_email_job(email, self.user)

        claimed = JobScheduler.claim_batch(worker_id="worker-01", batch_size=10)
        self.assertEqual(len(claimed), 10)

        p1_claimed = [j for j in claimed if j.priority == "P1"]
        p2_claimed = [j for j in claimed if j.priority == "P2"]
        p3_claimed = [j for j in claimed if j.priority == "P3"]

        self.assertGreaterEqual(len(p1_claimed), 4)
        self.assertGreaterEqual(len(p2_claimed), 2)
        self.assertGreaterEqual(len(p3_claimed), 1)

        for j in claimed:
            self.assertEqual(j.status, JobStatus.PROCESSING)
            self.assertEqual(j.locked_by, "worker-01")

    def test_aging_promotes_old_p3_jobs(self):
        """Verify that P3 jobs waiting past aging threshold are promoted to P2."""
        old_time = timezone.now() - timedelta(hours=10)
        email = self._create_test_email("p3_old_msg", "thread_old", "Newsletter", priority="P3")
        job = JobScheduler.enqueue_email_job(email, self.user)

        EmailProcessingJob.objects.filter(id=job.id).update(created_at=old_time)

        promoted = JobScheduler.apply_aging_promotions(aging_hours=6)
        self.assertEqual(promoted, 1)

        job.refresh_from_db()
        self.assertEqual(job.priority, "P2")

    def test_thread_promotion_on_new_p1_message(self):
        """When a new P1 message arrives in a thread, previous P3 jobs in that thread get promoted."""
        thread_id = "thread_promoted_001"
        email_p3 = self._create_test_email("msg_step1", thread_id, "Newsletter", priority="P3")
        job_p3 = JobScheduler.enqueue_email_job(email_p3, self.user)
        self.assertEqual(job_p3.priority, "P3")

        email_p1 = self._create_test_email("msg_step2", thread_id, "Interview with Recruiter", priority="P1")
        JobScheduler.enqueue_email_job(email_p1, self.user, email_data={"subject": "Interview with Recruiter", "snippet": "schedule interview"})

        job_p3.refresh_from_db()
        self.assertEqual(job_p3.priority, "P1")

    def test_stale_lock_crash_recovery(self):
        """Verify crash-safe recovery of jobs stuck in PROCESSING past lock timeout."""
        email = self._create_test_email("crash_msg", "thread_crash", "Status update", priority="P2")
        job = JobScheduler.enqueue_email_job(email, self.user)

        past_locked = timezone.now() - timedelta(minutes=15)
        EmailProcessingJob.objects.filter(id=job.id).update(
            status=JobStatus.PROCESSING,
            locked_at=past_locked,
            locked_by="crashed-worker-99"
        )

        recovered = JobScheduler.recover_stale_locks(timeout_minutes=10)
        self.assertEqual(recovered, 1)

        job.refresh_from_db()
        self.assertEqual(job.status, JobStatus.RETRY)
        self.assertIsNone(job.locked_at)
        self.assertIsNone(job.locked_by)

    def test_job_retry_and_dead_letter_transition(self):
        """Verify retry exponential backoff and DEAD_LETTER state transition when max attempts reached."""
        email = self._create_test_email("retry_msg", "thread_retry", "Assessment", priority="P2")
        job = JobScheduler.enqueue_email_job(email, self.user)
        job.attempt_count = 1
        job.status = JobStatus.PROCESSING
        job.save()

        JobScheduler.retry_job(job, error_msg="Temporary network failure", backoff_seconds=10)
        job.refresh_from_db()
        self.assertEqual(job.status, JobStatus.RETRY)

        job.attempt_count = 3
        job.status = JobStatus.PROCESSING
        job.save()
        JobScheduler.retry_job(job, error_msg="Persistent 500 error", backoff_seconds=10)
        job.refresh_from_db()
        self.assertEqual(job.status, JobStatus.DEAD_LETTER)
        self.assertIn("Max attempts", job.last_error)


class WorkerAndLoadControllerTests(TestCase):
    """Tests for EmailWorker end-to-end execution, concurrent claim isolation, and LoadController."""

    def setUp(self):
        LoadController.reset()
        self.user = User.objects.create_user(
            username="workeruser",
            email="workeruser@example.com",
            password="password123"
        )

    def test_worker_end_to_end_job_execution(self):
        """Verify worker downloads, decompresses, runs pipeline, and creates Application."""
        email = ProcessedEmail.objects.create(
            user=self.user,
            gmail_message_id="worker_test_001",
            thread_id="thread_w1",
            r2_object_key="users/1/emails/worker_test_001.json.gz",
            r2_storage_status=R2StorageStatus.UPLOADED,
            sender="recruiting@airbnb.com",
            subject="Interview Invitation at Airbnb for Software Engineer",
            snippet="We would like to invite you for a technical interview at Airbnb.",
            received_at=timezone.now(),
            triage_priority=TriagePriority.P1,
            is_job_related=True
        )
        job = JobScheduler.enqueue_email_job(email, self.user)
        job.status = JobStatus.PROCESSING
        job.locked_by = "worker-test-01"
        job.save()

        canonical = CanonicalEmail(
            gmail_message_id="worker_test_001",
            thread_id="thread_w1",
            sender="recruiting@airbnb.com",
            sender_domain="airbnb.com",
            recipient=self.user.email,
            subject="Interview Invitation at Airbnb for Software Engineer",
            snippet="We would like to invite you for a technical interview at Airbnb.",
            plain_text_content="We would like to invite you for a technical interview at Airbnb.",
            received_at=timezone.now().isoformat()
        )
        compressed, _, _ = canonical.to_compressed_payload()

        with patch('services.storage.object_storage_service.ObjectStorageService.download_compressed_email', return_value=compressed):
            worker = EmailWorker(worker_id="worker-test-01")
            res = worker.process_job(job)

        self.assertTrue(res["success"])
        job.refresh_from_db()
        self.assertEqual(job.status, JobStatus.COMPLETED)

        # Verify application was created and linked
        email.refresh_from_db()
        self.assertIsNotNone(email.application_id)
        app = Application.objects.get(id=email.application_id)
        self.assertIn("Airbnb", app.company)

    def test_concurrent_workers_claim_disjoint_jobs(self):
        """Verify two workers claiming jobs simultaneously do not collide on the same rows."""
        # Create 10 pending jobs
        for i in range(10):
            email = ProcessedEmail.objects.create(
                user=self.user,
                gmail_message_id=f"concurrent_msg_{i}",
                thread_id=f"thread_conc_{i}",
                r2_object_key=f"users/1/emails/concurrent_{i}.json.gz",
                r2_storage_status=R2StorageStatus.UPLOADED,
                sender="jobs@tech.com",
                subject=f"Job Application {i}",
                received_at=timezone.now(),
                triage_priority=TriagePriority.P1,
                is_job_related=True
            )
            JobScheduler.enqueue_email_job(email, self.user)

        # Worker 1 claims 5 jobs
        w1_claimed = JobScheduler.claim_batch(worker_id="worker-A", batch_size=5)
        # Worker 2 claims 5 jobs
        w2_claimed = JobScheduler.claim_batch(worker_id="worker-B", batch_size=5)

        w1_ids = set(j.id for j in w1_claimed)
        w2_ids = set(j.id for j in w2_claimed)

        # Ensure no overlap
        self.assertEqual(len(w1_ids.intersection(w2_ids)), 0)
        self.assertEqual(len(w1_ids), 5)
        self.assertEqual(len(w2_ids), 5)

    def test_load_controller_adaptive_scaling_and_cooldown(self):
        """Test LoadController health evaluation, rate-limit cooldown, and step-down on error spikes."""
        self.assertEqual(LoadController.get_current_concurrency(), 1)
        self.assertEqual(LoadController.get_current_batch_size(), 25)

        # Record multiple successes
        for _ in range(15):
            LoadController.record_job_outcome(success=True)

        state = LoadController.evaluate_and_adapt(pending_queue_size=80)
        self.assertTrue(state['is_healthy'])
        self.assertEqual(state['concurrency'], 2)  # Scaled up gradually to 2

        # Simulate provider rate limit (429)
        LoadController.record_rate_limit_event(provider='groq', cooldown_seconds=30)
        self.assertTrue(LoadController.is_in_cooldown())
        self.assertEqual(LoadController.get_current_concurrency(), 1)  # Throttled back to 1


class ClassifierPipelineTests(TestCase):
    """Tests for the master classification pipeline and strict escalation gates."""

    def test_pipeline_non_job_email_early_exit(self):
        email_data = {
            "sender": "newsletter@medium.com",
            "subject": "Your daily Medium digest",
            "snippet": "Read the top stories of the day on technology and programming.",
            "body": "Here are 5 articles recommended for you today."
        }
        output = ClassifierPipeline.process_email(email_data)
        self.assertFalse(output["is_job_related"])
        self.assertFalse(output["needs_review"])

    def test_pipeline_high_confidence_rule_bypasses_hf_and_llm(self):
        """When Rule Engine achieves high confidence and extracts company, HF and LLM must NOT be called."""
        email_data = {
            "sender": "recruiting@stripe.com",
            "subject": "Interview Invitation at Stripe for Software Engineer",
            "snippet": "We would like to invite you for an interview at Stripe for the Software Engineer role.",
            "body": "Congratulations, please schedule your interview on our portal."
        }
        with patch('services.pipeline.hf_service.HFService.classify_email_zero_shot') as mock_hf, \
             patch('services.pipeline.llm_fallback_service.LLMFallbackService.classify_email') as mock_llm:
            output = ClassifierPipeline.process_email(email_data)
            self.assertTrue(output["is_job_related"])
            self.assertEqual(output["tier_used"], "rule_engine")
            mock_hf.assert_not_called()
            mock_llm.assert_not_called()

    @override_settings(GROQ_API_KEY='mock-groq-key', GEMINI_API_KEY='mock-gemini-key', OPENROUTER_API_KEY='mock-openrouter-key')
    def test_llm_fallback_chain_groq_gemini_openrouter(self):
        """Test fallback cascade when Groq fails, Gemini is attempted."""
        from services.pipeline.providers.registry import ProviderRegistry
        ProviderRegistry.reset()

        email_data = {
            "sender": "unknown@domain.com",
            "subject": "Status update",
            "snippet": "Your status has been updated",
            "body": "Please log in."
        }
        with patch('services.pipeline.providers.groq_provider.GroqProvider.classify', return_value=None), \
             patch('services.pipeline.providers.gemini_provider.GeminiProvider.classify', return_value={
                 'is_job_related': True,
                 'company': 'Acme Corp',
                 'job_title': 'Developer',
                 'status': 'Applied',
                 'event_type': 'application_status_update',
                 'confidence': 0.88,
                 'provider': 'gemini'
             }):
            res = LLMFallbackService.classify_email(email_data)
            self.assertEqual(res['provider'], 'gemini')
            self.assertEqual(res['company'], 'Acme Corp')


class RuleEngineTests(TestCase):
    """Comprehensive tests for deterministic pattern families and negative context disambiguation."""

    def test_direct_rejection_pattern_matching(self):
        email_data = {
            "sender": "no-reply@greenhouse.io",
            "subject": "Update on your application with Stripe",
            "snippet": "Thank you for your interest in Stripe. Unfortunately, we are not moving forward with your application.",
            "body": "We received many qualified applicants and have decided to proceed with other candidates whose experience aligns more closely."
        }
        res = RuleEngine.evaluate(email_data)
        self.assertTrue(res['is_job_related'])
        self.assertEqual(res['category'], RuleCategory.REJECTION.value)
        self.assertEqual(res['status'], 'Rejected')
        self.assertEqual(res['event_type'], 'rejection')
        self.assertGreaterEqual(res['evidence_score'], 70)
        self.assertTrue(res['is_deterministic_final'])

    def test_indirect_rejection_pattern_matching(self):
        email_data = {
            "sender": "careers@netflix.com",
            "subject": "Status of your application for Software Engineer",
            "snippet": "After careful consideration, we have chosen another candidate for this role.",
            "body": "The position has now been filled. We will keep your resume on file for future openings."
        }
        res = RuleEngine.evaluate(email_data)
        self.assertTrue(res['is_job_related'])
        self.assertEqual(res['category'], RuleCategory.REJECTION.value)
        self.assertEqual(res['status'], 'Rejected')
        self.assertGreaterEqual(res['evidence_score'], 70)

    def test_interview_invitation_pattern_matching(self):
        email_data = {
            "sender": "recruiting@uber.com",
            "subject": "Interview Invitation: Uber Software Engineer",
            "snippet": "We would like to invite you for a 45-minute technical interview with our team.",
            "body": "Please select a time on our calendar using the scheduling link below."
        }
        res = RuleEngine.evaluate(email_data)
        self.assertTrue(res['is_job_related'])
        self.assertEqual(res['category'], RuleCategory.INTERVIEW.value)
        self.assertEqual(res['status'], 'Interview')
        self.assertEqual(res['event_type'], 'interview_invitation')
        self.assertGreaterEqual(res['evidence_score'], 70)
        self.assertTrue(res['is_deterministic_final'])

    def test_technical_assessment_pattern_matching(self):
        email_data = {
            "sender": "talent@bloomberg.com",
            "subject": "Bloomberg Online Technical Assessment - HackerRank",
            "snippet": "Please complete the 90-minute coding assessment on HackerRank within 5 days.",
            "body": "Follow the assessment link below to begin your coding test."
        }
        res = RuleEngine.evaluate(email_data)
        self.assertTrue(res['is_job_related'])
        self.assertEqual(res['category'], RuleCategory.ASSESSMENT.value)
        self.assertEqual(res['status'], 'Assessment')
        self.assertEqual(res['event_type'], 'coding_assessment')
        self.assertGreaterEqual(res['evidence_score'], 70)

    def test_offer_letter_pattern_matching(self):
        email_data = {
            "sender": "hr@apple.com",
            "subject": "Offer of Employment - Apple",
            "snippet": "We are pleased to offer you the position of Senior Software Engineer at Apple.",
            "body": "Attached is your formal offer letter detailing compensation, base salary, and benefits."
        }
        res = RuleEngine.evaluate(email_data)
        self.assertTrue(res['is_job_related'])
        self.assertEqual(res['category'], RuleCategory.OFFER.value)
        self.assertEqual(res['status'], 'Offer')
        self.assertEqual(res['event_type'], 'offer')
        self.assertGreaterEqual(res['evidence_score'], 70)
        self.assertTrue(res['is_deterministic_final'])

    def test_application_received_pattern_matching(self):
        email_data = {
            "sender": "jobs@meta.com",
            "subject": "Thank you for applying to Meta",
            "snippet": "We have received your application for the Frontend Engineer position.",
            "body": "Our recruiting team is currently reviewing your application."
        }
        res = RuleEngine.evaluate(email_data)
        self.assertTrue(res['is_job_related'])
        self.assertEqual(res['category'], RuleCategory.APPLICATION_RECEIVED.value)
        self.assertEqual(res['status'], 'Applied')
        self.assertGreaterEqual(res['evidence_score'], 70)

    def test_negative_context_interview_negation(self):
        """'We do not require an interview at this stage' must NOT be classified as an Interview invitation."""
        email_data = {
            "sender": "info@contractor.com",
            "subject": "Application update",
            "snippet": "We do not require an interview at this stage of the evaluation.",
            "body": "Your portfolio is currently being reviewed."
        }
        res = RuleEngine.evaluate(email_data)
        self.assertNotEqual(res['category'], RuleCategory.INTERVIEW.value)

    def test_negative_context_interview_tips_newsletter(self):
        """'Tips for interviewing' advice article must NOT be classified as an Interview invitation."""
        email_data = {
            "sender": "newsletter@careeradvice.com",
            "subject": "Top 10 Tips for Interviewing in Tech",
            "snippet": "Here is our weekly guide on how to prepare for your interview.",
            "body": "Read expert interview tips to ace your next technical screen."
        }
        res = RuleEngine.evaluate(email_data)
        self.assertNotEqual(res['category'], RuleCategory.INTERVIEW.value)
        self.assertFalse(res['is_deterministic_final'])

    def test_negative_context_promotional_offer(self):
        """Promotional marketing discount offers must NOT trigger job offer classification."""
        email_data = {
            "sender": "deals@udemy.com",
            "subject": "Special offer: 80% off all coding bootcamps",
            "snippet": "Limited time offer on python and web development courses.",
            "body": "Claim your discount offer today before it expires."
        }
        res = RuleEngine.evaluate(email_data)
        self.assertNotEqual(res['category'], RuleCategory.OFFER.value)

    def test_withdrawal_pattern_matching(self):
        email_data = {
            "sender": "recruiting@spotify.com",
            "subject": "Confirmation: Application Withdrawn",
            "snippet": "As requested, we have confirmed the withdrawal of your application for Software Engineer.",
            "body": "Your candidacy is no longer under consideration per your request."
        }
        res = RuleEngine.evaluate(email_data)
        self.assertTrue(res['is_job_related'])
        self.assertEqual(res['category'], RuleCategory.WITHDRAWAL.value)


class MultiLayerIntelligencePipelineTests(TestCase):
    """Tests for Phase 5: Multi-layer Intelligence Pipeline, Provider Abstraction, and Fallback Cascade."""

    def setUp(self):
        from services.pipeline.providers.registry import ProviderRegistry
        ProviderRegistry.reset()

    def test_provider_registry_initialization_and_order(self):
        from services.pipeline.providers.registry import ProviderRegistry
        ProviderRegistry.initialize()
        groq = ProviderRegistry.get_provider('groq')
        gemini = ProviderRegistry.get_provider('gemini')
        openrouter = ProviderRegistry.get_provider('openrouter')
        hf = ProviderRegistry.get_provider('huggingface')

        self.assertIsNotNone(groq)
        self.assertIsNotNone(gemini)
        self.assertIsNotNone(openrouter)
        self.assertIsNotNone(hf)
        self.assertEqual(groq.name, 'groq')

    def test_structured_llm_output_normalization_and_validation(self):
        """Verify that BaseClassifierProvider properly validates and normalizes raw dictionary payloads."""
        from services.pipeline.providers.groq_provider import GroqProvider
        provider = GroqProvider()

        raw_json_str = """
        ```json
        {
            "is_job_related": true,
            "company": "Figma",
            "job_title": "Product Designer",
            "status": "interviewing",
            "event_type": "interview_invitation",
            "interview_date": "2026-09-05T14:00:00Z",
            "confidence": 0.95,
            "reasoning": "Interview schedule requested"
        }
        ```
        """
        parsed = provider.parse_json_safely(raw_json_str)
        self.assertIsNotNone(parsed)
        self.assertTrue(parsed['is_job_related'])
        self.assertEqual(parsed['company'], 'Figma')
        self.assertEqual(parsed['status'], 'Interview')  # Normalized from 'interviewing'
        self.assertEqual(parsed['confidence'], 0.95)
        self.assertEqual(parsed['provider'], 'groq')

    @override_settings(GROQ_API_KEY='mock-groq-key', GEMINI_API_KEY='mock-gemini-key')
    def test_multi_layer_escalation_rule_to_hf_to_groq(self):
        """When Rule Engine and HF are uncertain, Groq is invoked and produces high confidence."""
        email_data = {
            "sender": "talent@stealthstartup.io",
            "subject": "Quick chat next week?",
            "snippet": "We saw your GitHub profile and would love to discuss a role.",
            "body": "Let me know your availability for a 20-minute chat."
        }

        mock_groq_response = {
            'is_job_related': True,
            'company': 'Stealth Startup',
            'job_title': 'Software Engineer',
            'status': 'Interview',
            'event_type': 'interview_invitation',
            'interview_date': None,
            'confidence': 0.90,
            'reasoning': 'Recruiter reached out for initial chat'
        }

        with patch('services.pipeline.hf_service.HFService.classify_email_zero_shot', return_value={'top_label': 'job interview invitation', 'score': 0.60}), \
             patch('services.pipeline.providers.groq_provider.GroqProvider.classify', return_value=mock_groq_response):
            output = ClassifierPipeline.process_email(email_data)
            self.assertTrue(output['is_job_related'])
            self.assertEqual(output['company'], 'Stealth Startup')
            self.assertEqual(output['status'], 'Interview')
            self.assertEqual(output['tier_used'], 'llm_groq')
            self.assertFalse(output['needs_review'])

    def test_all_ai_providers_unavailable_routes_safely_to_human_review(self):
        """If all AI providers are unconfigured/unavailable, system MUST route to Human Review without crashing."""
        email_data = {
            "sender": "recruiter@obscuredomain.xyz",
            "subject": "Interview update regarding your application",
            "snippet": "We have an update regarding your candidacy.",
            "body": "Please log in to your candidate portal."
        }

        with patch('services.pipeline.hf_service.HFService.classify_email_zero_shot', return_value=None), \
             patch('services.pipeline.providers.registry.ProviderRegistry.get_configured_llm_chain', return_value=[]):
            output = ClassifierPipeline.process_email(email_data)
            self.assertTrue(output['needs_review'])
            self.assertIn('review_reason', output)

    def test_status_safety_conservative_destructive_protection(self):
        """A low-confidence rejection status (<0.85) from an uncertain LLM must be flagged for Human Review."""
        email_data = {
            "sender": "no-reply@ats-system.com",
            "subject": "Notification",
            "snippet": "Your status was updated",
            "body": "Check status."
        }

        mock_uncertain_rejection = {
            'is_job_related': True,
            'company': 'Unknown Company',
            'job_title': '',
            'status': 'Rejected',
            'event_type': 'rejection',
            'interview_date': None,
            'confidence': 0.72,
            'reasoning': 'Possible rejection based on portal phrasing'
        }

        with patch('services.pipeline.hf_service.HFService.classify_email_zero_shot', return_value=None), \
             patch('services.pipeline.llm_fallback_service.LLMFallbackService.classify_email', return_value=mock_uncertain_rejection):
            output = ClassifierPipeline.process_email(email_data)
            self.assertTrue(output['needs_review'])
            self.assertIn('Conservative protection', output.get('review_reason', ''))


class RateLimitingAndQuotaManagementTests(TestCase):
    """Comprehensive tests for Phase 6: Rate Limiting, Quota Management, Circuit Breaker, and Failover."""

    def setUp(self):
        from services.pipeline.rate_limiter import ProviderRateLimiter
        from services.pipeline.circuit_breaker import CircuitBreaker
        from services.pipeline.providers.registry import ProviderRegistry
        ProviderRateLimiter.reset()
        CircuitBreaker.reset()
        ProviderRegistry.reset()

    def test_rate_limiter_rpm_and_rpd_enforcement(self):
        from services.pipeline.rate_limiter import ProviderRateLimiter, ProviderQuota
        # Custom tight quota for testing
        ProviderRateLimiter.DEFAULT_QUOTAS['test_provider'] = ProviderQuota(max_rpm=3, max_rpd=10)

        # 3 requests allowed
        for _ in range(3):
            allowed, _ = ProviderRateLimiter.can_acquire('test_provider')
            self.assertTrue(allowed)
            ProviderRateLimiter.acquire('test_provider')
            ProviderRateLimiter.release('test_provider')

        # 4th request must be rejected by RPM limit
        allowed, reason = ProviderRateLimiter.can_acquire('test_provider')
        self.assertFalse(allowed)
        self.assertIn("exceeded RPM limit", reason)

    def test_rate_limiter_tpm_enforcement(self):
        from services.pipeline.rate_limiter import ProviderRateLimiter, ProviderQuota
        ProviderRateLimiter.DEFAULT_QUOTAS['token_test'] = ProviderQuota(max_rpm=100, max_tpm=500)

        # Acquire 400 tokens
        allowed, _ = ProviderRateLimiter.can_acquire('token_test', estimated_tokens=400)
        self.assertTrue(allowed)
        ProviderRateLimiter.acquire('token_test', estimated_tokens=400)
        ProviderRateLimiter.release('token_test')

        # Requesting another 200 tokens (400 + 200 = 600 > 500 TPM) must be rejected
        allowed, reason = ProviderRateLimiter.can_acquire('token_test', estimated_tokens=200)
        self.assertFalse(allowed)
        self.assertIn("exceeded TPM limit", reason)

    def test_rate_limiter_in_flight_concurrency_control(self):
        from services.pipeline.rate_limiter import ProviderRateLimiter, ProviderQuota
        ProviderRateLimiter.DEFAULT_QUOTAS['concurrency_test'] = ProviderQuota(max_concurrent_requests=1)

        # Worker 1 acquires slot
        allowed, _ = ProviderRateLimiter.can_acquire('concurrency_test')
        self.assertTrue(allowed)
        ProviderRateLimiter.acquire('concurrency_test')

        # Worker 2 attempts concurrent acquire -> Rejected
        allowed, reason = ProviderRateLimiter.can_acquire('concurrency_test')
        self.assertFalse(allowed)
        self.assertIn("at max in-flight concurrency", reason)

        # Worker 1 finishes and releases slot
        ProviderRateLimiter.release('concurrency_test')

        # Worker 2 can now acquire
        allowed, _ = ProviderRateLimiter.can_acquire('concurrency_test')
        self.assertTrue(allowed)

    def test_rate_limiter_dynamic_retry_after_header_handling(self):
        from services.pipeline.rate_limiter import ProviderRateLimiter
        import time

        # Simulate 429 response with Retry-After: 2
        ProviderRateLimiter.update_from_headers('groq', {'Retry-After': '2'})

        allowed, reason = ProviderRateLimiter.can_acquire('groq')
        self.assertFalse(allowed)
        self.assertIn("Retry-After header cooldown active", reason)

        time.sleep(2.1)
        allowed, _ = ProviderRateLimiter.can_acquire('groq')
        self.assertTrue(allowed)

    def test_circuit_breaker_state_transitions(self):
        from services.pipeline.circuit_breaker import CircuitBreaker, CircuitState
        import time

        provider = "gemini_cb"
        self.assertEqual(CircuitBreaker.get_state(provider), CircuitState.CLOSED)
        self.assertTrue(CircuitBreaker.is_allowed(provider))

        # 3 consecutive failures open circuit
        CircuitBreaker.record_failure(provider, "500 Internal Error 1")
        CircuitBreaker.record_failure(provider, "500 Internal Error 2")
        self.assertEqual(CircuitBreaker.get_state(provider), CircuitState.CLOSED)

        CircuitBreaker.record_failure(provider, "500 Internal Error 3")
        self.assertEqual(CircuitBreaker.get_state(provider), CircuitState.OPEN)
        self.assertFalse(CircuitBreaker.is_allowed(provider))

        # Fast forward cooldown
        CircuitBreaker._circuits[provider]['cooldown_until'] = time.time() - 1

        # Check transition to HALF_OPEN probation
        self.assertEqual(CircuitBreaker.get_state(provider), CircuitState.HALF_OPEN)
        self.assertTrue(CircuitBreaker.is_allowed(provider))

        # Successful probe resets circuit to CLOSED
        CircuitBreaker.record_success(provider)
        self.assertEqual(CircuitBreaker.get_state(provider), CircuitState.CLOSED)
        self.assertEqual(CircuitBreaker._circuits[provider]['failures'], 0)

    def test_provider_manager_usage_logging_in_neon(self):
        from services.pipeline.provider_manager import ProviderManager
        from apps.gmail_integration.models import ProviderUsageLog
        from services.pipeline.providers.groq_provider import GroqProvider

        initial_count = ProviderUsageLog.objects.count()
        provider = GroqProvider()

        mock_result = {
            'is_job_related': True,
            'company': 'Netflix',
            'job_title': 'Senior Engineer',
            'status': 'Interview',
            'event_type': 'interview_invitation',
            'interview_date': None,
            'confidence': 0.95
        }

        with patch.object(provider, 'classify', return_value=mock_result):
            res = ProviderManager.execute_call(provider, {"subject": "Netflix Interview", "body": "Interview details"})
            self.assertIsNotNone(res)
            self.assertTrue(res['is_job_related'])

        # Verify usage log created in Neon DB
        self.assertEqual(ProviderUsageLog.objects.count(), initial_count + 1)
        log = ProviderUsageLog.objects.latest('created_at')
        self.assertEqual(log.provider, 'groq')
        self.assertTrue(log.success)
        self.assertEqual(log.status_code, 200)
        self.assertGreater(log.total_tokens, 0)


class JobApplicationIntelligenceAndUXTests(TestCase):
    """Tests for Phase 7: Application Matching, Status Transitions, Staleness, Review Queue, and Manual Fallback."""

    def setUp(self):
        User = get_user_model()
        self.user, _ = User.objects.get_or_create(
            username="p7_tester",
            defaults={"email": "p7_tester@test.com"}
        )
        self.client.force_login(self.user)

    def test_application_matcher_multi_signal_high_confidence_auto_attach(self):
        from services.application_matcher import ApplicationMatcher
        app = Application.objects.create(
            user=self.user,
            company="Canva",
            job_title="Frontend Engineer",
            application_date=timezone.now().date(),
            current_status=ApplicationStatus.APPLIED
        )

        email_data = {
            "company": "Canva",
            "job_title": "Frontend Engineer",
            "sender_domain": "canva.com",
            "subject": "Interview Invitation: Frontend Engineer at Canva",
            "thread_id": "canva_th_001"
        }

        matched_app, score, is_new = ApplicationMatcher.match_email_to_application(email_data, self.user)
        self.assertEqual(matched_app.id, app.id)
        self.assertGreaterEqual(score, 0.75)
        self.assertFalse(is_new)

    def test_application_matcher_ambiguous_low_confidence_routes_to_review(self):
        from services.application_matcher import ApplicationMatcher
        app = Application.objects.create(
            user=self.user,
            company="Meta Platforms",
            job_title="Security Engineer",
            application_date=timezone.now().date(),
            current_status=ApplicationStatus.APPLIED
        )

        # Ambiguous email: matching company & subject, but ambiguous title & no thread match
        email_data = {
            "company": "Meta Platforms",
            "job_title": "Lead Security Consultant",
            "sender_domain": "external-recruiter.com",
            "subject": "Meta Platforms Application Update",
            "thread_id": "diff_thread_999"
        }

        matched_app, score, is_new = ApplicationMatcher.match_email_to_application(email_data, self.user)
        # Should match candidate app, but score is below auto-attach threshold (< 0.75)
        self.assertIsNotNone(matched_app)
        self.assertEqual(matched_app.id, app.id)
        self.assertLess(score, 0.75)
        self.assertGreaterEqual(score, 0.40)

    def test_application_status_history_recording(self):
        app = Application.objects.create(
            user=self.user,
            company="Linear",
            job_title="Product Designer",
            application_date=timezone.now().date(),
            current_status=ApplicationStatus.APPLIED
        )

        # Transition status to Interview
        app.current_status = ApplicationStatus.INTERVIEW
        app.save()

        StatusHistory.objects.create(
            application=app,
            previous_status=ApplicationStatus.APPLIED,
            new_status=ApplicationStatus.INTERVIEW,
            source='email_worker',
            confidence=0.95,
            evidence="Interview scheduling invitation received"
        )

        history = app.status_history.first()
        self.assertIsNotNone(history)
        self.assertEqual(history.previous_status, ApplicationStatus.APPLIED)
        self.assertEqual(history.new_status, ApplicationStatus.INTERVIEW)
        self.assertEqual(history.confidence, 0.95)

    def test_staleness_and_ghosting_detection(self):
        from services.staleness_service import StalenessService
        # Application from 35 days ago with no activity
        old_date = timezone.now().date() - timedelta(days=35)
        app = Application.objects.create(
            user=self.user,
            company="StaleCo",
            job_title="DevOps",
            application_date=old_date,
            current_status=ApplicationStatus.APPLIED,
            last_activity_date=timezone.now() - timedelta(days=35)
        )

        result = StalenessService.audit_user_applications_for_staleness(self.user)
        app.refresh_from_db()

        self.assertEqual(result['ghosted_count'], 1)
        self.assertEqual(app.current_status, ApplicationStatus.GHOSTED)
        self.assertEqual(app.follow_ups.count(), 1)
        follow_up = app.follow_ups.first()
        self.assertFalse(follow_up.is_sent)  # Never automatically sent

    def test_needs_review_confirm_and_edit_endpoints(self):
        app = Application.objects.create(
            user=self.user,
            company="ReviewCo",
            job_title="Fullstack",
            application_date=timezone.now().date(),
            current_status=ApplicationStatus.INTERVIEW,
            needs_review=True,
            review_reason="Ambiguous match (score 0.55)"
        )

        # Test confirm review endpoint
        resp = self.client.post(f"/api/applications/{app.id}/confirm-review/")
        self.assertEqual(resp.status_code, 200)
        app.refresh_from_db()
        self.assertFalse(app.needs_review)

        # Flag again and test edit review endpoint
        app.needs_review = True
        app.save()

        edit_resp = self.client.post(
            f"/api/applications/{app.id}/edit-review/",
            data={"company": "ReviewCo Inc", "job_title": "Lead Fullstack", "status": "Offer"},
            content_type="application/json"
        )
        self.assertEqual(edit_resp.status_code, 200)
        app.refresh_from_db()
        self.assertEqual(app.company, "ReviewCo Inc")
        self.assertEqual(app.current_status, ApplicationStatus.OFFER)
        self.assertFalse(app.needs_review)

    def test_sync_summary_endpoint(self):
        resp = self.client.get("/api/applications/sync-summary/")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn('emails_scanned', data)
        self.assertIn('job_related', data)
        self.assertIn('applications_updated', data)
        self.assertIn('new_applications', data)
        self.assertIn('needs_review', data)
        self.assertIn('failed_processing', data)


class BackblazeB2StorageTests(TestCase):
    """
    Tests for Backblaze B2 Object Storage integration, key conventions,
    gzip compression roundtrip, SHA-256 integrity verification, zero attachments,
    retention pruning, and worker download retry behavior.
    """

    def setUp(self):
        self.user = User.objects.create_user(
            username="b2_testuser",
            email="b2_testuser@example.com",
            password="testpassword123"
        )
        from services.storage.b2_service import B2StorageService
        B2StorageService.reset_client()

    def test_b2_object_key_generation(self):
        """Verify standard Backblaze B2 object key convention."""
        dt = datetime(2026, 8, 31, 12, 0, 0)
        key = CanonicalEmail.generate_object_key(
            user_id=42,
            received_dt=dt,
            message_id="msg_b2_001"
        )
        self.assertEqual(key, "users/42/emails/2026/08/msg_b2_001.json.gz")
        # Verify alias matches
        self.assertEqual(CanonicalEmail.generate_b2_key(42, dt, "msg_b2_001"), key)

    def test_b2_gzip_compression_and_sha256_roundtrip(self):
        """Verify gzip compression, SHA-256 computation, and lossless decompression."""
        canonical = CanonicalEmail(
            gmail_message_id="msg_roundtrip_01",
            thread_id="th_roundtrip_01",
            sender="recruiter@b2corp.com",
            sender_domain="b2corp.com",
            recipient=self.user.email,
            subject="Technical Assessment Invitation - B2 Corp",
            received_at=timezone.now().isoformat(),
            snippet="Please complete your coding challenge.",
            plain_text_content="Here is the link to your technical assessment for Software Engineer."
        )

        compressed_bytes, sha256_hash, compressed_size = canonical.to_compressed_payload()
        self.assertIsInstance(compressed_bytes, bytes)
        self.assertGreater(len(compressed_bytes), 0)
        self.assertEqual(len(sha256_hash), 64)  # SHA-256 hex string

        # Decompress and verify identity
        reconstructed = CanonicalEmail.from_compressed_bytes(compressed_bytes)
        self.assertEqual(reconstructed.gmail_message_id, canonical.gmail_message_id)
        self.assertEqual(reconstructed.subject, canonical.subject)
        self.assertEqual(reconstructed.plain_text_content, canonical.plain_text_content)
        self.assertEqual(reconstructed.compute_sha256(), sha256_hash)

    def test_b2_upload_and_download_mocked(self):
        """Verify B2 upload and download through S3-compatible boto3 API."""
        from services.storage.b2_service import B2StorageService
        mock_s3 = MagicMock()
        mock_body = MagicMock()
        mock_body.read.return_value = b"mock_compressed_gzip_data"
        mock_s3.get_object.return_value = {'Body': mock_body}

        with patch.object(B2StorageService, 'get_client', return_value=mock_s3):
            # Upload
            uploaded = B2StorageService.upload_compressed_email(
                object_key="users/1/emails/2026/08/msg_test.json.gz",
                data_bytes=b"mock_compressed_gzip_data",
                sha256_hash="abcdef123456",
                metadata={'user_id': '1'}
            )
            self.assertTrue(uploaded)
            mock_s3.put_object.assert_called_once()

            # Download
            downloaded = B2StorageService.download_compressed_email("users/1/emails/2026/08/msg_test.json.gz")
            self.assertEqual(downloaded, b"mock_compressed_gzip_data")

            # Delete
            deleted = B2StorageService.delete_object("users/1/emails/2026/08/msg_test.json.gz")
            self.assertTrue(deleted)
            mock_s3.delete_object.assert_called_once()

    def test_b2_unconfigured_dev_fallback(self):
        """Verify graceful dev mode when B2 credentials are unset."""
        from services.storage.b2_service import B2StorageService
        with patch.object(B2StorageService, 'get_client', return_value=None):
            self.assertFalse(B2StorageService.is_configured())
            uploaded = B2StorageService.upload_compressed_email("test_key", b"test_bytes")
            self.assertTrue(uploaded)  # Dev fallback succeeds
            downloaded = B2StorageService.download_compressed_email("test_key")
            self.assertIsNone(downloaded)

    def test_b2_worker_download_failure_schedules_retry(self):
        """Verify worker schedules RETRY with backoff when B2 download fails during processing."""
        from services.storage.b2_service import B2StorageService
        from services.storage.object_storage_service import ObjectStorageService
        pe = ProcessedEmail.objects.create(
            user=self.user,
            gmail_message_id="msg_b2_retry_01",
            thread_id="th_b2_retry_01",
            subject="Job Update",
            received_at=timezone.now(),
            r2_object_key="users/1/emails/2026/08/msg_b2_retry_01.json.gz",
            r2_storage_status='uploaded',
            triage_priority=TriagePriority.P1
        )
        job = EmailProcessingJob.objects.create(
            user=self.user,
            email=pe,
            gmail_message_id="msg_b2_retry_01",
            thread_id="th_b2_retry_01",
            priority=TriagePriority.P1,
            status=JobStatus.PROCESSING
        )

        with patch.object(ObjectStorageService, 'is_configured', return_value=True), \
             patch.object(ObjectStorageService, 'download_compressed_email', return_value=None):
            worker = EmailWorker(worker_id="b2_worker_01")
            res = worker.process_job(job)
            self.assertFalse(res['success'])
            job.refresh_from_db()
            self.assertEqual(job.status, JobStatus.RETRY)
            self.assertIn("Backblaze B2", job.last_error)

    def test_b2_zero_attachments_enforced(self):
        """Verify all attachment types (PDF, DOCX, images, ZIP) are stripped from B2 payload."""
        raw_msg = {
            "id": "msg_att_b2",
            "threadId": "th_att_b2",
            "labelIds": ["INBOX"],
            "snippet": "Attached is the job description and assessment form.",
            "payload": {
                "headers": [
                    {"name": "From", "value": "recruiter@enterprise.com"},
                    {"name": "To", "value": self.user.email},
                    {"name": "Subject", "value": "Job Offer - Staff Engineer"}
                ],
                "parts": [
                    {"mimeType": "application/pdf", "filename": "OfferLetter.pdf", "body": {"attachmentId": "att_pdf"}},
                    {"mimeType": "application/zip", "filename": "bundle.zip", "body": {"attachmentId": "att_zip"}},
                    {"mimeType": "image/jpeg", "filename": "badge.jpg", "body": {"attachmentId": "att_img"}}
                ]
            }
        }
        parsed = {
            "sender": "recruiter@enterprise.com",
            "sender_domain": "enterprise.com",
            "subject": "Job Offer - Staff Engineer",
            "received_at": timezone.now(),
            "body": "Congratulations on the offer!"
        }

        canonical = CanonicalEmail.from_raw_gmail_message(raw_msg, parsed)
        payload_dict = canonical.to_dict()
        self.assertTrue(payload_dict["attachments_omitted"])
        self.assertNotIn("parts", payload_dict)
        self.assertNotIn("OfferLetter.pdf", json.dumps(payload_dict))
        self.assertNotIn("bundle.zip", json.dumps(payload_dict))


class GmailFullMailboxDiscoveryTests(TestCase):
    """
    Test suite verifying broad Gmail retrieval without premature keyword filtering,
    full 365-day historical coverage, resumable pagination, and decoupled worker execution.
    """

    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser_full@example.com",
            email="testuser_full@example.com",
            password="testpassword123",
            gmail_connected=True,
            gmail_access_token="mock_access_token",
            gmail_refresh_token="mock_refresh_token"
        )

    @patch('services.gmail_service.build')
    def test_gmail_service_query_has_no_premature_keyword_filter(self, mock_build):
        """Verify Gmail query uses broad high-recall date boundary without restrictive keyword list."""
        from services.gmail_service import GmailService
        mock_gmail = MagicMock()
        mock_build.return_value = mock_gmail
        mock_messages = MagicMock()
        mock_gmail.users.return_value.messages.return_value = mock_messages
        mock_messages.list.return_value.execute.return_value = {
            'messages': [{'id': 'msg_001', 'threadId': 't_001'}],
            'nextPageToken': 'token_page_2'
        }

        service = GmailService(self.user)
        messages, next_token = service.get_message_page(
            page_token=None,
            max_results=25,
            days_back=365
        )

        self.assertEqual(len(messages), 1)
        self.assertEqual(next_token, 'token_page_2')

        mock_messages.list.assert_called_once()
        call_kwargs = mock_messages.list.call_args[1]
        
        self.assertEqual(call_kwargs['userId'], 'me')
        self.assertEqual(call_kwargs['maxResults'], 25)
        self.assertNotIn('pageToken', call_kwargs)
        
        q_arg = call_kwargs['q']
        self.assertTrue(q_arg.startswith('after:'), f"Query should start with after:, got: {q_arg}")
        self.assertNotIn('application', q_arg)
        self.assertNotIn('interview', q_arg)
        self.assertNotIn('assessment', q_arg)

    @patch('services.gmail_service.build')
    def test_gmail_service_with_page_token_and_incremental_timestamp(self, mock_build):
        """Verify get_message_page correctly passes pageToken and incremental after_timestamp."""
        from services.gmail_service import GmailService
        mock_gmail = MagicMock()
        mock_build.return_value = mock_gmail
        mock_messages = MagicMock()
        mock_gmail.users.return_value.messages.return_value = mock_messages
        mock_messages.list.return_value.execute.return_value = {
            'messages': [{'id': 'msg_002', 'threadId': 't_002'}],
            'nextPageToken': None
        }

        service = GmailService(self.user)
        sync_time = timezone.now() - timedelta(days=5)
        messages, next_token = service.get_message_page(
            page_token='custom_cursor_token_abc',
            max_results=50,
            after_timestamp=sync_time
        )

        self.assertEqual(len(messages), 1)
        self.assertIsNone(next_token)

        call_kwargs = mock_messages.list.call_args[1]
        self.assertEqual(call_kwargs['pageToken'], 'custom_cursor_token_abc')
        self.assertEqual(call_kwargs['maxResults'], 50)
        expected_date = sync_time.strftime('%Y/%m/%d')
        self.assertEqual(call_kwargs['q'], f'after:{expected_date}')

    @override_settings(GMAIL_INITIAL_SYNC_DAYS=365, GMAIL_SYNC_PAGE_SIZE=25)
    @patch('services.sync_service.GmailService')
    def test_sync_gmail_batch_multi_page_resumable(self, mock_gmail_service_cls):
        """Verify multi-page batch sync persists cursor, handles pagination, and saves gmail_last_sync on finish."""
        from services.sync_service import SyncService
        from apps.gmail_integration.models import SyncLog
        mock_service_instance = MagicMock()
        mock_gmail_service_cls.return_value = mock_service_instance

        # Page 1: Returns 2 messages + next_page_token
        mock_service_instance.get_message_page.return_value = (
            [{'id': 'msg_page1_1'}, {'id': 'msg_page1_2'}],
            'token_page_2'
        )
        mock_service_instance.fetch_and_parse_message.side_effect = lambda msg_id: {
            'gmail_message_id': msg_id,
            'thread_id': f'thread_{msg_id}',
            'sender': 'recruiter@tech.io',
            'sender_domain': 'tech.io',
            'subject': f'Invitation to interview {msg_id}',
            'received_at': timezone.now(),
            'snippet': 'We would like to invite you for an interview.',
            'body': 'Interview invitation details...',
            'raw': {'id': msg_id, 'threadId': f'thread_{msg_id}', 'labelIds': ['INBOX']}
        }

        # Run Page 1
        res1 = SyncService.sync_gmail_batch(self.user, reset=True)
        self.assertEqual(res1['emails_scanned'], 2)
        self.assertTrue(res1['has_more'])
        self.assertEqual(res1['page'], 1)
        self.assertEqual(res1['status'], 'running')

        self.user.refresh_from_db()
        self.assertEqual(self.user.gmail_sync_cursor, 'token_page_2')
        self.assertEqual(self.user.gmail_sync_page, 1)
        self.assertEqual(self.user.gmail_sync_status, 'running')
        self.assertIsNone(self.user.gmail_last_sync)

        self.assertEqual(ProcessedEmail.objects.filter(user=self.user).count(), 2)
        self.assertEqual(EmailProcessingJob.objects.filter(user=self.user, status=JobStatus.PENDING).count(), 2)

        # Page 2: Returns 1 message + None
        mock_service_instance.get_message_page.return_value = (
            [{'id': 'msg_page2_1'}],
            None
        )

        res2 = SyncService.sync_gmail_batch(self.user, reset=False)
        self.assertEqual(res2['emails_scanned'], 1)
        self.assertFalse(res2['has_more'])
        self.assertEqual(res2['status'], 'completed')

        self.user.refresh_from_db()
        self.assertIsNone(self.user.gmail_sync_cursor)
        self.assertEqual(self.user.gmail_sync_status, 'completed')
        self.assertIsNotNone(self.user.gmail_last_sync)
        self.assertEqual(res2['cumulative']['emails_scanned'], 3)
        self.assertEqual(res2['cumulative']['pages_processed'], 2)

        self.assertEqual(ProcessedEmail.objects.filter(user=self.user).count(), 3)
        self.assertEqual(EmailProcessingJob.objects.filter(user=self.user, status=JobStatus.PENDING).count(), 3)

        self.assertEqual(SyncLog.objects.filter(user=self.user).count(), 1)
        log = SyncLog.objects.get(user=self.user)
        self.assertEqual(log.emails_scanned, 3)

    @override_settings(GMAIL_INITIAL_SYNC_DAYS=365)
    @patch('services.sync_service.GmailService')
    def test_deduplication_and_no_premature_application_creation(self, mock_gmail_service_cls):
        """
        Verify:
        1. Duplicate message IDs are skipped cleanly.
        2. Sync ingestion creates ProcessedEmail + EmailProcessingJob without creating Applications prematurely.
        3. Worker subsequently processes the queued jobs into Applications without duplicate AI processing.
        """
        from services.sync_service import SyncService
        mock_service_instance = MagicMock()
        mock_gmail_service_cls.return_value = mock_service_instance

        mock_service_instance.get_message_page.return_value = (
            [{'id': 'msg_dup_001'}, {'id': 'msg_dup_001'}],
            None
        )
        mock_service_instance.fetch_and_parse_message.return_value = {
            'gmail_message_id': 'msg_dup_001',
            'thread_id': 'thread_dup_001',
            'sender': 'jobs@anthropic.com',
            'sender_domain': 'anthropic.com',
            'subject': 'Update regarding your recent conversation with Anthropic',
            'received_at': timezone.now(),
            'snippet': 'Thank you for speaking with our team regarding the Research Engineer role.',
            'body': 'We are pleased to invite you to the technical stage for the Research Engineer position.',
            'raw': {'id': 'msg_dup_001', 'threadId': 'thread_dup_001', 'labelIds': ['ARCHIVE']}
        }

        res = SyncService.sync_gmail_batch(self.user, reset=True)
        self.assertEqual(res['status'], 'completed')

        self.assertEqual(ProcessedEmail.objects.filter(user=self.user, gmail_message_id='msg_dup_001').count(), 1)
        email_record = ProcessedEmail.objects.get(user=self.user, gmail_message_id='msg_dup_001')
        
        self.assertIsNone(email_record.application_id)
        self.assertEqual(Application.objects.filter(user=self.user).count(), 0)

        self.assertEqual(EmailProcessingJob.objects.filter(user=self.user, email=email_record).count(), 1)
        job = EmailProcessingJob.objects.get(user=self.user, email=email_record)
        self.assertEqual(job.status, JobStatus.PENDING)

        worker = EmailWorker(worker_id="test-worker-01")
        batch_result = worker.process_batch(batch_size=10)

        self.assertEqual(batch_result['successful'], 1)
        job.refresh_from_db()
        self.assertEqual(job.status, JobStatus.COMPLETED)

        email_record.refresh_from_db()
        self.assertTrue(email_record.is_job_related)
        self.assertIsNotNone(email_record.application_id)

        self.assertEqual(Application.objects.filter(user=self.user).count(), 1)
        app = Application.objects.get(user=self.user)
        self.assertEqual(app.company, 'Anthropic')

        self.assertEqual(StatusHistory.objects.filter(application=app).count(), 1)





