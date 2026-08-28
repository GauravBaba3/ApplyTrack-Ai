"""
URL configuration for ApplyTrack AI project.
"""
from django.contrib import admin
from django.urls import path, include

from django.http import JsonResponse
from django.urls import path

def health_check(request):
    return JsonResponse({"status": "ok"})

urlpatterns = [
    path('admin/', admin.site.urls),
    path("health/", health_check),
    path('api/auth/', include('apps.accounts.urls')),
    path('api/applications/', include('apps.applications.urls')),
    path('api/emails/', include('apps.gmail_integration.urls')),
    path('api/analytics/', include('apps.analytics.urls')),
    path('api/gmail/', include('apps.gmail_integration.gmail_urls')),
]
