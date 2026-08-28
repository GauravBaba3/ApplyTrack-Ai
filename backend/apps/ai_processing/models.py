"""
AI processing models for ApplyTrack AI.
"""
from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class AIRequestLog(models.Model):
    """Log of AI API requests for debugging and cost tracking."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='ai_requests')
    request_type = models.CharField(max_length=100)
    tokens_used = models.IntegerField(default=0)
    response_time = models.FloatField(default=0.0)  # seconds
    success = models.BooleanField(default=True)
    error_message = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.request_type} - {self.tokens_used} tokens"
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['user', 'request_type']),
        ]
