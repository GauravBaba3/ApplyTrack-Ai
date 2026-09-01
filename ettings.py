warning: in the working copy of 'scripts/start_web.sh', LF will be replaced by CRLF the next time Git touches it
[1mdiff --git a/backend/apps/accounts/views.py b/backend/apps/accounts/views.py[m
[1mindex 442bbc1..841818e 100644[m
[1m--- a/backend/apps/accounts/views.py[m
[1m+++ b/backend/apps/accounts/views.py[m
[36m@@ -115,9 +115,11 @@[m [mclass GoogleCallbackView(APIView):[m
             code = request.GET.get('code')[m
             raw_state = request.GET.get('state', '')[m
 [m
[32m+[m[32m            default_frontend = 'https://applytrackai.in' if getattr(settings, 'IS_PRODUCTION', False) else 'http://localhost:5174'[m
[32m+[m[32m            frontend_url = os.getenv('FRONTEND_URL', default_frontend).rstrip('/')[m
[32m+[m
             if not code:[m
                 logger.error("OAuth callback missing authorization code")[m
[31m-                frontend_url = os.getenv('FRONTEND_URL', 'http://localhost:5174')[m
                 return redirect(f"{frontend_url}/login?auth=failed&error=missing_code")[m
 [m
             # Try to decode our encoded state payload[m
[36m@@ -135,7 +137,6 @@[m [mclass GoogleCallbackView(APIView):[m
 [m
             if not nonce:[m
                 logger.error("OAuth callback: no valid state found")[m
[31m-                frontend_url = os.getenv('FRONTEND_URL', 'http://localhost:5174')[m
                 return redirect(f"{frontend_url}/login?auth=failed&error=invalid_state")[m
 [m
             # Create a new flow; inject the PKCE verifier we recovered[m
[36m@@ -202,21 +203,23 @@[m [mclass GoogleCallbackView(APIView):[m
             from django.middleware.csrf import get_token[m
             csrf_token = get_token(request)[m
 [m
[31m-            frontend_url = os.getenv('FRONTEND_URL', 'http://localhost:5174')[m
[32m+[m[32m            default_frontend = 'https://applytrackai.in' if getattr(settings, 'IS_PRODUCTION', False) else 'http://localhost:5174'[m
[32m+[m[32m            frontend_url = os.getenv('FRONTEND_URL', default_frontend).rstrip('/')[m
             response = redirect(f"{frontend_url}/dashboard?auth=success")[m
             response.set_cookie([m
                 key='csrftoken',[m
                 value=csrf_token,[m
[31m-                samesite='Lax',[m
[31m-                secure=settings.SESSION_COOKIE_SECURE,[m
[32m+[m[32m                samesite=getattr(settings, 'CSRF_COOKIE_SAMESITE', 'Lax'),[m
[32m+[m[32m                secure=getattr(settings, 'CSRF_COOKIE_SECURE', False),[m
                 httponly=False,[m
[31m-                domain=None[m
[32m+[m[32m                domain=getattr(settings, 'CSRF_COOKIE_DOMAIN', None)[m
             )[m
             return response[m
 [m
         except Exception as e:[m
             logger.error(f"Google OAuth callback failed: {str(e)}", exc_info=True)[m
[31m-            frontend_url = os.getenv('FRONTEND_URL', 'http://localhost:5174')[m
[32m+[m[32m            default_frontend = 'https://applytrackai.in' if getattr(settings, 'IS_PRODUCTION', False) else 'http://localhost:5174'[m
[32m+[m[32m            frontend_url = os.getenv('FRONTEND_URL', default_frontend).rstrip('/')[m
             return redirect(f"{frontend_url}/login?auth=failed&error=oauth_failed")[m
 [m
 [m
[1mdiff --git a/backend/config/settings.py b/backend/config/settings.py[m
[1mindex 9d28c24..3ae18ca 100644[m
[1m--- a/backend/config/settings.py[m
[1m+++ b/backend/config/settings.py[m
[36m@@ -17,16 +17,15 @@[m [mSECRET_KEY = os.getenv('DJANGO_SECRET_KEY', 'django-insecure-default-key-for-dev[m
 # SECURITY WARNING: don't run with debug turned on in production![m
 DEBUG = os.getenv('DEBUG', 'True').lower() == 'true'[m
 [m
[31m-# ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')[m
[31m-[m
[31m-ALLOWED_HOSTS = [[m
[31m-    host.strip()[m
[31m-    for host in os.getenv([m
[31m-        "ALLOWED_HOSTS",[m
[31m-        "localhost,127.0.0.1"[m
[31m-    ).split(",")[m
[31m-    if host.strip()[m
[32m+[m[32m_default_hosts = [[m
[32m+[m[32m    "localhost",[m
[32m+[m[32m    "127.0.0.1",[m
[32m+[m[32m    "applytrackai.i