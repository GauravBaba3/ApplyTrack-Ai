"""
Analytics models for ApplyTrack AI.
"""
from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class UserAnalytics(models.Model):
    """Aggregated analytics data for users."""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='analytics')
    total_applications = models.IntegerField(default=0)
    applications_this_month = models.IntegerField(default=0)
    interview_rate = models.FloatField(default=0.0)
    response_rate = models.FloatField(default=0.0)
    offer_rate = models.FloatField(default=0.0)
    rejection_rate = models.FloatField(default=0.0)
    avg_days_to_response = models.FloatField(default=0.0)
    last_updated = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Analytics for {self.user.email}"
    
    class Meta:
        verbose_name_plural = 'User Analytics'
