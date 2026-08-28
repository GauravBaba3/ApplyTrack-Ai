"""
Views for accounts app - Google OAuth and user management.
"""
import logging
import os
import json
import base64
import secrets
from django.shortcuts import redirect
from django.conf import settings
from django.contrib.auth import login, logout
from django.utils import timezone
from rest_framework import status, generics
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from google.oauth2 import id_token
from google_auth_oauthlib.flow import Flow
from google.auth.transport import requests as google_requests

from .models import CustomUser, UserSettings
from .serializers import UserSerializer, UserSettingsSerializer

# Allow OAuth over HTTP in local development
os.environ.setdefault('OAUTHLIB_INSECURE_TRANSPORT', '1')
# Relax token scope comparison (Google may reorder/expand scopes)
os.environ.setdefault('OAUTHLIB_RELAX_TOKEN_SCOPE', '1')

logger = logging.getLogger(__name__)


# Define the scopes for Gmail read-only access
SCOPES = [
    'openid',
    'email',
    'profile',
    'https://www.googleapis.com/auth/gmail.readonly',
]


def get_google_flow():
    """Create and return a Google OAuth Flow object using environment variables."""
    client_config = {
        "web": {
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "redirect_uris": [settings.GOOGLE_REDIRECT_URI],
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
        }
    }
    return Flow.from_client_config(
        client_config=client_config,
        scopes=SCOPES,
        redirect_uri=settings.GOOGLE_REDIRECT_URI
    )


class GoogleLoginView(APIView):
    """Initiate Google OAuth flow."""
    permission_classes = [AllowAny]

    def get(self, request):
        """Redirect to Google for authentication."""
        try:
            flow = get_google_flow()

            # Generate a random nonce to use as the real OAuth state
            nonce = secrets.token_urlsafe(24)

            # Generate authorization URL — this also generates the PKCE verifier
            authorization_url, _ = flow.authorization_url(
                access_type='offline',
                include_granted_scopes='true',
                prompt='consent',
                state=nonce,
            )

            # Encode nonce + code_verifier into the state parameter so it
            # survives the cross-domain redirect (session cookie is not sent
            # back on the Google callback due to SameSite=Lax).
            code_verifier = getattr(flow, 'code_verifier', None)
            payload = {'nonce': nonce, 'cv': code_verifier}
            encoded_state = base64.urlsafe_b64encode(
                json.dumps(payload).encode()
            ).decode()

            # Rebuild the authorization URL replacing the state with our encoded payload
            authorization_url = authorization_url.replace(
                f'state={nonce}', f'state={encoded_state}'
            )

            # Also store in session as a fallback
            request.session['oauth_state'] = nonce
            if code_verifier:
                request.session['oauth_code_verifier'] = code_verifier
            request.session.save()

            return redirect(authorization_url)
        except Exception as e:
            logger.error(f"Google OAuth initialization failed: {str(e)}")
            return Response(
                {'error': 'Failed to initialize Google OAuth'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class GoogleCallbackView(APIView):
    """Handle Google OAuth callback."""
    permission_classes = [AllowAny]

    def get(self, request):
        """Exchange authorization code for tokens and authenticate user."""
        try:
            code = request.GET.get('code')
            raw_state = request.GET.get('state', '')

            if not code:
                logger.error("OAuth callback missing authorization code")
                frontend_url = os.getenv('FRONTEND_URL', 'http://localhost:5174')
                return redirect(f"{frontend_url}/login?auth=failed&error=missing_code")

            # Try to decode our encoded state payload
            code_verifier = None
            nonce = None
            try:
                payload = json.loads(base64.urlsafe_b64decode(raw_state.encode()).decode())
                nonce = payload.get('nonce')
                code_verifier = payload.get('cv')
            except Exception:
                # Fallback to session if state is not our encoded format
                nonce = request.session.get('oauth_state')
                code_verifier = request.session.get('oauth_code_verifier')
                logger.warning("Could not decode state payload, falling back to session")

            if not nonce:
                logger.error("OAuth callback: no valid state found")
                frontend_url = os.getenv('FRONTEND_URL', 'http://localhost:5174')
                return redirect(f"{frontend_url}/login?auth=failed&error=invalid_state")

            # Create a new flow; inject the PKCE verifier we recovered
            flow = get_google_flow()
            if code_verifier:
                flow.code_verifier = code_verifier

            # Build the full authorization response URL so requests-oauthlib
            # can extract all parameters correctly
            authorization_response = request.build_absolute_uri()
            # Replace encoded state back so the library can validate it
            # (pass nonce as the expected state)
            flow.fetch_token(
                authorization_response=authorization_response,
                state=nonce,
            )

            # Clean up session
            for key in ('oauth_state', 'oauth_code_verifier'):
                request.session.pop(key, None)
            request.session.modified = True

            # Verify ID token
            credentials = flow.credentials
            id_info = id_token.verify_oauth2_token(
                credentials.id_token,
                google_requests.Request(),
                settings.GOOGLE_CLIENT_ID
            )

            email = id_info.get('email')
            first_name = id_info.get('given_name', '')
            last_name = id_info.get('family_name', '')

            user, created = CustomUser.objects.get_or_create(
                email=email,
                defaults={
                    'username': email,
                    'first_name': first_name,
                    'last_name': last_name,
                    'gmail_connected': True,
                    'gmail_access_token': credentials.token,
                    'gmail_refresh_token': credentials.refresh_token,
                    'gmail_token_expiry': credentials.expiry.replace(tzinfo=timezone.utc) if credentials.expiry else None,
                    'gmail_last_sync': timezone.now()
                }
            )

            if not created:
                user.first_name = first_name or user.first_name
                user.last_name = last_name or user.last_name
                user.gmail_connected = True
                user.gmail_access_token = credentials.token
                user.gmail_refresh_token = credentials.refresh_token
                user.gmail_token_expiry = credentials.expiry.replace(tzinfo=timezone.utc) if credentials.expiry else None
                user.gmail_last_sync = timezone.now()
                user.save()

            UserSettings.objects.get_or_create(
                user=user,
                defaults={'notifications_enabled': True, 'sync_frequency': 'manual'}
            )

            login(request, user)
            from django.middleware.csrf import get_token
            csrf_token = get_token(request)

            frontend_url = os.getenv('FRONTEND_URL', 'http://localhost:5174')
            response = redirect(f"{frontend_url}/dashboard?auth=success")
            response.set_cookie(
                key='csrftoken',
                value=csrf_token,
                samesite='Lax',
                secure=settings.SESSION_COOKIE_SECURE,
                httponly=False,
                domain=None
            )
            return response

        except Exception as e:
            logger.error(f"Google OAuth callback failed: {str(e)}", exc_info=True)
            frontend_url = os.getenv('FRONTEND_URL', 'http://localhost:5174')
            return redirect(f"{frontend_url}/login?auth=failed&error=oauth_failed")


from django.views.decorators.csrf import ensure_csrf_cookie
from django.utils.decorators import method_decorator


class CsrfTokenView(APIView):
    """Return CSRF token for cross-origin SPA requests."""
    permission_classes = [AllowAny]

    @method_decorator(ensure_csrf_cookie)
    def get(self, request):
        from django.middleware.csrf import get_token
        return Response({'csrfToken': get_token(request)})


@method_decorator(ensure_csrf_cookie, name='dispatch')
class UserMeView(generics.RetrieveAPIView):
    """Get current user information."""
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]
    
    def get_object(self):
        return self.request.user


class LogoutView(APIView):
    """Logout user."""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """Logout the current user."""
        try:
            # Clear Gmail tokens
            user = request.user
            user.gmail_connected = False
            user.gmail_access_token = None
            user.gmail_refresh_token = None
            user.gmail_token_expiry = None
            user.save()
            
            logout(request)
            return Response({'message': 'Successfully logged out'})
        except Exception as e:
            logger.error(f"Logout failed: {str(e)}")
            return Response(
                {'error': 'Logout failed'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class DisconnectGmailView(APIView):
    """Disconnect Gmail from user account."""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """Disconnect Gmail integration."""
        try:
            user = request.user
            user.gmail_connected = False
            user.gmail_access_token = None
            user.gmail_refresh_token = None
            user.gmail_token_expiry = None
            user.save()
            
            return Response({'message': 'Gmail disconnected successfully'})
        except Exception as e:
            logger.error(f"Gmail disconnect failed: {str(e)}")
            return Response(
                {'error': 'Failed to disconnect Gmail'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class SettingsView(generics.RetrieveUpdateAPIView):
    """Get and update user settings."""
    serializer_class = UserSettingsSerializer
    permission_classes = [IsAuthenticated]
    
    def get_object(self):
        user = self.request.user
        settings, created = UserSettings.objects.get_or_create(
            user=user,
            defaults={'notifications_enabled': True, 'sync_frequency': 'manual'}
        )
        return settings
