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


class ProcessedEmail(models.Model):
    """Model for storing processed job-related emails."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='processed_emails')
    
    # Gmail identifiers
    gmail_message_id = models.CharField(max_length=255, unique=True)
    thread_id = models.CharField(max_length=255)
    
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
