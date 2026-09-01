"""
Dual-mode Authentication Classes for ApplyTrack AI.
Supports both standard cookie-based Django sessions and cross-domain Header sessions.
"""
import logging
from importlib import import_module
from django.conf import settings
from django.contrib.auth import get_user_model, SESSION_KEY, BACKEND_SESSION_KEY, load_backend
from rest_framework.authentication import BaseAuthentication, SessionAuthentication

logger = logging.getLogger(__name__)


class HeaderSessionAuthentication(BaseAuthentication):
    """
    Authenticate against Django's active session store using an Authorization or X-Session-ID header.
    Solves cross-domain third-party cookie blocking across separate origins (e.g. applytrackai.in -> render.com).
    """

    def authenticate(self, request):
        auth_header = request.headers.get('Authorization') or request.META.get('HTTP_AUTHORIZATION')
        session_header = request.headers.get('X-Session-ID') or request.META.get('HTTP_X_SESSION_ID')

        session_key = None

        if auth_header:
            parts = auth_header.split()
            if len(parts) == 2 and parts[0].lower() in ('bearer', 'session', 'token'):
                session_key = parts[1].strip()
            elif len(parts) == 1:
                session_key = parts[0].strip()

        if not session_key and session_header:
            session_key = session_header.strip()

        if not session_key:
            return None

        # Load session from Django's configured session engine
        engine = import_module(settings.SESSION_ENGINE)
        session = engine.SessionStore(session_key=session_key)

        if not session.exists(session_key):
            return None

        user_id = session.get(SESSION_KEY)
        if not user_id:
            return None

        User = get_user_model()
        try:
            user = User.objects.get(pk=user_id, is_active=True)
        except User.DoesNotExist:
            return None

        # Attach active session to request for downstream handlers
        request.session = session
        return (user, None)
