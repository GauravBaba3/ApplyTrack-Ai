"""
Job application tracking models for ApplyTrack AI.
"""
from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()


class ApplicationSource(models.TextChoices):
    """Sources for job applications."""
    LINKEDIN = 'LinkedIn', 'LinkedIn'
    INDEED = 'Indeed', 'Indeed'
    COMPANY_WEBSITE = 'Company Website', 'Company Website'
    NAUKRI = 'Naukri', 'Naukri'
    WELLFOUND = 'Wellfound', 'Wellfound'
    REFERRAL = 'Referral', 'Referral'
    EMAIL = 'Email', 'Email'
    OTHER = 'Other', 'Other'


class ApplicationStatus(models.TextChoices):
    """Status choices for job applications."""
    APPLIED = 'Applied', 'Applied'
    ASSESSMENT = 'Assessment', 'Assessment'
    INTERVIEW = 'Interview', 'Interview'
    OFFER = 'Offer', 'Offer'
    REJECTED = 'Rejected', 'Rejected'
    WITHDRAWN = 'Withdrawn', 'Withdrawn'
    PENDING = 'Pending', 'Pending'
    NO_RESPONSE = 'No Response', 'No Response'
    GHOSTED = 'Ghosted', 'Ghosted'
    UNKNOWN = 'Unknown', 'Unknown'


class Application(models.Model):
    """Main job application model."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='applications')
    
    # Company and role information
    company = models.CharField(max_length=255)
    job_title = models.CharField(max_length=255)
    job_url = models.URLField(blank=True, null=True)
    location = models.CharField(max_length=255, blank=True, null=True)
    source = models.CharField(
        max_length=50,
        choices=ApplicationSource.choices,
        default=ApplicationSource.OTHER
    )
    
    # Application details
    application_date = models.DateField()
    current_status = models.CharField(
        max_length=50,
        choices=ApplicationStatus.choices,
        default=ApplicationStatus.APPLIED
    )
    
    # Tracking fields
    status_updated_at = models.DateTimeField(auto_now_add=True)
    last_email_date = models.DateTimeField(blank=True, null=True)
    last_activity_date = models.DateTimeField(blank=True, null=True)
    confidence = models.FloatField(default=1.0)  # Confidence in AI detection
    
    # User notes
    notes = models.TextField(blank=True, null=True)
    
    # Metadata
    is_ai_detected = models.BooleanField(default=False)
    is_manual = models.BooleanField(default=False)
    needs_review = models.BooleanField(default=False)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.company} - {self.job_title} ({self.current_status})"
    
    class Meta:
        ordering = ['-application_date']
        indexes = [
            models.Index(fields=['user', 'company']),
            models.Index(fields=['user', 'current_status']),
            models.Index(fields=['user', 'application_date']),
        ]


class StatusHistory(models.Model):
    """History of status changes for applications."""
    application = models.ForeignKey(
        Application, 
        on_delete=models.CASCADE, 
        related_name='status_history'
    )
    previous_status = models.CharField(
        max_length=50,
        choices=ApplicationStatus.choices,
        blank=True,
        null=True
    )
    new_status = models.CharField(
        max_length=50,
        choices=ApplicationStatus.choices
    )
    source = models.CharField(max_length=50, default='ai')  # ai, manual, email
    timestamp = models.DateTimeField(auto_now_add=True)
    # Store related email ID instead of ForeignKey to avoid circular dependency
    related_email_id = models.IntegerField(blank=True, null=True, db_index=True)
    
    def __str__(self):
        return f"{self.application.company}: {self.previous_status} -> {self.new_status}"
    
    class Meta:
        ordering = ['-timestamp']
        verbose_name_plural = 'Status Histories'


class FollowUp(models.Model):
    """Follow-up drafts for applications."""
    application = models.ForeignKey(
        Application,
        on_delete=models.CASCADE,
        related_name='follow_ups'
    )
    draft_subject = models.CharField(max_length=500)
    draft_body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_sent = models.BooleanField(default=False)
    
    def __str__(self):
        return f"Follow-up for {self.application.company}"
    
    class Meta:
        ordering = ['-created_at']
