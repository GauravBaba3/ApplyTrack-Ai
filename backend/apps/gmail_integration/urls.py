"""
URLs for gmail_integration app - mounted at /api/emails/
"""
from django.urls import path
from .views import (
    ProcessedEmailListView,
    ProcessedEmailDetailView,
    SyncLogListView,
    MarkEmailReviewedView,
    IgnoreEmailView
)

urlpatterns = [
    path('', ProcessedEmailListView.as_view(), name='processed-email-list'),
    path('sync-logs/', SyncLogListView.as_view(), name='sync-log-list'),
    path('<int:id>/', ProcessedEmailDetailView.as_view(), name='processed-email-detail'),
    path('<int:email_id>/review/', MarkEmailReviewedView.as_view(), name='mark-email-reviewed'),
    path('<int:email_id>/ignore/', IgnoreEmailView.as_view(), name='ignore-email'),
]
