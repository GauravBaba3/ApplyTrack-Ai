"""
Views for applications app.
"""
import logging
from django.utils import timezone
from datetime import timedelta
from rest_framework import status, generics, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db.models import Count, Q

from .models import Application, StatusHistory, FollowUp, ApplicationStatus
from .serializers import (
    ApplicationSerializer,
    ApplicationDetailSerializer,
    StatusHistorySerializer,
    FollowUpSerializer,
    ApplicationStatsSerializer,
    ApplicationCreateSerializer
)

logger = logging.getLogger(__name__)


class ApplicationListCreateView(generics.ListCreateAPIView):
    """List and create applications."""
    serializer_class = ApplicationSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        queryset = Application.objects.filter(user=user)
        
        # Filter by status
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(current_status=status_filter)
        
        # Filter by company
        company_filter = self.request.query_params.get('company')
        if company_filter:
            queryset = queryset.filter(company__icontains=company_filter)
        
        # Filter by needs_review
        needs_review = self.request.query_params.get('needs_review')
        if needs_review == 'true':
            queryset = queryset.filter(needs_review=True)
        
        # Ordering
        ordering = self.request.query_params.get('ordering', '-application_date')
        queryset = queryset.order_by(ordering)
        
        return queryset
    
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return ApplicationCreateSerializer
        return ApplicationSerializer
    
    def perform_create(self, serializer):
        serializer.save(
            user=self.request.user,
            is_manual=True,
            is_ai_detected=False,
            needs_review=False
        )


class ApplicationRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update, or delete a specific application."""
    serializer_class = ApplicationDetailSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'id'
    
    def get_queryset(self):
        return Application.objects.filter(user=self.request.user)
    
    def perform_update(self, serializer):
        # Mark as user-modified
        if not serializer.instance.is_manual:
            serializer.save(is_manual=True)
        else:
            serializer.save()


class ApplicationStatsView(APIView):
    """Get application statistics."""
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        user = request.user
        
        # Get all applications
        applications = Application.objects.filter(user=user)
        
        # Count by status
        status_counts = applications.values('current_status').annotate(
            count=Count('id')
        )
        
        # Build status dictionary
        status_dict = {item['current_status']: item['count'] for item in status_counts}
        
        # Calculate stale applications (no activity for threshold days)
        stale_threshold = user.stale_application_threshold
        stale_date = timezone.now() - timedelta(days=stale_threshold)
        stale_count = applications.filter(
            last_activity_date__lt=stale_date,
            current_status__in=[
                ApplicationStatus.APPLIED,
                ApplicationStatus.ASSESSMENT,
                ApplicationStatus.PENDING,
                ApplicationStatus.NO_RESPONSE
            ]
        ).count()
        
        # Count needs review
        needs_review_count = applications.filter(needs_review=True).count()
        
        # Build response
        data = {
            'total_applications': applications.count(),
            'applied': status_dict.get(ApplicationStatus.APPLIED, 0),
            'assessment': status_dict.get(ApplicationStatus.ASSESSMENT, 0),
            'interview': status_dict.get(ApplicationStatus.INTERVIEW, 0),
            'offer': status_dict.get(ApplicationStatus.OFFER, 0),
            'rejected': status_dict.get(ApplicationStatus.REJECTED, 0),
            'no_response': status_dict.get(ApplicationStatus.NO_RESPONSE, 0),
            'stale': stale_count,
            'needs_review': needs_review_count
        }
        
        serializer = ApplicationStatsSerializer(data)
        return Response(serializer.data)


class StatusHistoryListView(generics.ListAPIView):
    """List status history for an application."""
    serializer_class = StatusHistorySerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        application_id = self.kwargs.get('application_id')
        user = self.request.user
        return StatusHistory.objects.filter(
            application__user=user,
            application_id=application_id
        ).order_by('-timestamp')


class FollowUpListCreateView(generics.ListCreateAPIView):
    """List and create follow-ups for an application."""
    serializer_class = FollowUpSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        application_id = self.kwargs.get('application_id')
        user = self.request.user
        return FollowUp.objects.filter(
            application__user=user,
            application_id=application_id
        ).order_by('-created_at')
    
    def perform_create(self, serializer):
        application_id = self.kwargs.get('application_id')
        application = Application.objects.get(id=application_id, user=self.request.user)
        serializer.save(application=application)


class FollowUpDraftView(APIView):
    """Generate a follow-up draft for an application."""
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request, application_id):
        """Generate a follow-up draft using AI."""
        try:
            from services.groq_service import GroqService
            
            application = Application.objects.get(
                id=application_id,
                user=request.user
            )
            
            # Generate draft
            draft = GroqService.generate_followup_draft(application)
            
            # Create follow-up record
            followup = FollowUp.objects.create(
                application=application,
                draft_subject=draft.get('subject', ''),
                draft_body=draft.get('body', '')
            )
            
            serializer = FollowUpSerializer(followup)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
            
        except Application.DoesNotExist:
            return Response(
                {'error': 'Application not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Failed to generate follow-up draft: {str(e)}")
            return Response(
                {'error': 'Failed to generate follow-up draft'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
