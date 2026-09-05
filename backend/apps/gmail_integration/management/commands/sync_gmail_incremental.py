"""
Management command to run incremental Gmail sync across all active users.

Called by the Render cron job every 15 minutes (applytrack-sync-gmail).
Coordinates through the durable GmailSyncJob architecture:
1. Requests/activates a durable GmailSyncJob in Neon PostgreSQL
2. Claims the job with lease lock
3. Executes page-by-page ingestion and advances checkpoint
4. Recovers any stale sync jobs abandoned by crashed worker instances
"""
import logging
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from apps.gmail_integration.models import GmailSyncJob, SyncJobStatus
from services.queue.gmail_sync_coordinator import GmailSyncCoordinator

User = get_user_model()
logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Run durable incremental Gmail sync for all users with connected Gmail accounts'

    def add_arguments(self, parser):
        parser.add_argument('--user-id', type=int, help='Specific user ID to sync')
        parser.add_argument('--reset', action='store_true', default=False,
                            help='Force full re-sync (ignore existing cursor/checkpoint)')
        parser.add_argument('--max-pages', type=int, default=50,
                            help='Max pages to process per user (safety limit)')

    def handle(self, *args, **options):
        user_id = options.get('user_id')
        reset = options.get('reset', False)
        max_pages = options.get('max_pages', 50)

        if user_id:
            users = User.objects.filter(id=user_id, gmail_connected=True)
        else:
            users = User.objects.filter(gmail_connected=True)

        user_count = users.count()
        self.stdout.write(f"Starting durable incremental Gmail sync for {user_count} users...")

        for user in users:
            try:
                self.stdout.write(f"Syncing user {user.id} ({user.email})...")

                # 1. Request or activate durable GmailSyncJob
                job = GmailSyncCoordinator.request_sync(user=user, reset=reset)

                # 2. Claim job for this cron worker run
                cron_worker_id = f"cron-sync-{user.id}"
                # If job was already claimed by a live continuous worker, execute_sync_job will skip
                if job.status == SyncJobStatus.RUNNING and job.worker_id and not job.worker_id.startswith("cron-"):
                    # Check if worker lease is fresh
                    if job.last_heartbeat_at:
                        from django.utils import timezone
                        from datetime import timedelta
                        if (timezone.now() - job.last_heartbeat_at) < timedelta(seconds=GmailSyncCoordinator.STALE_LEASE_SECONDS):
                            self.stdout.write(
                                f"User {user.id} already being processed by live worker [{job.worker_id}]. Skipping."
                            )
                            continue

                job.status = SyncJobStatus.RUNNING
                job.worker_id = cron_worker_id
                from django.utils import timezone
                job.last_heartbeat_at = timezone.now()
                job.save(update_fields=['status', 'worker_id', 'last_heartbeat_at'])

                # 3. Execute pages
                result = GmailSyncCoordinator.execute_sync_job(
                    job_id=job.id,
                    worker_id=cron_worker_id,
                    max_pages=max_pages,
                )

                if result.get('success'):
                    job.refresh_from_db()
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"User {user.id}: Done. status={job.status} "
                            f"scanned={job.emails_fetched} stored={job.emails_stored} "
                            f"pages={job.pages_processed}"
                        )
                    )
                else:
                    self.stdout.write(
                        self.style.WARNING(f"User {user.id}: finished with status={result.get('error')}")
                    )

            except Exception as e:
                logger.error(f"Cron sync error for user {user.id}: {e}", exc_info=True)
                self.stdout.write(self.style.ERROR(f"Sync error for user {user.id}: {str(e)}"))
