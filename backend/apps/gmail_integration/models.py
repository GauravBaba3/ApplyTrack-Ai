"""
Gmail integration models for tracking processed emails.
"""
from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class EmailEventType(models.TextChoices):
    """Types of job-related email events."""
    APPLICATION_CONFIRMATION = 'application_confirmation', 'Application Confirmation'
    APPLICATION_RECEIVED = 'application_received', 'Application Received'
    INTERVIEW_INVITATION = 'interview_invitation', 'Interview Invitation'
    ASSESSMENT_INVITATION = 'assessment_invitation', 'Assessment Invitation'
    RECRUITER_OUTREACH = 'recruiter_outreach', 'Recruiter Outreach'
    REJECTION = 'rejection', 'Rejection'
    OFFER = 'offer', 'Offer'
    NEXT_ROUND = 'next_round', 'Next Round'
    HIRING_MANAGER_MESSAGE = 'hiring_manager_message', 'Hiring Manager Message'
    CODING_ASSESSMENT = 'coding_assessment', 'Coding Assessment'
    INTERVIEW_SCHEDULING = 'interview_scheduling', 'Interview Scheduling'
    APPLICATION_STATUS_UPDATE = 'application_status_update', 'Application Status Update'
    POSITION_FILLED = 'position_filled', 'Position Filled'
    CANDIDATE_NOT_SELECTED = 'candidate_not_selected', 'Candidate Not Selected'
    APPLICATION_WITHDRAWN = 'application_withdrawn', 'Application Withdrawn'
    OTHER = 'other', 'Other'


class ProcessingStatus(models.TextChoices):
    """Status of email processing."""
    DETECTED = 'detected', 'Detected'
    NEEDS_REVIEW = 'needs_review', 'Needs Review'
    IGNORED = 'ignored', 'Ignored'
    PROCESSED = 'processed', 'Processed'
    FAILED = 'failed', 'Failed'


class TriagePriority(models.TextChoices):
    """Priority queues for asynchronous email processing."""
    P1 = 'P1', 'P1 - High (Interview/Offer/Decision/Rejection)'
    P2 = 'P2', 'P2 - Medium (Assessment/Application/Status/Recruiter)'
    P3 = 'P3', 'P3 - Low (Alerts/Newsletters/Deferred)'


class R2StorageStatus(models.TextChoices):
    """Status of raw compressed email in Cloudflare R2."""
    PENDING = 'pending', 'Pending'
    UPLOADED = 'uploaded', 'Uploaded'
    FAILED = 'failed', 'Failed'
    PRUNED = 'pruned', 'Pruned (Retention Expired)'


class ProcessedEmail(models.Model):
    """Model for storing processed job-related emails and R2 storage references."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='processed_emails')
    
    # Gmail identifiers
    gmail_message_id = models.CharField(max_length=255, unique=True)
    thread_id = models.CharField(max_length=255)
    
    # Cloudflare R2 Object Storage Reference & Compression metadata
    r2_object_key = models.CharField(max_length=512, blank=True, null=True, db_index=True)
    r2_storage_status = models.CharField(
        max_length=20,
        choices=R2StorageStatus.choices,
        default=R2StorageStatus.PENDING,
        db_index=True
    )
    r2_content_sha256 = models.CharField(max_length=64, blank=True, null=True)
    r2_compression_version = models.CharField(max_length=20, default='gzip-v1')
    compressed_size_bytes = models.IntegerField(default=0)
    raw_retention_expires_at = models.DateTimeField(blank=True, null=True, db_index=True)
    
    triage_priority = models.CharField(
        max_length=10,
        choices=TriagePriority.choices,
        default=TriagePriority.P2,
        db_index=True
    )
    
    # Email metadata
    sender = models.EmailField()
    sender_domain = models.CharField(max_length=255, blank=True, null=True)
    subject = models.CharField(max_length=1000)
    received_at = models.DateTimeField()
    
    # Extracted content (safe snippet only)
    snippet = models.TextField(blank=True, null=True)
    
    # AI classification
    is_job_related = models.BooleanField(default=False)
    company = models.CharField(max_length=255, blank=True, null=True)
    job_title = models.CharField(max_length=255, blank=True, null=True)
    detected_status = models.CharField(
        max_length=50,
        blank=True,
        null=True
    )
    event_type = models.CharField(
        max_length=50,
        choices=EmailEventType.choices,
        blank=True,
        null=True
    )
    interview_date = models.DateTimeField(blank=True, null=True)
    ai_confidence = models.FloatField(default=0.0)
    
    # Processing metadata
    processing_status = models.CharField(
        max_length=50,
        choices=ProcessingStatus.choices,
        default=ProcessingStatus.DETECTED
    )
    
    # Store application ID instead of ForeignKey to avoid circular dependency
    application_id = models.IntegerField(blank=True, null=True, db_index=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.subject} from {self.sender}"

    @property
    def object_storage_key(self) -> str:
        """Provider-neutral alias for cloud object storage reference key."""
        return self.r2_object_key or ''

    @object_storage_key.setter
    def object_storage_key(self, value: str):
        self.r2_object_key = value

    @property
    def b2_object_key(self) -> str:
        """Backblaze B2 specific alias for cloud object storage reference key."""
        return self.r2_object_key or ''

    @b2_object_key.setter
    def b2_object_key(self, value: str):
        self.r2_object_key = value

    @property
    def object_storage_status(self) -> str:
        """Provider-neutral alias for cloud object storage status."""
        return self.r2_storage_status

    @object_storage_status.setter
    def object_storage_status(self, value: str):
        self.r2_storage_status = value
    
    class Meta:
        ordering = ['-received_at']
        indexes = [
            models.Index(fields=['user', 'gmail_message_id']),
            models.Index(fields=['user', 'thread_id']),
            models.Index(fields=['user', 'processing_status']),
            models.Index(fields=['user', 'is_job_related']),
            models.Index(fields=['user', 'received_at']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'gmail_message_id'],
                name='unique_user_message_id'
            ),
        ]


class SyncLog(models.Model):
    """Log of Gmail sync operations."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sync_logs')
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(blank=True, null=True)
    emails_scanned = models.IntegerField(default=0)
    job_related_emails = models.IntegerField(default=0)
    applications_updated = models.IntegerField(default=0)
    new_applications = models.IntegerField(default=0)
    needs_review = models.IntegerField(default=0)
    error_message = models.TextField(blank=True, null=True)
    
    def __str__(self):
        return f"Sync at {self.started_at} - {self.emails_scanned} emails scanned"
    
    class Meta:
        ordering = ['-started_at']


class JobStatus(models.TextChoices):
    """Durable queue processing job states."""
    PENDING = 'PENDING', 'Pending'
    PROCESSING = 'PROCESSING', 'Processing'
    COMPLETED = 'COMPLETED', 'Completed'
    RETRY = 'RETRY', 'Retry'
    FAILED = 'FAILED', 'Failed'
    NEEDS_REVIEW = 'NEEDS_REVIEW', 'Needs Review'
    DEAD_LETTER = 'DEAD_LETTER', 'Dead Letter'


class TriageStatusChoice(models.TextChoices):
    """High-recall initial triage classification categories."""
    JOB_LIKELY = 'job_likely', 'Job Likely'
    UNCERTAIN = 'uncertain', 'Uncertain'
    LOW_PRIORITY = 'low_priority', 'Low Priority'


class EmailProcessingJob(models.Model):
    """
    Durable queue job record for asynchronous, priority-scheduled email processing.
    Stored in Neon PostgreSQL (not in-memory).
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='processing_jobs')
    email = models.OneToOneField(
        ProcessedEmail,
        on_delete=models.CASCADE,
        related_name='processing_job'
    )
    
    # Identifiers for quick lookup
    gmail_message_id = models.CharField(max_length=255, db_index=True)
    thread_id = models.CharField(max_length=255, db_index=True)
    
    # Queue Priority & Status
    priority = models.CharField(
        max_length=10,
        choices=TriagePriority.choices,
        default=TriagePriority.P2,
        db_index=True
    )
    status = models.CharField(
        max_length=20,
        choices=JobStatus.choices,
        default=JobStatus.PENDING,
        db_index=True
    )
    
    # Triage metadata
    triage_status = models.CharField(
        max_length=20,
        choices=TriageStatusChoice.choices,
        default=TriageStatusChoice.UNCERTAIN,
        db_index=True
    )
    triage_score = models.FloatField(default=0.0)
    triage_reason = models.TextField(blank=True, null=True)
    triaged_at = models.DateTimeField(auto_now_add=True)
    
    # Processing stage tracking
    processing_stage = models.CharField(max_length=50, default='triage')
    
    # Retry & scheduling
    attempt_count = models.IntegerField(default=0)
    max_attempts = models.IntegerField(default=3)
    next_attempt_at = models.DateTimeField(auto_now_add=True, db_index=True)
    
    # Locking & concurrency (crash-safe)
    locked_at = models.DateTimeField(blank=True, null=True, db_index=True)
    locked_by = models.CharField(max_length=255, blank=True, null=True)
    completed_at = models.DateTimeField(blank=True, null=True)
    
    # Error tracking
    last_error = models.TextField(blank=True, null=True)
    
    # Effective priority for aging / fair scheduling
    effective_priority_score = models.FloatField(default=0.0, db_index=True)
    
    # Optional link to active GmailSyncJob session
    sync_job = models.ForeignKey(
        'GmailSyncJob',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='email_jobs',
        db_index=True
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Job {self.id} [{self.priority} - {self.status}] for msg {self.gmail_message_id}"
    
    class Meta:
        ordering = ['-priority', 'next_attempt_at']
        indexes = [
            models.Index(fields=['priority', 'status', 'next_attempt_at']),
            models.Index(fields=['thread_id', 'priority']),
            models.Index(fields=['status', 'locked_at']),
            models.Index(fields=['sync_job', 'status']),
        ]


class ProviderUsageLog(models.Model):
    """
    Model for tracking AI provider & API usage metrics in Neon PostgreSQL.
    Tracks token counts, latencies, success rates, and status codes without storing secrets.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='provider_usage_logs', null=True, blank=True)
    provider = models.CharField(max_length=50, db_index=True)  # 'gmail', 'huggingface', 'groq', 'gemini', 'openrouter'
    model_name = models.CharField(max_length=100, blank=True, null=True)
    endpoint = models.CharField(max_length=255, blank=True, null=True)
    request_tokens = models.IntegerField(default=0)
    response_tokens = models.IntegerField(default=0)
    total_tokens = models.IntegerField(default=0)
    latency_ms = models.IntegerField(default=0)
    status_code = models.IntegerField(default=200)
    success = models.BooleanField(default=True, db_index=True)
    error_message = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['provider', 'created_at']),
            models.Index(fields=['provider', 'success']),
        ]

    def __str__(self):
        return f"{self.provider} [{self.status_code}] ({self.latency_ms}ms) at {self.created_at}"


class SyncJobStatus(models.TextChoices):
    """Lifecycle states for durable Gmail synchronization jobs."""
    PENDING = 'PENDING', 'Pending'
    RUNNING = 'RUNNING', 'Running'
    COMPLETED = 'COMPLETED', 'Completed'
    FAILED = 'FAILED', 'Failed'
    CANCELLED = 'CANCELLED', 'Cancelled'


class GmailSyncJob(models.Model):
    """
    Durable server-side Gmail synchronization job record stored in Neon PostgreSQL.
    Tracks pagination checkpoints, worker leases, heartbeats, metrics, and recovery states
    independently of Django web-process or browser lifetimes.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='gmail_sync_jobs')
    status = models.CharField(
        max_length=20,
        choices=SyncJobStatus.choices,
        default=SyncJobStatus.PENDING,
        db_index=True
    )
    
    # Checkpoint & Pagination
    cursor = models.CharField(max_length=255, blank=True, null=True)
    page = models.IntegerField(default=0)
    pages_processed = models.IntegerField(default=0)
    
    # Granular Pipeline Counters
    emails_fetched = models.IntegerField(default=0)
    emails_stored = models.IntegerField(default=0)
    emails_queued = models.IntegerField(default=0)
    job_related_emails = models.IntegerField(default=0)
    applications_updated = models.IntegerField(default=0)
    new_applications = models.IntegerField(default=0)
    needs_review = models.IntegerField(default=0)
    
    # Lease & Lock Ownership (Crash-Safe Recovery)
    worker_id = models.CharField(max_length=255, blank=True, null=True, db_index=True)
    last_heartbeat_at = models.DateTimeField(blank=True, null=True, db_index=True)
    lease_timeout_seconds = models.IntegerField(default=300)
    
    # Retry and Error Tracking
    retry_count = models.IntegerField(default=0)
    max_retries = models.IntegerField(default=3)
    last_error = models.TextField(blank=True, null=True)
    
    # Lifecycle Timestamps
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    started_at = models.DateTimeField(blank=True, null=True)
    completed_at = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['status', 'last_heartbeat_at']),
        ]

    def __str__(self):
        return f"GmailSyncJob #{self.id} [{self.status}] user={self.user_id} page={self.page} worker={self.worker_id}"


