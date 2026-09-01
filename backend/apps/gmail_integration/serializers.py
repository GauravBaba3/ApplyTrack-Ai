"""
Serializers for gmail_integration app.
"""
from rest_framework import serializers
from .models import ProcessedEmail, SyncLog, ProcessingStatus, EmailEventType


class ProcessingStatusSerializer(serializers.Field):
    """Serializer for ProcessingStatus choices."""
    def to_representation(self, value):
        if not value:
            return ''
        return getattr(value, 'value', str(value))
    
    def to_internal_value(self, data):
        if not data:
            return ProcessingStatus.DETECTED
        try:
            return ProcessingStatus(data)
        except ValueError:
            return str(data)


class EmailEventTypeSerializer(serializers.Field):
    """Serializer for EmailEventType choices."""
    def to_representation(self, value):
        if not value:
            return ''
        return getattr(value, 'value', str(value))
    
    def to_internal_value(self, data):
        if not data:
            return EmailEventType.OTHER
        try:
            return EmailEventType(data)
        except ValueError:
            return str(data)


class ProcessedEmailSerializer(serializers.ModelSerializer):
    """Serializer for ProcessedEmail model."""
    processing_status = ProcessingStatusSerializer()
    event_type = EmailEventTypeSerializer()
    
    class Meta:
        model = ProcessedEmail
        fields = [
            'id', 'gmail_message_id', 'thread_id', 'sender',
            'sender_domain', 'subject', 'received_at', 'snippet',
            'is_job_related', 'company', 'job_title', 'detected_status',
            'event_type', 'interview_date', 'ai_confidence',
            'processing_status', 'triage_priority', 'r2_object_key',
            'r2_storage_status', 'r2_content_sha256', 'r2_compression_version',
            'compressed_size_bytes', 'raw_retention_expires_at',
            'object_storage_key', 'object_storage_status',
            'application_id', 'created_at', 'updated_at'
        ]
        read_only_fields = fields


class SyncLogSerializer(serializers.ModelSerializer):
    """Serializer for SyncLog model."""
    class Meta:
        model = SyncLog
        fields = [
            'id', 'started_at', 'completed_at', 'emails_scanned',
            'job_related_emails', 'applications_updated',
            'new_applications', 'needs_review', 'error_message'
        ]
        read_only_fields = fields


class SyncSummarySerializer(serializers.Serializer):
    """Serializer for sync summary."""
    emails_scanned = serializers.IntegerField(default=0)
    job_related_emails = serializers.IntegerField(default=0)
    applications_updated = serializers.IntegerField(default=0)
    new_applications = serializers.IntegerField(default=0)
    needs_review = serializers.IntegerField(default=0)
    message = serializers.CharField(default='')
    status = serializers.CharField(required=False, default='completed')
    has_more = serializers.BooleanField(required=False, default=False)
    page = serializers.IntegerField(required=False, default=1)
    cumulative = serializers.DictField(required=False, default=dict)


class SyncStatusResponseSerializer(serializers.Serializer):
    """Serializer for sync status response."""
    status = serializers.CharField()
    page = serializers.IntegerField()
    has_more = serializers.BooleanField()
    last_sync = serializers.DateTimeField(allow_null=True)
    stats = serializers.DictField()


class EmailProcessingJobSerializer(serializers.ModelSerializer):
    """Serializer for EmailProcessingJob model."""
    class Meta:
        from .models import EmailProcessingJob
        model = EmailProcessingJob
        fields = [
            'id', 'gmail_message_id', 'thread_id', 'priority', 'status',
            'triage_status', 'triage_score', 'triage_reason', 'triaged_at',
            'processing_stage', 'attempt_count', 'max_attempts', 'next_attempt_at',
            'locked_at', 'locked_by', 'completed_at', 'last_error',
            'effective_priority_score', 'created_at', 'updated_at'
        ]
        read_only_fields = fields
