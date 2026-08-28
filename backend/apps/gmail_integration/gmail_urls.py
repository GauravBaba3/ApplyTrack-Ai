"""
URLs for /api/gmail/ endpoint.
"""
from django.urls import path
from .views import GmailSyncView, GmailSyncStatusView

urlpatterns = [
    path('sync/', GmailSyncView.as_view(), name='gmail-sync-api'),
    path('sync/status/', GmailSyncStatusView.as_view(), name='gmail-sync-status'),
]
