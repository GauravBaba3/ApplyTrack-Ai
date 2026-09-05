"""
Management command to run the ApplyTrack AI Background Worker daemon.

Supervises both:
1. Producer: GmailSyncCoordinator (claims durable GmailSyncJob records, fetches pages,
   persists emails, queues jobs, and advances checkpoints)
2. Consumer: EmailWorker (claims queued EmailProcessingJob records, decompresses from B2,
   runs tiered AI classification, and updates applications)

Both operate concurrently in the background worker process independently of the web process.
"""
import sys
import signal
import threading
from django.core.management.base import BaseCommand
from services.queue.email_worker import EmailWorker
from services.queue.gmail_sync_coordinator import GmailSyncCoordinator
from services.queue.load_controller import LoadController


class Command(BaseCommand):
    help = 'Run the background worker daemon for durable Gmail ingestion and email processing.'

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
            help='Process a single batch/job and immediately exit.',
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
        parser.add_argument(
            '--process-only',
            action='store_true',
            help='Run only the EmailWorker consumer (no Gmail sync producer).',
        )
        parser.add_argument(
            '--sync-only',
            action='store_true',
            help='Run only the GmailSyncCoordinator producer (no email processing).',
        )

    def handle(self, *args, **options):
        worker_id = options['worker_id']
        run_once = options['once']
        max_batches = options['max_batches']
        poll_interval = options['poll_interval']
        batch_size = options['batch_size']
        process_only = options.get('process_only', False)
        sync_only = options.get('sync_only', False)

        stop_requested = threading.Event()
        worker = EmailWorker(worker_id=worker_id)

        # Handle graceful shutdown on SIGINT / SIGTERM
        def sig_handler(signum, frame):
            self.stdout.write(self.style.WARNING(f"\nReceived signal {signum}. Requesting graceful worker shutdown..."))
            stop_requested.set()
            worker.stop()

        signal.signal(signal.SIGINT, sig_handler)
        if hasattr(signal, 'SIGTERM'):
            signal.signal(signal.SIGTERM, sig_handler)

        mode_desc = "sync-only" if sync_only else ("process-only" if process_only else "concurrent producer + consumer")
        self.stdout.write(self.style.NOTICE(
            f"Starting Worker [{worker_id}] mode={mode_desc} "
            f"(poll_interval={poll_interval}s, once={run_once})..."
        ))

        # ------------------------------------------------------------------
        # SINGLE-RUN MODE (--once)
        # ------------------------------------------------------------------
        if run_once:
            if not process_only:
                sync_job = GmailSyncCoordinator.claim_next_job(worker_id=f"{worker_id}-sync")
                if sync_job:
                    res = GmailSyncCoordinator.execute_sync_job(
                        job_id=sync_job.id,
                        worker_id=f"{worker_id}-sync",
                        max_pages=1,
                    )
                    self.stdout.write(self.style.SUCCESS(f"Single sync job execution finished: {res}"))
                else:
                    self.stdout.write("No pending GmailSyncJob found.")

            if not sync_only:
                result = worker.process_batch(batch_size=batch_size)
                self.stdout.write(self.style.SUCCESS(
                    f"Batch execution finished: {result['processed']} processed "
                    f"({result['successful']} successful, {result['failed']} failed)."
                ))
            return

        # ------------------------------------------------------------------
        # CONTINUOUS MODE
        # ------------------------------------------------------------------
        sync_thread = None

        if not process_only:
            # Launch Gmail Sync Producer thread
            sync_thread = threading.Thread(
                target=GmailSyncCoordinator.run_loop,
                kwargs={
                    'worker_id': f"{worker_id}-sync",
                    'poll_interval_seconds': poll_interval,
                    'should_stop_callable': stop_requested.is_set,
                },
                name=f"gmail-sync-producer-{worker_id}",
                daemon=False,
            )
            sync_thread.start()
            self.stdout.write(self.style.SUCCESS(f"GmailSyncProducer thread started [{worker_id}-sync]."))

        if not sync_only:
            # Run Email Processing Consumer on the main thread
            try:
                worker.run_loop(poll_interval_seconds=poll_interval, max_batches=max_batches)
            finally:
                stop_requested.set()
        else:
            # In sync-only mode, wait on the sync thread
            try:
                while not stop_requested.is_set():
                    stop_requested.wait(timeout=1.0)
            except KeyboardInterrupt:
                stop_requested.set()

        # Clean shutdown join
        if sync_thread and sync_thread.is_alive():
            self.stdout.write("Waiting for GmailSyncProducer to finish current page...")
            sync_thread.join(timeout=30)

        self.stdout.write(self.style.SUCCESS(f"Worker [{worker_id}] stopped cleanly."))
