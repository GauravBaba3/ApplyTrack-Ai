"""
Management command to prune raw canonical email objects past retention period from Backblaze B2.
"""
from django.core.management.base import BaseCommand
from services.storage.retention_service import RetentionService


class Command(BaseCommand):
    help = 'Prune expired raw canonical email objects (.json.gz) from Backblaze B2 object storage.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Simulate pruning without actually deleting objects from Backblaze B2.',
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=500,
            help='Maximum number of records to process in this run (default: 500).',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        limit = options['limit']

        self.stdout.write(self.style.NOTICE(f"Starting raw email retention pruning (dry_run={dry_run}, limit={limit})..."))
        result = RetentionService.prune_expired_raw_objects(dry_run=dry_run, limit=limit)

        if dry_run:
            self.stdout.write(self.style.WARNING(result['message']))
        else:
            self.stdout.write(self.style.SUCCESS(result['message']))
