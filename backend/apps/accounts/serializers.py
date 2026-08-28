"""
Serializers for accounts app.
"""
from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import UserSettings

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    """Serializer for CustomUser model."""
    csrf_token = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name',
            'gmail_connected', 'gmail_last_sync', 'stale_application_threshold',
            'created_at', 'updated_at', 'csrf_token'
        ]
        read_only_fields = ['id', 'gmail_last_sync', 'created_at', 'updated_at', 'csrf_token']

    def get_csrf_token(self, obj):
        request = self.context.get('request')
        if request:
            from django.middleware.csrf import get_token
            return get_token(request)
        return None


class UserSettingsSerializer(serializers.ModelSerializer):
    """Serializer for UserSettings model."""
    
    class Meta:
        model = UserSettings
        fields = ['notifications_enabled', 'sync_frequency']
