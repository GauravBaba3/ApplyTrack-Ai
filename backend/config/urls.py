"""
URL configuration for ApplyTrack AI project.
"""
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/auth/', include('apps.accounts.urls')),
    path('api/applications/', include('apps.applications.urls')),
    path('api/emails/', include('apps.gmail_integration.urls')),
    path('api/analytics/', include('apps.analytics.urls')),
    path('api/gmail/', include('apps.gmail_integration.gmail_urls')),
]
