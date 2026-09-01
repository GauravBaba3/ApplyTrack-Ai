"""
URLs for applications app in ApplyTrack AI.
"""
from django.urls import path
from .views import (
    ApplicationListCreateView,
    ApplicationRetrieveUpdateDestroyView,
    ApplicationStatsView,
    StatusHistoryListView,
    FollowUpListCreateView,
    FollowUpDraftView,
    ConfirmReviewView,
    EditReviewView,
    IgnoreReviewView,
    SyncSummaryView
)

urlpatterns = [
    path('', ApplicationListCreateView.as_view(), name='application-list'),
    path('<int:id>/', ApplicationRetrieveUpdateDestroyView.as_view(), name='application-detail'),
    path('stats/', ApplicationStatsView.as_view(), name='application-stats'),
    path('sync-summary/', SyncSummaryView.as_view(), name='sync-summary'),
    path('<int:id>/confirm-review/', ConfirmReviewView.as_view(), name='confirm-review'),
    path('<int:id>/edit-review/', EditReviewView.as_view(), name='edit-review'),
    path('<int:id>/ignore-review/', IgnoreReviewView.as_view(), name='ignore-review'),
    path('<int:application_id>/history/', StatusHistoryListView.as_view(), name='status-history'),
    path('<int:application_id>/followups/', FollowUpListCreateView.as_view(), name='followup-list'),
    path('<int:application_id>/followups/draft/', FollowUpDraftView.as_view(), name='followup-draft'),
]
