"""
Management command to output system health, observability stats, and provider readiness.
"""
from django.core.management.base import BaseCommand
import json
from services.observability_service import ObservabilityService


class Command(BaseCommand):
    help = 'Audit system health, queue status, circuit breaker states, and observability telemetry'

    def handle(self, *args, **options):
        self.stdout.write("Gathering system observability metrics...")
        metrics = ObservabilityService.get_system_metrics()
        self.stdout.write(json.dumps(metrics, indent=2))
        self.stdout.write(self.style.SUCCESS("System health audit complete."))
