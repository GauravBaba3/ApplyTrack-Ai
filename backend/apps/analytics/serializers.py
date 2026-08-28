"""
Serializers for analytics app.
"""
from rest_framework import serializers
from .models import UserAnalytics


class UserAnalyticsSerializer(serializers.ModelSerializer):
    """Serializer for UserAnalytics model."""
    class Meta:
        model = UserAnalytics
        fields = [
            'total_applications', 'applications_this_month',
            'interview_rate', 'response_rate', 'offer_rate',
            'rejection_rate', 'avg_days_to_response'
        ]
