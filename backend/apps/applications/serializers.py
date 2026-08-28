"""
Serializers for applications app.
"""
from rest_framework import serializers
from .models import Application, StatusHistory, FollowUp, ApplicationStatus, ApplicationSource


class ApplicationSourceSerializer(serializers.Field):
    """Serializer for ApplicationSource choices."""
    def to_representation(self, value):
        if not value:
            return ''
        return getattr(value, 'value', str(value))
    
    def to_internal_value(self, data):
        if not data:
            return ApplicationSource.OTHER
        try:
            return ApplicationSource(data)
        except ValueError:
            return str(data)


class ApplicationStatusSerializer(serializers.Field):
    """Serializer for ApplicationStatus choices."""
    def to_representation(self, value):
        if not value:
            return ''
        return getattr(value, 'value', str(value))
    
    def to_internal_value(self, data):
        if not data:
            return ApplicationStatus.APPLIED
        try:
            return ApplicationStatus(data)
        except ValueError:
            return str(data)


class ApplicationSerializer(serializers.ModelSerializer):
    """Serializer for Application model."""
    source = ApplicationSourceSerializer()
    current_status = ApplicationStatusSerializer()
    
    class Meta:
        model = Application
        fields = [
            'id', 'company', 'job_title', 'job_url', 'location',
            'source', 'application_date', 'current_status',
            'status_updated_at', 'last_email_date', 'last_activity_date',
            'confidence', 'notes', 'is_ai_detected', 'is_manual',
            'needs_review', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'status_updated_at', 'last_email_date',
            'last_activity_date', 'confidence', 'is_ai_detected',
            'created_at', 'updated_at'
        ]


class ApplicationDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for Application model with related data."""
    source = ApplicationSourceSerializer()
    current_status = ApplicationStatusSerializer()
    
    class Meta:
        model = Application
        fields = '__all__'


class StatusHistorySerializer(serializers.ModelSerializer):
    """Serializer for StatusHistory model."""
    previous_status = ApplicationStatusSerializer()
    new_status = ApplicationStatusSerializer()
    
    class Meta:
        model = StatusHistory
        fields = ['id', 'application', 'previous_status', 'new_status', 'source', 'timestamp', 'related_email_id']


class FollowUpSerializer(serializers.ModelSerializer):
    """Serializer for FollowUp model."""
    class Meta:
        model = FollowUp
        fields = ['id', 'application', 'draft_subject', 'draft_body', 'created_at', 'is_sent']
        read_only_fields = ['id', 'created_at', 'is_sent']


class ApplicationStatsSerializer(serializers.Serializer):
    """Serializer for application statistics."""
    total_applications = serializers.IntegerField()
    applied = serializers.IntegerField()
    assessment = serializers.IntegerField()
    interview = serializers.IntegerField()
    offer = serializers.IntegerField()
    rejected = serializers.IntegerField()
    no_response = serializers.IntegerField()
    stale = serializers.IntegerField()
    needs_review = serializers.IntegerField()


class ApplicationCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating applications manually."""
    source = ApplicationSourceSerializer()
    current_status = ApplicationStatusSerializer()
    
    class Meta:
        model = Application
        fields = [
            'company', 'job_title', 'job_url', 'location',
            'source', 'application_date', 'current_status', 'notes'
        ]
