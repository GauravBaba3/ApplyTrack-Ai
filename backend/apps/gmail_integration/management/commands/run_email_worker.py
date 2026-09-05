"""
Management command to run the ApplyTrack AI Background Worker daemon.

Supervises both:
1. Producer: GmailSyncCoordinator (claims durable GmailSyncJob records, fetches pages,
   persists emails, queues jobs, and advances checkpoints)
2. Consumer: EmailWorker (claims queued EmailProcessingJob records, decompresses from B2,
   runs tiered AI classification, and updates applications)

Both operate concurrently in the background worker process independently of the web process.
Includes database pre-flight checks, thread watchdog supervision, and connection recycling.
"""
import sys
import signal
import threading
import logging
from django.core.management.base import BaseCommand
from django.conf import settings
from django.db import close_old_connections
from services.queue.email_worker import EmailWorker
from services.queue.gmail_sync_coordinator import GmailSyncCoordinator
from services.queue.load_controller import LoadController

logger = logging.getLogger(__name__)


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

        # ------------------------------------------------------------------
        # STARTUP DATABASE DIAGNOSTIC (Safe host/engine logging, no secrets)
        # ------------------------------------------------------------------
        db_conf = settings.DATABASES.get('default', {})
        raw_engine = db_conf.get('ENGINE', '')
        engine_type = 'postgresql' if 'postgres' in raw_engine else ('sqlite3' if 'sqlite' in raw_engine else raw_engine)
        host = db_conf.get('HOST') or 'localhost'
        dbname = db_conf.get('NAME') or ''
        is_production = (not settings.DEBUG) or ('RENDER' in settings.ALLOWED_HOSTS or 'RENDER' in dir(settings))

        # Check production invariant
        if (not settings.DEBUG) and 'sqlite' in engine_type:
            err_msg = "[WORKER_DB_ERROR] Production worker is not allowed to run on SQLite."
            logger.critical(err_msg)
            self.stderr.write(self.style.ERROR(err_msg))
            sys.exit(1)

        db_diag = (
            f"[WORKER_DB]\n"
            f"engine={engine_type}\n"
            f"host={host}\n"
            f"database={dbname}"
        )
        logger.info(f"[WORKER_DB] engine={engine_type} host={host} database={dbname}")
        self.stdout.write(db_diag)

        stop_requested = threading.Event()
        worker = EmailWorker(worker_id=worker_id)

        # Handle graceful shutdown on SIGINT / SIGTERM
        def sig_handler(signum, frame):
            logger.warning(f"[WORKER_SIGNAL] Received signal {signum}. Requesting graceful worker shutdown...")
            self.stdout.write(self.style.WARNING(f"\nReceived signal {signum}. Requesting graceful worker shutdown..."))
            stop_requested.set()
            worker.stop()

        signal.signal(signal.SIGINT, sig_handler)
        if hasattr(signal, 'SIGTERM'):
            signal.signal(signal.SIGTERM, sig_handler)

        mode_desc = "sync-only" if sync_only else ("process-only" if process_only else "concurrent producer + consumer")
        startup_msg = f"[WORKER_START] Worker {worker_id} started (poll_interval={poll_interval}s, mode={mode_desc}, once={run_once})"
        logger.info(startup_msg)
        self.stdout.write(self.style.NOTICE(startup_msg))

        # ------------------------------------------------------------------
        # SINGLE-RUN MODE (--once)
        # ------------------------------------------------------------------
        if run_once:
            close_old_connections()
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
                close_old_connections()
                result = worker.process_batch(batch_size=batch_size)
                self.stdout.write(self.style.SUCCESS(
                    f"Batch execution finished: {result['processed']} processed "
                    f"({result['successful']} successful, {result['failed']} failed)."
                ))
            return

        # ------------------------------------------------------------------
        # CONTINUOUS SUPERVISED MODE
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
            logger.info(f"[GMAIL_COORDINATOR_STARTED] GmailSyncCoordinator thread active [{worker_id}-sync]")
            self.stdout.write(self.style.SUCCESS(f"[GMAIL_COORDINATOR_STARTED] GmailSyncCoordinator thread active [{worker_id}-sync]"))

        if not sync_only:
            logger.info(f"[EMAIL_WORKER_STARTED] EmailWorker consumer loop active [{worker_id}]")
            self.stdout.write(self.style.SUCCESS(f"[EMAIL_WORKER_STARTED] EmailWorker consumer loop active [{worker_id}]"))

        # Supervisor loop running on main thread
        batches_processed = 0
        try:
            while not stop_requested.is_set():
                # 1. Watchdog: check producer thread health
                if sync_thread is not None and not sync_thread.is_alive() and not stop_requested.is_set():
                    logger.critical(
                        f"[WORKER_FATAL] GmailSyncCoordinator thread crashed or terminated unexpectedly! "
                        f"Worker [{worker_id}] cannot continue without producer. Terminating worker for restart."
                    )
                    self.stderr.write(self.style.ERROR("[WORKER_FATAL] GmailSyncCoordinator thread crashed unexpectedly!"))
                    stop_requested.set()
                    worker.stop()
                    sys.exit(1)

                # 2. Recycle stale DB connections
                close_old_connections()

                # 3. Process email jobs batch if consumer is enabled
                had_work = False
                if not sync_only:
                    try:
                        batch_res = worker.process_batch(batch_size=batch_size)
                        if batch_res.get('processed', 0) > 0:
                            had_work = True
                            batches_processed += 1
                            if max_batches and batches_processed >= max_batches:
                                logger.info(f"[WORKER_MAX_BATCHES] Reached limit ({max_batches}). Stopping.")
                                stop_requested.set()
                                break
                    except Exception as e:
                        logger.error(f"[EMAIL_WORKER_ERROR] Consumer batch error: {e}", exc_info=True)

                # If consumer had work, continue immediately without sleep; otherwise wait poll_interval
                if not had_work:
                    stop_requested.wait(timeout=poll_interval)

        except KeyboardInterrupt:
            stop_requested.set()
            worker.stop()
        finally:
            stop_requested.set()
            worker.stop()

        # Clean shutdown join
        if sync_thread and sync_thread.is_alive():
            self.stdout.write("Waiting for GmailSyncProducer to finish current page...")
            sync_thread.join(timeout=30)

        logger.info(f"[WORKER_STOPPED] Worker [{worker_id}] stopped cleanly.")
        self.stdout.write(self.style.SUCCESS(f"[WORKER_STOPPED] Worker [{worker_id}] stopped cleanly."))
