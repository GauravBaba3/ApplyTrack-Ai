"""
Diagnostic command to safely verify Gmail sync worker execution path,
database identity, pending/running jobs, and claimability against Neon PostgreSQL.

CRITICAL SAFETY:
- Never outputs passwords, full connection strings, or secrets.
- Tests claim_next_job() inside an atomic transaction rollback to leave DB state untouched.
"""
from datetime import timedelta
from urllib.parse import urlparse
from django.core.management.base import BaseCommand
from django.conf import settings
from django.utils import timezone
from django.db import transaction, close_old_connections
from apps.gmail_integration.models import (
    GmailSyncJob,
    SyncJobStatus,
    EmailProcessingJob,
    JobStatus,
)
from services.queue.gmail_sync_coordinator import GmailSyncCoordinator


class Command(BaseCommand):
    help = 'Safely diagnose worker execution path, Neon database identity, and job claimability.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--probe-claim',
            action='store_true',
            default=True,
            help='Perform a dry-run claim test using database transaction rollback (default: True).',
        )

    def handle(self, *args, **options):
        close_old_connections()
        self.stdout.write("=" * 70)
        self.stdout.write(" ApplyTrack AI — Worker & Database Execution Path Diagnostic")
        self.stdout.write("=" * 70)

        # 1. Database Configuration & Identity (Safe logging, no credentials)
        db_conf = settings.DATABASES.get('default', {})
        engine = db_conf.get('ENGINE', '')
        engine_short = 'postgresql' if 'postgres' in engine else ('sqlite3' if 'sqlite' in engine else engine)
        host = db_conf.get('HOST') or 'localhost'
        dbname = db_conf.get('NAME') or ''
        is_prod = (not settings.DEBUG) or ('RENDER' in settings.ALLOWED_HOSTS or 'RENDER' in dir(settings))

        self.stdout.write("\n[1] Database Runtime Identity:")
        self.stdout.write(f"  • Engine: {engine_short} ({engine})")
        self.stdout.write(f"  • Host:   {host}")
        self.stdout.write(f"  • DB:     {dbname}")
        self.stdout.write(f"  • Mode:   {'PRODUCTION (DEBUG=False)' if not settings.DEBUG else 'DEVELOPMENT (DEBUG=True)'}")

        if (not settings.DEBUG) and 'sqlite' in engine_short:
            self.stdout.write(self.style.ERROR("  [CRITICAL ERROR] Production environment is running on SQLite! This violates production safety."))
        else:
            self.stdout.write(self.style.SUCCESS(f"  [OK] Database engine matches expected target: {engine_short}"))

        # 2. GmailSyncJob Table State in this database
        now = timezone.now()
        stale_cutoff = now - timedelta(seconds=GmailSyncCoordinator.STALE_LEASE_SECONDS)

        pending_count = GmailSyncJob.objects.filter(status=SyncJobStatus.PENDING).count()
        running_jobs = GmailSyncJob.objects.filter(status=SyncJobStatus.RUNNING)
        running_count = running_jobs.count()
        stale_count = running_jobs.filter(last_heartbeat_at__lt=stale_cutoff).count()
        completed_count = GmailSyncJob.objects.filter(status=SyncJobStatus.COMPLETED).count()
        failed_count = GmailSyncJob.objects.filter(status=SyncJobStatus.FAILED).count()

        self.stdout.write("\n[2] Durable GmailSyncJob Table Metrics:")
        self.stdout.write(f"  • PENDING Jobs:   {pending_count}")
        self.stdout.write(f"  • RUNNING Jobs:   {running_count} (stale > 5min: {stale_count})")
        self.stdout.write(f"  • COMPLETED Jobs: {completed_count}")
        self.stdout.write(f"  • FAILED Jobs:    {failed_count}")

        # List recent active jobs
        active_jobs = GmailSyncJob.objects.filter(
            status__in=[SyncJobStatus.PENDING, SyncJobStatus.RUNNING]
        ).order_by('-created_at')[:5]

        if active_jobs:
            self.stdout.write("\n  Active Job Details:")
            for j in active_jobs:
                is_stale_flag = (j.status == SyncJobStatus.RUNNING and j.last_heartbeat_at and j.last_heartbeat_at < stale_cutoff)
                self.stdout.write(
                    f"    - Job #{j.id} | User {j.user_id} | status={j.status} | "
                    f"worker={j.worker_id} | stale={is_stale_flag} | "
                    f"page={j.page} | cursor={bool(j.cursor)} | created={j.created_at}"
                )
        else:
            self.stdout.write("  • No active (PENDING or RUNNING) jobs currently in database.")

        # 3. Downstream Processing Queue Metrics
        queued_processing = EmailProcessingJob.objects.filter(
            status__in=[JobStatus.PENDING, JobStatus.RETRY]
        ).count()
        in_progress_processing = EmailProcessingJob.objects.filter(
            status=JobStatus.PROCESSING
        ).count()
        completed_processing = EmailProcessingJob.objects.filter(
            status=JobStatus.COMPLETED
        ).count()

        self.stdout.write("\n[3] EmailProcessingJob Queue Metrics:")
        self.stdout.write(f"  • Pending/Retry: {queued_processing}")
        self.stdout.write(f"  • Processing:    {in_progress_processing}")
        self.stdout.write(f"  • Completed:     {completed_processing}")

        # 4. Dry-Run Claim Test (Atomic Rollback)
        self.stdout.write("\n[4] Claim Query Dry-Run Verification:")
        try:
            with transaction.atomic():
                claimed = GmailSyncCoordinator.claim_next_job(worker_id="diagnostic-probe")
                if claimed:
                    self.stdout.write(self.style.SUCCESS(
                        f"  [SUCCESS] claim_next_job() successfully claimed Job #{claimed.id} "
                        f"(User {claimed.user_id}, status transitioned to {claimed.status})."
                    ))
                else:
                    self.stdout.write(
                        "  [INFO] claim_next_job() returned None. (No PENDING or stale RUNNING jobs exist)."
                    )
                # Strictly roll back so dry-run probe leaves database state untouched
                transaction.set_rollback(True)
            self.stdout.write("  [OK] Dry-run transaction rolled back. Database state preserved.")
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"  [CLAIM ERROR] claim_next_job() failed with exception: {e}"))

        # 5. Environment & Integration Sanity (Boolean presence only, no secrets)
        self.stdout.write("\n[5] Environment Integration Sanity:")
        checks = [
            ("DATABASE_URL", bool(settings.DATABASES['default'].get('NAME'))),
            ("GOOGLE_CLIENT_ID", bool(getattr(settings, 'GOOGLE_CLIENT_ID', ''))),
            ("GOOGLE_CLIENT_SECRET", bool(getattr(settings, 'GOOGLE_CLIENT_SECRET', ''))),
            ("B2_KEY_ID / APPLICATION_KEY", bool(getattr(settings, 'B2_KEY_ID', ''))),
            ("AI_PROVIDERS (Groq/Gemini/OpenRouter)", bool(
                getattr(settings, 'GROQ_API_KEY', '') or
                getattr(settings, 'GEMINI_API_KEY', '') or
                getattr(settings, 'OPENROUTER_API_KEY', '')
            )),
        ]
        for name, ok in checks:
            status_text = self.style.SUCCESS("CONFIGURED") if ok else self.style.WARNING("NOT CONFIGURED")
            self.stdout.write(f"  • {name:<36}: {status_text}")

        self.stdout.write("\n" + "=" * 70)
        self.stdout.write(" Diagnostic Complete.")
        self.stdout.write("=" * 70 + "\n")
