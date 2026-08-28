"""
URLs for accounts app.
"""
from django.urls import path
from .views import (
    GoogleLoginView,
    GoogleCallbackView,
    UserMeView,
    LogoutView,
    DisconnectGmailView,
    SettingsView,
    CsrfTokenView,
)

urlpatterns = [
    path('google/', GoogleLoginView.as_view(), name='google-login'),
    path('google/callback/', GoogleCallbackView.as_view(), name='google-callback'),
    path('me/', UserMeView.as_view(), name='user-me'),
    path('csrf/', CsrfTokenView.as_view(), name='csrf-token'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('disconnect-gmail/', DisconnectGmailView.as_view(), name='disconnect-gmail'),
    path('settings/', SettingsView.as_view(), name='user-settings'),
]
