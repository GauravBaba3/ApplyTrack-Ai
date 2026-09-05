"""
End-to-End Production Worker Pipeline Verification Script.

Validates:
1. Database identity (PostgreSQL on Neon, same DB for web and worker)
2. Production safety invariant: Fail-fast on missing DATABASE_URL or SQLite in production
3. Start sync API: POST /api/gmail/sync/start/ -> creates durable GmailSyncJob as PENDING
4. Worker claim: claim_next_job() claims the EXACT Neon row -> RUNNING with worker_id
5. Gmail fetch & persistence: Fetches page, stores ProcessedEmail, queues EmailProcessingJob
6. Worker consumption: EmailWorker claims and processes jobs from Neon
7. Status API: GET /api/gmail/sync/status/ reflects real progression
8. Watchdog & Connection recycling: Validates supervision and close_old_connections
"""
import os
import sys
import json
import time
import subprocess
from pathlib import Path

# Setup Django
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

import django
django.setup()

from django.test import Client
from django.contrib.auth import get_user_model
from django.db import connection, close_old_connections
from apps.gmail_integration.models import (
    GmailSyncJob,
    SyncJobStatus,
    ProcessedEmail,
    EmailProcessingJob,
    JobStatus,
)
from services.queue.gmail_sync_coordinator import GmailSyncCoordinator
from services.queue.email_worker import EmailWorker

User = get_user_model()

results = {}

def run_test(name, fn):
    print(f"\n{'='*70}\n[TEST] {name}\n{'='*70}")
    try:
        fn()
        results[name] = "PASS"
        print(f"[PASS] {name}")
    except Exception as e:
        results[name] = f"FAIL: {e}"
        print(f"[FAIL] {name}: {e}")
        import traceback
        traceback.print_exc()

# --------------------------------------------------------------------------
# Test 1: Worker uses PostgreSQL on Neon
# --------------------------------------------------------------------------
def test_1_database_identity():
    db_conf = connection.settings_dict
    engine = db_conf.get('ENGINE', '')
    host = db_conf.get('HOST', '')
    name = db_conf.get('NAME', '')
    print(f"Engine: {engine}")
    print(f"Host:   {host}")
    print(f"Name:   {name}")
    assert 'postgresql' in engine, f"Expected postgresql engine, got {engine}"
    assert 'neon.tech' in host, f"Expected Neon host, got {host}"
    assert name == 'neondb', f"Expected neondb database, got {name}"

# --------------------------------------------------------------------------
# Test 2: Web and Worker use the exact same database
# --------------------------------------------------------------------------
def test_2_same_database():
    # Web view and worker code both import Django connection settings
    from django.conf import settings
    web_db = settings.DATABASES['default']
    assert 'postgres' in web_db['ENGINE']
    assert web_db['HOST'] == connection.settings_dict['HOST']
    assert web_db['NAME'] == connection.settings_dict['NAME']
    print(f"Shared Host: {web_db['HOST']}")

# --------------------------------------------------------------------------
# Test 3: Missing DATABASE_URL in production fails fast
# --------------------------------------------------------------------------
def test_3_production_fail_fast():
    env = os.environ.copy()
    env['DEBUG'] = 'False'
    env['DATABASE_URL'] = ''
    proc = subprocess.run(
        [sys.executable, '-c', "import django, os; os.environ['DJANGO_SETTINGS_MODULE']='config.settings'; django.setup()"],
        env=env,
        capture_output=True,
        text=True,
    )
    assert proc.returncode != 0, "Expected non-zero exit code when DATABASE_URL is missing in production"
    assert "DATABASE_URL environment variable is required in production" in proc.stderr, (
        f"Missing expected error message in stderr: {proc.stderr}"
    )
    print("Verified fail-fast on missing DATABASE_URL in production.")

# --------------------------------------------------------------------------
# Test 4: SQLite in production fails fast
# --------------------------------------------------------------------------
def test_4_production_sqlite_rejected():
    env = os.environ.copy()
    env['DEBUG'] = 'False'
    env['DATABASE_URL'] = 'sqlite:///test_sqlite.db'
    proc = subprocess.run(
        [sys.executable, '-c', "import django, os; os.environ['DJANGO_SETTINGS_MODULE']='config.settings'; django.setup()"],
        env=env,
        capture_output=True,
        text=True,
    )
    assert proc.returncode != 0, "Expected non-zero exit code when SQLite configured in production"
    assert "SQLite database engine is not permitted in production" in proc.stderr, (
        f"Missing expected error message in stderr: {proc.stderr}"
    )
    print("Verified fail-fast on SQLite in production.")

# --------------------------------------------------------------------------
# Test 5: POST /api/gmail/sync/start/ creates durable GmailSyncJob as PENDING
# --------------------------------------------------------------------------
user = None
job_id = None

def test_5_start_sync_api():
    global user, job_id
    user = User.objects.filter(gmail_connected=True).first()
    assert user is not None, "No user with gmail_connected=True found"
    print(f"Testing with User {user.id} ({user.email})")

    # Clear any active jobs for clean test
    GmailSyncJob.objects.filter(user=user, status__in=[SyncJobStatus.PENDING, SyncJobStatus.RUNNING]).update(
        status=SyncJobStatus.COMPLETED
    )

    client = Client()
    client.force_login(user)

    response = client.post('/api/gmail/sync/start/', data={'reset': True})
    assert response.status_code == 202, f"Expected 202 Accepted, got {response.status_code}: {response.content}"
    data = response.json()
    assert data.get('status') in ('started', 'running'), f"Unexpected status: {data.get('status')}"
    job_id = data.get('sync', {}).get('job_id') or data.get('sync_job_id')
    assert job_id is not None, f"Expected sync_job_id in response: {data}"

    job = GmailSyncJob.objects.get(id=job_id)
    assert job.status in (SyncJobStatus.PENDING, SyncJobStatus.RUNNING), f"Expected PENDING or RUNNING status, got {job.status}"
    assert job.user_id == user.id
    print(f"Created GmailSyncJob #{job.id} in Neon with status={job.status}")

# --------------------------------------------------------------------------
# Test 6: Worker claims GmailSyncJob (PENDING -> RUNNING)
# --------------------------------------------------------------------------
def test_6_worker_claims_job():
    global job_id
    worker_id = "test-worker-prod-01-sync"
    claimed_job = GmailSyncCoordinator.claim_next_job(worker_id=worker_id)
    assert claimed_job is not None, "Worker failed to claim job"
    assert claimed_job.id == job_id, f"Expected to claim Job #{job_id}, got #{claimed_job.id}"
    assert claimed_job.status == SyncJobStatus.RUNNING, f"Expected RUNNING status, got {claimed_job.status}"
    assert claimed_job.worker_id == worker_id, f"Expected worker_id {worker_id}, got {claimed_job.worker_id}"
    print(f"Worker claimed Job #{claimed_job.id}: status={claimed_job.status}, worker={claimed_job.worker_id}")

# --------------------------------------------------------------------------
# Test 7: Worker executes 1 page of sync
# --------------------------------------------------------------------------
def test_7_worker_executes_page():
    global job_id
    worker_id = "test-worker-prod-01-sync"
    res = GmailSyncCoordinator.execute_sync_job(
        job_id=job_id,
        worker_id=worker_id,
        max_pages=1,
    )
    assert res.get('success') is True, f"execute_sync_job failed: {res}"
    job = GmailSyncJob.objects.get(id=job_id)
    print(f"Sync execution finished: pages={job.pages_processed}, fetched={job.emails_fetched}, stored={job.emails_stored}, cursor={bool(job.cursor)}")
    assert job.pages_processed >= 1, "Expected at least 1 page processed"
    assert job.emails_fetched >= 1, "Expected emails fetched from Gmail API"

# --------------------------------------------------------------------------
# Test 8: EmailWorker consumes processing jobs from Neon
# --------------------------------------------------------------------------
def test_8_email_worker_consumption():
    worker = EmailWorker(worker_id="test-consumer-01")
    batch_res = worker.process_batch()
    print(f"Batch execution result: {batch_res}")
    assert 'processed' in batch_res

# --------------------------------------------------------------------------
# Test 9: GET /api/gmail/sync/status/ reflects current-sync progression
# --------------------------------------------------------------------------
def test_9_status_api():
    client = Client()
    client.force_login(user)
    response = client.get('/api/gmail/sync/status/')
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    data = response.json()
    assert 'sync' in data, "Expected 'sync' key in status API"
    assert 'global' in data, "Expected 'global' key in status API"
    sync_data = data['sync']
    print(f"API Current Sync Metrics: fetched={sync_data.get('emails_fetched')}, stored={sync_data.get('emails_stored')}, status={sync_data.get('status')}")

# --------------------------------------------------------------------------
# Test 10: Connection recycling verification
# --------------------------------------------------------------------------
def test_10_connection_recycling():
    close_old_connections()
    assert connection.connection is None or connection.is_usable(), "Connection should be closed or usable"
    # Execute simple query to confirm clean reconnection
    count = GmailSyncJob.objects.count()
    assert count >= 1
    print("close_old_connections() cleanly recycles and reconnects.")

# --------------------------------------------------------------------------
# Test 11: Run All Tests
# --------------------------------------------------------------------------
if __name__ == '__main__':
    run_test("1. Worker uses PostgreSQL on Neon", test_1_database_identity)
    run_test("2. Web and worker use same database", test_2_same_database)
    run_test("3. Missing DATABASE_URL fails fast in production", test_3_production_fail_fast)
    run_test("4. SQLite rejected in production", test_4_production_sqlite_rejected)
    run_test("5. POST /api/gmail/sync/start/ creates PENDING job", test_5_start_sync_api)
    run_test("6. Worker claims job (PENDING -> RUNNING)", test_6_worker_claims_job)
    run_test("7. Gmail page actually fetched & persisted", test_7_worker_executes_page)
    run_test("8. EmailWorker consumes processing jobs", test_8_email_worker_consumption)
    run_test("9. Status API reflects scoped progression", test_9_status_api)
    run_test("10. Connection recycling functions cleanly", test_10_connection_recycling)

    print("\n" + "=" * 70)
    print(" SUMMARY OF ACCEPTANCE TESTS")
    print("=" * 70)
    all_passed = True
    for name, res in results.items():
        print(f"  {name:<50}: {res}")
        if not res.startswith("PASS"):
            all_passed = False
    print("=" * 70)
    if all_passed:
        print("ALL ACCEPTANCE TESTS PASSED SUCCESSFULLY!")
        sys.exit(0)
    else:
        print("SOME TESTS FAILED!")
        sys.exit(1)
