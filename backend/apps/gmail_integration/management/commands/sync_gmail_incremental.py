"""
Management command to run incremental Gmail sync across all active users.
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from services.sync_service import SyncService

User = get_user_model()


class Command(BaseCommand):
    help = 'Run incremental Gmail sync for all users with connected Gmail accounts'

    def add_arguments(self, parser):
        parser.add_argument('--user-id', type=int, help='Specific user ID to sync')

    def handle(self, *args, **options):
        user_id = options.get('user_id')
        if user_id:
            users = User.objects.filter(id=user_id, gmail_connected=True)
        else:
            users = User.objects.filter(gmail_connected=True)

        self.stdout.write(f"Starting incremental Gmail sync for {users.count()} users...")

        for user in users:
            try:
                self.stdout.write(f"Syncing user {user.id} ({user.email})...")
                res = SyncService.sync_user_emails(user)
                self.stdout.write(
                    self.style.SUCCESS(
                        f"User {user.id}: Synced {res.get('emails_fetched', 0)} emails "
                        f"({res.get('new_ingested', 0)} new canonical objects created)"
                    )
                )
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Sync error for user {user.id}: {str(e)}"))
