"""
Views for analytics app.
"""
import logging
from django.utils import timezone
from datetime import timedelta
from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.applications.models import Application, ApplicationStatus
from .models import UserAnalytics
from .serializers import UserAnalyticsSerializer

logger = logging.getLogger(__name__)


class AnalyticsView(APIView):
    """Get user analytics data."""
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        """Calculate and return analytics for the current user."""
        try:
            user = request.user
            
            # Get all applications
            applications = Application.objects.filter(user=user)
            
            # Calculate metrics
            total_applications = applications.count()
            
            # Applications this month
            this_month = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            applications_this_month = applications.filter(
                application_date__gte=this_month
            ).count()
            
            # Calculate rates
            total_with_response = applications.exclude(
                current_status__in=[ApplicationStatus.NO_RESPONSE, ApplicationStatus.GHOSTED]
            ).count()
            
            interview_count = applications.filter(
                current_status=ApplicationStatus.INTERVIEW
            ).count()
            offer_count = applications.filter(
                current_status=ApplicationStatus.OFFER
            ).count()
            rejection_count = applications.filter(
                current_status=ApplicationStatus.REJECTED
            ).count()
            
            response_rate = (total_with_response / total_applications * 100) if total_applications > 0 else 0
            interview_rate = (interview_count / total_applications * 100) if total_applications > 0 else 0
            offer_rate = (offer_count / total_applications * 100) if total_applications > 0 else 0
            rejection_rate = (rejection_count / total_applications * 100) if total_applications > 0 else 0
            
            # Calculate average days to response
            avg_days = 0
            response_dates = []
            from datetime import datetime
            for app in applications.exclude(last_activity_date__isnull=True):
                # application_date is a DateField; convert to aware datetime for comparison
                app_date_aware = timezone.make_aware(
                    datetime.combine(app.application_date, datetime.min.time())
                )
                if app.last_activity_date > app_date_aware:
                    days = (app.last_activity_date - app_date_aware).days
                    response_dates.append(days)
            
            if response_dates:
                avg_days = sum(response_dates) / len(response_dates)
            
            # Build response
            data = {
                'total_applications': total_applications,
                'applications_this_month': applications_this_month,
                'interview_rate': round(interview_rate, 2),
                'response_rate': round(response_rate, 2),
                'offer_rate': round(offer_rate, 2),
                'rejection_rate': round(rejection_rate, 2),
                'avg_days_to_response': round(avg_days, 1)
            }
            
            # Update or create analytics record
            UserAnalytics.objects.update_or_create(
                user=user,
                defaults=data
            )
            
            serializer = UserAnalyticsSerializer(data)
            return Response(serializer.data)
            
        except Exception as e:
            logger.error(f"Failed to calculate analytics: {str(e)}")
            return Response(
                {'error': 'Failed to calculate analytics'},
                status=500
            )
