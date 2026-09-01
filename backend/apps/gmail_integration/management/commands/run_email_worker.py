"""
Management command to run the ApplyTrack AI Email Processing Worker daemon.
"""
import sys
import signal
from django.core.management.base import BaseCommand
from services.queue.email_worker import EmailWorker
from services.queue.load_controller import LoadController


class Command(BaseCommand):
    help = 'Run the background Email Processing Worker daemon to process queued emails in controlled batches.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--worker-id',
            type=str,
            default='worker-01',
            help='Unique identifier for this worker instance (default: worker-01).',
        )
        parser.add_argument(
            '--once',
            action='store_true',
            help='Process a single batch and immediately exit.',
        )
        parser.add_argument(
            '--max-batches',
            type=int,
            default=None,
            help='Maximum number of batches to process before terminating.',
        )
        parser.add_argument(
            '--poll-interval',
            type=int,
            default=5,
            help='Poll interval in seconds when queue is empty (default: 5).',
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=None,
            help='Override default batch size for processing.',
        )

    def handle(self, *args, **options):
        worker_id = options['worker_id']
        run_once = options['once']
        max_batches = options['max_batches']
        poll_interval = options['poll_interval']
        batch_size = options['batch_size']

        worker = EmailWorker(worker_id=worker_id)

        # Handle graceful shutdown on SIGINT / SIGTERM
        def sig_handler(signum, frame):
            self.stdout.write(self.style.WARNING(f"\nReceived signal {signum}. Requesting graceful worker shutdown..."))
            worker.stop()

        signal.signal(signal.SIGINT, sig_handler)
        if hasattr(signal, 'SIGTERM'):
            signal.signal(signal.SIGTERM, sig_handler)

        self.stdout.write(self.style.NOTICE(f"Starting EmailWorker [{worker_id}] (batch_size={batch_size or LoadController.get_current_batch_size()}, once={run_once})..."))

        if run_once:
            result = worker.process_batch(batch_size=batch_size)
            self.stdout.write(self.style.SUCCESS(
                f"Batch execution finished: {result['processed']} processed ({result['successful']} successful, {result['failed']} failed)."
            ))
        else:
            worker.run_loop(poll_interval_seconds=poll_interval, max_batches=max_batches)
            self.stdout.write(self.style.SUCCESS(f"Worker [{worker_id}] stopped cleanly."))
