"""
Custom user model and Gmail token storage for ApplyTrack AI.
"""
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone


class CustomUser(AbstractUser):
    """Custom user model with additional fields for Gmail integration."""
    
    gmail_connected = models.BooleanField(default=False)
    gmail_access_token = models.TextField(blank=True, null=True)
    gmail_refresh_token = models.TextField(blank=True, null=True)
    gmail_token_expiry = models.DateTimeField(blank=True, null=True)
    gmail_last_sync = models.DateTimeField(blank=True, null=True)
    
    # Incremental & paginated sync tracking
    gmail_sync_status = models.CharField(max_length=20, default='idle')  # idle, running, completed, failed
    gmail_sync_cursor = models.CharField(max_length=255, blank=True, null=True)
    gmail_sync_page = models.IntegerField(default=0)
    gmail_sync_started_at = models.DateTimeField(blank=True, null=True)
    gmail_sync_batch_stats = models.JSONField(default=dict, blank=True)
    
    # Settings
    stale_application_threshold = models.IntegerField(default=14)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.email or self.username
    
    class Meta:
        ordering = ['-created_at']


class UserSettings(models.Model):
    """Extended user settings."""
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='settings')
    notifications_enabled = models.BooleanField(default=True)
    sync_frequency = models.CharField(max_length=20, default='manual')  # manual, daily, weekly
    
    def __str__(self):
        return f"Settings for {self.user.email}"
