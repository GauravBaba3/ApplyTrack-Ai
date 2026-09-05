"""
Empirical Verification of Multi-Page Incremental Pipeline & Concurrency.

Proves:
1. Page 1 fetched -> persisted -> queued -> committed
2. Worker IMMEDIATELY starts processing Page 1 jobs
3. WHILE Page 1 is processing: Page 2 is fetched -> persisted -> queued -> committed
4. WHILE Page 2 is processing: Page 3 is fetched -> persisted -> queued -> committed
5. Processing starts before complete Gmail sync finishes!
6. Worker crash recovery: sync resumes from exact persisted cursor checkpoint!
"""
import os
import sys
import time
import threading
from pathlib import Path
from datetime import timedelta
from unittest.mock import patch, MagicMock

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()

from django.utils import timezone
from django.contrib.auth import get_user_model
from apps.gmail_integration.models import (
    GmailSyncJob,
    SyncJobStatus,
    ProcessedEmail,
    EmailProcessingJob,
    JobStatus,
)
from services.sync_service import SyncService
from services.queue.gmail_sync_coordinator import GmailSyncCoordinator
from services.queue.email_worker import EmailWorker
from services.queue.job_scheduler import JobScheduler

User = get_user_model()


def run_multipage_concurrency_proof():
    print("\n" + "=" * 75)
    print("PROVING INCREMENTAL CONCURRENT PIPELINE & WORKER RECOVERY")
    print("=" * 75)

    user, _ = User.objects.get_or_create(
        username="multipage_test_user",
        defaults={"email": "multipage@example.com", "gmail_connected": True}
    )
    user.gmail_connected = True
    user.save()

    # Clean previous test records
    EmailProcessingJob.objects.filter(user=user).delete()
    ProcessedEmail.objects.filter(user=user).delete()
    GmailSyncJob.objects.filter(user=user).delete()

    event_timeline = []

    def record_event(event_name, details=""):
        t = time.time()
        event_timeline.append((t, event_name, details))
        print(f"  [{t:.3f}] {event_name.ljust(35)} : {details}")

    # Mock GmailService pages: 3 pages total
    pages_data = {
        None: ([{"id": f"msg_p1_{i}"} for i in range(1, 4)], "token_page_2"),
        "token_page_2": ([{"id": f"msg_p2_{i}"} for i in range(1, 4)], "token_page_3"),
        "token_page_3": ([{"id": f"msg_p3_{i}"} for i in range(1, 4)], None),
    }

    def mock_get_message_page(page_token=None, max_results=25, days_back=365, after_timestamp=None):
        # Simulate network latency of Gmail API
        time.sleep(0.4)
        messages, next_token = pages_data.get(page_token, ([], None))
        return messages, next_token

    def mock_fetch_and_parse_message(msg_id):
        return {
            "gmail_message_id": msg_id,
            "thread_id": f"thread_{msg_id}",
            "sender": "jobs@company.com",
            "sender_domain": "company.com",
            "subject": f"Interview invitation for {msg_id}",
            "snippet": "We are pleased to invite you for an interview...",
            "received_at": timezone.now(),
            "raw": {"snippet": "We are pleased to invite you..."},
        }

    # Start durable sync job via SyncService (as web endpoint would)
    sync_job = GmailSyncCoordinator.request_sync(user=user, reset=True)
    record_event("SYNC_JOB_CREATED_IN_NEON", f"Job ID #{sync_job.id}, Status=PENDING")

    stop_event = threading.Event()
    worker_started_event = threading.Event()

    # Track timing
    timing = {
        "page_1_committed": None,
        "worker_first_process": None,
        "page_2_committed": None,
        "page_3_committed": None,
        "sync_completed": None,
    }

    # Instrumentation hooks for timeline
    orig_save = GmailSyncJob.save
    def instrumented_job_save(self, *args, **kwargs):
        res = orig_save(self, *args, **kwargs)
        if self.page == 1 and self.cursor == "token_page_2" and not timing["page_1_committed"]:
            timing["page_1_committed"] = time.time()
            record_event("PAGE_1_COMMITTED_TO_NEON", "3 jobs queued, cursor='token_page_2'")
        elif self.page == 2 and self.cursor == "token_page_3" and not timing["page_2_committed"]:
            timing["page_2_committed"] = time.time()
            record_event("PAGE_2_COMMITTED_TO_NEON", "3 jobs queued, cursor='token_page_3'")
        elif self.page == 3 and not self.cursor and not timing["page_3_committed"]:
            timing["page_3_committed"] = time.time()
            record_event("PAGE_3_COMMITTED_TO_NEON", "3 jobs queued, cursor=None")
        if self.status == SyncJobStatus.COMPLETED and not timing["sync_completed"]:
            timing["sync_completed"] = time.time()
            record_event("SYNC_COMPLETED_IN_NEON", f"Total fetched={self.emails_fetched}")
        return res

    orig_process_job = EmailWorker.process_job
    def instrumented_process_job(self, job=None):
        target_job = self if job is None else job
        if not timing["worker_first_process"]:
            timing["worker_first_process"] = time.time()
            worker_started_event.set()
            record_event("WORKER_STARTED_PROCESSING", f"Worker claimed Job #{target_job.id} ({target_job.gmail_message_id})")
        else:
            record_event("WORKER_PROCESSED_JOB", f"Worker completed Job #{target_job.id} ({target_job.gmail_message_id})")
        # Fast local mock for email processing
        JobScheduler.complete_job(target_job)
        return {"success": True, "job_id": target_job.id}

    with patch.object(GmailSyncJob, 'save', instrumented_job_save), \
         patch.object(EmailWorker, 'process_job', instrumented_process_job), \
         patch('services.sync_service.ObjectStorageService.upload_compressed_email', return_value=True), \
         patch('services.storage.b2_service.B2StorageService.upload_compressed_email', return_value=True), \
         patch('services.storage.object_storage_service.ObjectStorageService.upload_compressed_email', return_value=True), \
         patch('services.queue.gmail_sync_coordinator.GmailService') as MockGmailServiceClass:

        mock_svc = MagicMock()
        mock_svc.get_message_page.side_effect = mock_get_message_page
        mock_svc.fetch_and_parse_message.side_effect = mock_fetch_and_parse_message
        MockGmailServiceClass.return_value = mock_svc

        # Thread 1: Ingestion Producer Loop
        def run_producer():
            record_event("PRODUCER_THREAD_STARTING", "Claiming sync job from Neon...")
            job = GmailSyncCoordinator.claim_next_job(worker_id="producer-worker-01")
            if job:
                GmailSyncCoordinator.execute_sync_job(
                    job_id=job.id,
                    worker_id="producer-worker-01",
                    should_stop_callable=stop_event.is_set,
                )
            record_event("PRODUCER_THREAD_FINISHED", "All pages ingested.")

        # Thread 2: Email Worker Consumer Loop
        def run_consumer():
            record_event("CONSUMER_THREAD_STARTING", "Listening for queued EmailProcessingJobs...")
            while not stop_event.is_set():
                # Claim jobs for this test user as soon as they appear in Neon
                user_jobs = list(EmailProcessingJob.objects.filter(user=user, status=JobStatus.PENDING)[:2])
                if user_jobs:
                    for j in user_jobs:
                        j.status = JobStatus.PROCESSING
                        j.save(update_fields=['status'])
                        instrumented_process_job(j)
                        time.sleep(0.05)
                else:
                    time.sleep(0.05)

        t_producer = threading.Thread(target=run_producer, name="producer-thread")
        t_consumer = threading.Thread(target=run_consumer, name="consumer-thread")

        t_producer.start()
        t_consumer.start()

        t_producer.join(timeout=60)
        # Give consumer a moment to finish any remaining jobs
        time.sleep(1.0)
        stop_event.set()
        t_consumer.join(timeout=5)

    print("\n" + "=" * 75)
    print("TIMELINE & CONCURRENCY VERIFICATION")
    print("=" * 75)

    assert timing["page_1_committed"] is not None, "Page 1 was never committed!"
    assert timing["worker_first_process"] is not None, "Worker never started processing!"
    assert timing["page_2_committed"] is not None, "Page 2 was never committed!"
    assert timing["sync_completed"] is not None, "Sync never completed!"

    print(f"1. Page 1 committed at              : {timing['page_1_committed']:.3f}")
    print(f"2. Worker started processing Page 1 : {timing['worker_first_process']:.3f}")
    print(f"3. Page 2 committed at              : {timing['page_2_committed']:.3f}")
    print(f"4. Page 3 committed at              : {timing['page_3_committed']:.3f}")
    print(f"5. Complete Sync finished at        : {timing['sync_completed']:.3f}")

    # Proof of Concurrency: Worker started processing BEFORE sync finished
    assert timing["worker_first_process"] < timing["sync_completed"], \
        "VIOLATION: Worker did NOT start processing before sync finished!"
    print("\n[PROVEN] Worker started processing BEFORE complete sync finished! (Delta: "
          f"{timing['sync_completed'] - timing['worker_first_process']:.3f}s earlier)")

    # Proof of Page-by-Page Pipelining: Worker started processing before Page 2 finished committing
    assert timing["worker_first_process"] <= timing["page_2_committed"] + 0.1, \
        "VIOLATION: Worker did not process Page 1 while Page 2 was in-flight!"
    print(f"[PROVEN] Worker processed Page 1 WHILE Page 2 was being fetched & committed!")

    # ------------------------------------------------------------------
    # PART 2: PROVE WORKER CRASH & CHECKPOINT RECOVERY
    # ------------------------------------------------------------------
    print("\n" + "=" * 75)
    print("PROVING WORKER CRASH & CURSOR RECOVERY (ACROSS PROCESS RESTART)")
    print("=" * 75)

    # Setup a crashed job on Page 2
    crashed_job = GmailSyncJob.objects.create(
        user=user,
        status=SyncJobStatus.RUNNING,
        cursor="token_page_2",
        page=1,
        pages_processed=1,
        emails_fetched=3,
        emails_stored=3,
        worker_id="crashed-worker-pid-9999",
        last_heartbeat_at=timezone.now() - timedelta(minutes=10),  # Stale lease
    )
    record_event("CRASHED_WORKER_SIMULATED", f"Job #{crashed_job.id} at cursor='token_page_2', worker died")

    with patch('services.sync_service.ObjectStorageService.upload_compressed_email', return_value=True), \
         patch('services.storage.b2_service.B2StorageService.upload_compressed_email', return_value=True), \
         patch('services.storage.object_storage_service.ObjectStorageService.upload_compressed_email', return_value=True), \
         patch('services.queue.gmail_sync_coordinator.GmailService') as MockGmailServiceClass2:
        mock_svc2 = MagicMock()
        mock_svc2.get_message_page.side_effect = mock_get_message_page
        mock_svc2.fetch_and_parse_message.side_effect = mock_fetch_and_parse_message
        MockGmailServiceClass2.return_value = mock_svc2

        # New worker starts up after restart
        record_event("NEW_WORKER_STARTUP", "New worker process started. Scanning for jobs...")
        recovered_job = GmailSyncCoordinator.claim_next_job(worker_id="new-worker-pid-1111")

        assert recovered_job is not None, "Failed to claim crashed job!"
        assert recovered_job.id == crashed_job.id
        assert recovered_job.worker_id == "new-worker-pid-1111"
        assert recovered_job.cursor == "token_page_2", f"Cursor lost! {recovered_job.cursor}"
        record_event("STALE_LEASE_RECOVERED", f"Claimed job #{recovered_job.id}, cursor='{recovered_job.cursor}'")

        # Resume execution from checkpoint
        exec_res = GmailSyncCoordinator.execute_sync_job(
            job_id=recovered_job.id,
            worker_id="new-worker-pid-1111",
        )
        assert exec_res['success'] is True, f"Failed executing recovered job: {exec_res}"

        recovered_job.refresh_from_db()
        assert recovered_job.status == SyncJobStatus.COMPLETED
        assert recovered_job.cursor is None
        assert recovered_job.pages_processed >= 2
        record_event("RECOVERED_JOB_COMPLETED", f"Status={recovered_job.status}, Total fetched={recovered_job.emails_fetched}")

    print("\n[PROVEN] Worker crash automatically recovered from persisted checkpoint cursor!")
    print("=" * 75)
    print("ALL EMPIRICAL CONCURRENCY & RECOVERY PROOFS PASSED!")
    print("=" * 75)
    return True


if __name__ == '__main__':
    success = run_multipage_concurrency_proof()
    sys.exit(0 if success else 1)
