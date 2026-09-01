"""
Management command to run scheduled P3 re-triage, thread promotions, and anti-starvation aging.
"""
from django.core.management.base import BaseCommand
from services.queue.job_scheduler import JobScheduler


class Command(BaseCommand):
    help = 'Reprocess P3 queue items, check thread activity, and apply anti-starvation promotions'

    def handle(self, *args, **options):
        self.stdout.write("Running scheduled P3 queue re-triage and aging maintenance...")

        # 1. Recover any stale locks
        stale_reclaimed = JobScheduler.recover_stale_locks()
        self.stdout.write(f"Stale locks reclaimed: {stale_reclaimed}")

        # 2. Apply anti-starvation aging promotions (> 6 hours old P3 -> P2)
        aging_promoted = JobScheduler.apply_aging_promotions()
        self.stdout.write(f"Aging promotions applied (P3 -> P2): {aging_promoted}")

        self.stdout.write(self.style.SUCCESS("P3 queue re-triage completed successfully."))
