"""
URLs for applications app.
"""
from django.urls import path
from .views import (
    ApplicationListCreateView,
    ApplicationRetrieveUpdateDestroyView,
    ApplicationStatsView,
    StatusHistoryListView,
    FollowUpListCreateView,
    FollowUpDraftView
)

urlpatterns = [
    path('', ApplicationListCreateView.as_view(), name='application-list'),
    path('<int:id>/', ApplicationRetrieveUpdateDestroyView.as_view(), name='application-detail'),
    path('stats/', ApplicationStatsView.as_view(), name='application-stats'),
    path('<int:application_id>/history/', StatusHistoryListView.as_view(), name='status-history'),
    path('<int:application_id>/followups/', FollowUpListCreateView.as_view(), name='followup-list'),
    path('<int:application_id>/followups/draft/', FollowUpDraftView.as_view(), name='followup-draft'),
]
