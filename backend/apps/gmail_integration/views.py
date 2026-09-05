"""
Views for gmail_integration app.
"""
import logging
from django.utils import timezone
from rest_framework import status, generics, permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import ProcessedEmail, SyncLog
from .serializers import (
    ProcessedEmailSerializer,
    SyncLogSerializer,
    SyncSummarySerializer,
    SyncStatusResponseSerializer
)
from services.sync_service import SyncService

logger = logging.getLogger(__name__)


class ProcessedEmailListView(generics.ListAPIView):
    """List processed emails for the current user."""
    serializer_class = ProcessedEmailSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        queryset = ProcessedEmail.objects.filter(user=user)
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(processing_status=status_filter)
        job_related = self.request.query_params.get('job_related')
        if job_related == 'true':
            queryset = queryset.filter(is_job_related=True)
        elif job_related == 'false':
            queryset = queryset.filter(is_job_related=False)
        return queryset.order_by('-received_at')


class ProcessedEmailDetailView(generics.RetrieveAPIView):
    """Retrieve a specific processed email."""
    serializer_class = ProcessedEmailSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'id'
    
    def get_queryset(self):
        return ProcessedEmail.objects.filter(user=self.request.user)


class SyncLogListView(generics.ListAPIView):
    """List sync logs for the current user."""
    serializer_class = SyncLogSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return SyncLog.objects.filter(user=self.request.user).order_by('-started_at')


class GmailSyncStartView(APIView):
    """
    Start a server-side background Gmail sync for the current user.

    POST /api/gmail/sync/start/

    Returns 202 immediately. The actual sync runs in a background daemon thread
    that survives browser refresh / navigation / close. Duplicate syncs are
    prevented server-side: if a sync is already running, the current state is
    returned without starting a new process.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        user = request.user
        if not user.gmail_connected:
            return Response(
                {'error': 'Gmail is not connected'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        reset = bool(request.data.get('reset', False))
        logger.info(f"[SYNC_START_REQUEST] User {user.id} ({user.email}) reset={reset}")
        try:
            sync_state = SyncService.start_background_sync(user, reset=reset)
            return Response(sync_state, status=status.HTTP_202_ACCEPTED)
        except Exception as e:
            logger.error(f"Failed to start background sync for {user.email}: {e}")
            return Response(
                {'error': f'Failed to start sync: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class GmailSyncView(APIView):
    """
    Legacy Gmail sync endpoint - kept for backward compatibility.

    POST /api/gmail/sync/

    Now delegates to start_background_sync() so the HTTP request returns quickly
    and the actual sync runs server-side.
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        """Start background sync (returns immediately) or return current sync state."""
        try:
            user = request.user
            if not user.gmail_connected:
                return Response(
                    {'error': 'Gmail is not connected'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            reset = bool(request.data.get('reset', False))
            sync_state = SyncService.start_background_sync(user, reset=reset)
            stats = sync_state.get('stats', {})
            summary = {
                'emails_scanned': sync_state.get('emails_fetched', stats.get('emails_scanned', 0)),
                'job_related_emails': sync_state.get('job_related', stats.get('job_related_emails', 0)),
                'applications_updated': sync_state.get('applications_updated', stats.get('applications_updated', 0)),
                'new_applications': sync_state.get('new_applications', stats.get('new_applications', 0)),
                'needs_review': stats.get('needs_review', 0),
                'status': sync_state.get('status', 'running'),
                'has_more': sync_state.get('has_more', True),
                'page': sync_state.get('page', 0),
                'cumulative': stats,
                'message': 'Sync started in background - poll /api/gmail/sync/status/ for progress',
            }
            serializer = SyncSummarySerializer(summary)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Gmail sync start failed: {str(e)}")
            return Response(
                {'error': f'Sync failed: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class GmailSyncStatusView(APIView):
    """
    Get current sync status and granular pipeline progress for the authenticated user.

    GET /api/gmail/sync/status/

    Returns authoritative DB-derived counters. Safe to poll every few seconds.
    All values reflect actual backend state - correct after refresh / reconnect /
    multiple tabs / browser close.
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        """Return pipeline state."""
        try:
            status_data = SyncService.get_sync_status(request.user)
            return Response(status_data, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Failed to get sync status: {str(e)}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class MarkEmailReviewedView(APIView):
    """Mark an email as reviewed."""
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request, email_id):
        """Mark a processed email as reviewed/confirmed."""
        try:
            email = ProcessedEmail.objects.get(id=email_id, user=request.user)
            email.processing_status = 'processed'
            email.save()
            if email.application_id:
                from apps.applications.models import Application
                Application.objects.filter(
                    id=email.application_id,
                    user=request.user
                ).update(needs_review=False)
            serializer = ProcessedEmailSerializer(email)
            return Response(serializer.data)
        except ProcessedEmail.DoesNotExist:
            return Response(
                {'error': 'Email not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Failed to mark email as reviewed: {str(e)}")
            return Response(
                {'error': 'Failed to update email'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class IgnoreEmailView(APIView):
    """Mark an email as ignored."""
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request, email_id):
        """Mark a processed email as ignored."""
        try:
            email = ProcessedEmail.objects.get(id=email_id, user=request.user)
            email.processing_status = 'ignored'
            email.is_job_related = False
            email.save()
            serializer = ProcessedEmailSerializer(email)
            return Response(serializer.data)
        except ProcessedEmail.DoesNotExist:
            return Response(
                {'error': 'Email not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Failed to ignore email: {str(e)}")
            return Response(
                {'error': 'Failed to update email'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
