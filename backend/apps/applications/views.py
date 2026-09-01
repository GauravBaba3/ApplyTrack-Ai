"""
Views for applications app in ApplyTrack AI.

Provides REST API endpoints for:
- Application listing, search, filtering, and manual creation
- Detailed application views with history and timeline
- Dashboard statistics and metrics
- Needs Review queue confirmation, editing, and ignoring
- Staleness auditing and follow-up draft generation
- Gmail sync summary statistics
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
from services.staleness_service import StalenessService
from apps.gmail_integration.models import ProcessedEmail, EmailProcessingJob, JobStatus, ProcessingStatus

logger = logging.getLogger(__name__)


class ApplicationListCreateView(generics.ListCreateAPIView):
    """List and create applications with search and multi-field filtering."""
    serializer_class = ApplicationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        queryset = Application.objects.filter(user=user)

        # Filter by status
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(current_status=status_filter)

        # Search by company or role
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(company__icontains=search) | Q(job_title__icontains=search)
            )

        # Filter by company
        company_filter = self.request.query_params.get('company')
        if company_filter:
            queryset = queryset.filter(company__icontains=company_filter)

        # Filter by source
        source_filter = self.request.query_params.get('source')
        if source_filter:
            queryset = queryset.filter(source=source_filter)

        # Filter by needs_review
        needs_review = self.request.query_params.get('needs_review')
        if needs_review == 'true':
            queryset = queryset.filter(needs_review=True)
        elif needs_review == 'false':
            queryset = queryset.filter(needs_review=False)

        # Date range filters
        date_from = self.request.query_params.get('date_from')
        if date_from:
            queryset = queryset.filter(application_date__gte=date_from)
        date_to = self.request.query_params.get('date_to')
        if date_to:
            queryset = queryset.filter(application_date__lte=date_to)

        # Ordering
        ordering = self.request.query_params.get('ordering', '-application_date')
        return queryset.order_by(ordering)

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return ApplicationCreateSerializer
        return ApplicationSerializer

    def perform_create(self, serializer):
        app = serializer.save(
            user=self.request.user,
            is_manual=True,
            is_ai_detected=False,
            needs_review=False,
            last_activity_date=timezone.now()
        )
        # Create initial status history entry
        StatusHistory.objects.create(
            application=app,
            previous_status=None,
            new_status=app.current_status,
            source='manual',
            confidence=1.0,
            evidence='Manually created by user'
        )


class ApplicationRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update, or delete a specific application."""
    serializer_class = ApplicationDetailSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'id'

    def get_queryset(self):
        return Application.objects.filter(user=self.request.user)

    def perform_update(self, serializer):
        old_status = serializer.instance.current_status
        new_status = serializer.validated_data.get('current_status', old_status)
        instance = serializer.save(is_manual=True, last_activity_date=timezone.now())

        if old_status != new_status:
            StatusHistory.objects.create(
                application=instance,
                previous_status=old_status,
                new_status=new_status,
                source='manual',
                confidence=1.0,
                evidence='Status updated manually by user'
            )


class ApplicationStatsView(APIView):
    """Get aggregate dashboard statistics."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        applications = Application.objects.filter(user=user)

        status_counts = applications.values('current_status').annotate(count=Count('id'))
        status_dict = {item['current_status']: item['count'] for item in status_counts}

        # Calculate stale applications (no activity for >= 7 days)
        stale_threshold_days = getattr(user, 'stale_application_threshold', 7)
        stale_date = timezone.now() - timedelta(days=stale_threshold_days)
        stale_count = applications.filter(
            last_activity_date__lt=stale_date,
            current_status__in=[
                ApplicationStatus.APPLIED,
                ApplicationStatus.UNDER_REVIEW,
                ApplicationStatus.ASSESSMENT,
                ApplicationStatus.NO_RESPONSE
            ]
        ).count()

        needs_review_count = applications.filter(needs_review=True).count()

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
    """List status history audit timeline for an application."""
    serializer_class = StatusHistorySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        application_id = self.kwargs.get('application_id')
        return StatusHistory.objects.filter(
            application__user=self.request.user,
            application_id=application_id
        ).order_by('-timestamp')


class FollowUpListCreateView(generics.ListCreateAPIView):
    """List and create follow-up drafts for an application."""
    serializer_class = FollowUpSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        application_id = self.kwargs.get('application_id')
        return FollowUp.objects.filter(
            application__user=self.request.user,
            application_id=application_id
        ).order_by('-created_at')

    def perform_create(self, serializer):
        application_id = self.kwargs.get('application_id')
        application = Application.objects.get(id=application_id, user=self.request.user)
        serializer.save(application=application)


class FollowUpDraftView(APIView):
    """Generate or retrieve a contextual follow-up draft."""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, id=None, application_id=None):
        app_id = id or application_id
        try:
            application = Application.objects.get(id=app_id, user=request.user)
            followup = StalenessService.generate_follow_up_draft(application)
            serializer = FollowUpSerializer(followup)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except Application.DoesNotExist:
            return Response({'error': 'Application not found'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Failed to generate follow-up: {str(e)}")
            return Response({'error': 'Failed to generate follow-up'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ConfirmReviewView(APIView):
    """Confirm a detected application in the Needs Review queue."""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, id=None, application_id=None):
        app_id = id or application_id
        try:
            app = Application.objects.get(id=app_id, user=request.user)
            app.needs_review = False
            app.review_reason = None
            app.confidence = 1.0
            app.save(update_fields=['needs_review', 'review_reason', 'confidence', 'updated_at'])

            StatusHistory.objects.create(
                application=app,
                previous_status=app.current_status,
                new_status=app.current_status,
                source='user_review_confirmed',
                confidence=1.0,
                evidence='User confirmed detected status'
            )

            return Response({'status': 'confirmed', 'application_id': app.id})
        except Application.DoesNotExist:
            return Response({'error': 'Application not found'}, status=status.HTTP_404_NOT_FOUND)


class EditReviewView(APIView):
    """Edit application details and approve from Needs Review queue."""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, id=None, application_id=None):
        app_id = id or application_id
        try:
            app = Application.objects.get(id=app_id, user=request.user)
            company = request.data.get('company', app.company)
            job_title = request.data.get('job_title', app.job_title)
            new_status_str = request.data.get('status', app.current_status)

            old_status = app.current_status
            app.company = company
            app.job_title = job_title
            app.current_status = new_status_str
            app.needs_review = False
            app.is_manual = True
            app.review_reason = None
            app.confidence = 1.0
            app.save()

            StatusHistory.objects.create(
                application=app,
                previous_status=old_status,
                new_status=new_status_str,
                source='user_review_edited',
                confidence=1.0,
                evidence=f"User edited details from review queue"
            )

            return Response({'status': 'updated', 'application': ApplicationSerializer(app).data})
        except Application.DoesNotExist:
            return Response({'error': 'Application not found'}, status=status.HTTP_404_NOT_FOUND)


class IgnoreReviewView(APIView):
    """Ignore or dismiss an item in the Needs Review queue."""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, id=None, application_id=None):
        app_id = id or application_id
        try:
            app = Application.objects.get(id=app_id, user=request.user)
            # Delete false positive application created during review queue
            deleted_id = app.id
            app.delete()
            return Response({'status': 'ignored', 'deleted_application_id': deleted_id})
        except Application.DoesNotExist:
            return Response({'error': 'Application not found'}, status=status.HTTP_404_NOT_FOUND)


class SyncSummaryView(APIView):
    """Get high-level Gmail sync and ingestion summary metrics."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        emails = ProcessedEmail.objects.filter(user=user)
        jobs = EmailProcessingJob.objects.filter(user=user)
        apps = Application.objects.filter(user=user)

        total_scanned = emails.count()
        job_related = emails.filter(is_job_related=True).count()
        needs_review = apps.filter(needs_review=True).count() + emails.filter(processing_status=ProcessingStatus.NEEDS_REVIEW).count()
        failed_processing = jobs.filter(status=JobStatus.DEAD_LETTER).count()
        apps_updated = StatusHistory.objects.filter(application__user=user, source__in=['ai', 'rule_engine', 'email_worker']).count()
        new_apps = apps.filter(is_ai_detected=True).count()

        return Response({
            'emails_scanned': total_scanned,
            'job_related': job_related,
            'applications_updated': apps_updated,
            'new_applications': new_apps,
            'needs_review': needs_review,
            'failed_processing': failed_processing,
        })
