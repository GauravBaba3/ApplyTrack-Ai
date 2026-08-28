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
        
        # Filter by processing status
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(processing_status=status_filter)
        
        # Filter by is_job_related
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


class GmailSyncView(APIView):
    """Trigger incremental/paginated Gmail sync batch for the current user."""
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        """Sync a batch of Gmail messages."""
        try:
            user = request.user
            
            # Check if Gmail is connected
            if not user.gmail_connected:
                return Response(
                    {'error': 'Gmail is not connected'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            reset = request.data.get('reset', False)
            page_size = request.data.get('page_size', None)
            
            # Perform paginated batch sync
            result = SyncService.sync_gmail_batch(user, reset=reset, page_size=page_size)
            
            # Prepare response
            cumulative = result.get('cumulative') or {}
            summary = {
                'emails_scanned': result.get('emails_scanned', 0),
                'job_related_emails': result.get('job_related_emails', 0),
                'applications_updated': result.get('applications_updated', 0),
                'new_applications': result.get('new_applications', 0),
                'needs_review': result.get('needs_review', 0),
                'status': result.get('status', 'completed'),
                'has_more': result.get('has_more', False),
                'page': result.get('page', 1),
                'cumulative': cumulative,
                'message': 'Batch processed successfully' if not result.get('error') else result.get('error')
            }
            
            serializer = SyncSummarySerializer(summary)
            return Response(serializer.data, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Gmail sync batch failed: {str(e)}")
            return Response(
                {'error': f'Sync failed: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class GmailSyncStatusView(APIView):
    """Get current sync status and progress for the authenticated user."""
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        """Return sync state."""
        try:
            status_data = SyncService.get_sync_status(request.user)
            serializer = SyncStatusResponseSerializer(status_data)
            return Response(serializer.data, status=status.HTTP_200_OK)
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
            
            # Mark as processed
            email.processing_status = 'processed'
            email.save()
            
            # If this email was related to an application, mark it as not needing review
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
            
            # Mark as ignored
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
