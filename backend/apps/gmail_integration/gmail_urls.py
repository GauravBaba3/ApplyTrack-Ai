"""
URLs for /api/gmail/ endpoint.
"""
from django.urls import path
from .views import GmailSyncView, GmailSyncStatusView, GmailSyncStartView

urlpatterns = [
    path('sync/', GmailSyncView.as_view(), name='gmail-sync-api'),
    path('sync/start/', GmailSyncStartView.as_view(), name='gmail-sync-start'),
    path('sync/status/', GmailSyncStatusView.as_view(), name='gmail-sync-status'),
]
