"""
Django settings for ApplyTrack AI project.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Load environment variables robustly
load_dotenv(dotenv_path=BASE_DIR / '.env')

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv('DJANGO_SECRET_KEY', 'django-insecure-default-key-for-dev')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.getenv('DEBUG', 'True').lower() == 'true'

_default_hosts = [
    "localhost",
    "127.0.0.1",
    "applytrackai.in",
    "www.applytrackai.in",
    ".onrender.com",
]
_env_hosts = [h.strip() for h in os.getenv("ALLOWED_HOSTS", "").split(",") if h.strip()]
ALLOWED_HOSTS = list(set(_env_hosts + _default_hosts))


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # Third-party apps
    'rest_framework',
    'corsheaders',
    
    # Local apps - order matters for dependencies
    'apps.accounts',
    'apps.gmail_integration',
    'apps.applications',
    'apps.ai_processing',
    'apps.analytics',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'
ASGI_APPLICATION = 'config.asgi.application'


# Database
# https://docs.djangoproject.com/en/4.2/ref/settings/#databases

import sys
import dj_database_url

if 'test' in sys.argv or 'pytest' in sys.argv:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': ':memory:',
        }
    }
else:
    DATABASES = {
        'default': dj_database_url.parse(os.getenv('DATABASE_URL', 'sqlite:///db.sqlite3'))
    }


# Password validation
# https://docs.djangoproject.com/en/4.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/4.2/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'Asia/Calcutta'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/4.2/howto/static-files/

STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'


# Default primary key field type
# https://docs.djangoproject.com/en/4.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


# Custom user model
AUTH_USER_MODEL = 'accounts.CustomUser'


# Django REST Framework
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
}


# CORS Configuration
CORS_ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.getenv(
        "CORS_ALLOWED_ORIGINS",
        "http://localhost:5173,http://localhost:5174,http://127.0.0.1:5173,http://127.0.0.1:5174"
    ).split(",")
    if origin.strip()
]
CORS_ALLOW_CREDENTIALS = True
# CSRF_TRUSTED_ORIGINS = [
#     origin.strip()
#     for origin in os.getenv(
#         "CORS_ALLOWED_ORIGINS",
#         "http://localhost:5173,http://localhost:5174,http://127.0.0.1:5173,http://127.0.0.1:5174"
#     ).split(",")
#     if origin.strip()
# ]

# CORS & CSRF Configuration
_default_dev_origins = [
    "http://localhost:5173",
    "http://localhost:5174",
    "http://localhost:3000",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:5174",
    "http://127.0.0.1:3000",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
]

_default_prod_origins = [
    "https://applytrackai.in",
    "https://www.applytrackai.in",
]

_frontend_url = os.getenv("FRONTEND_URL", "").strip().rstrip("/")
_extra_origins = [_frontend_url] if _frontend_url else []

_env_cors = [o.strip().rstrip("/") for o in os.getenv("CORS_ALLOWED_ORIGINS", "").split(",") if o.strip()]
CORS_ALLOWED_ORIGINS = list(set(_env_cors + _default_prod_origins + _extra_origins + (_default_dev_origins if DEBUG else [])))
CORS_ALLOW_CREDENTIALS = True

_env_csrf = [o.strip().rstrip("/") for o in os.getenv("CSRF_TRUSTED_ORIGINS", "").split(",") if o.strip()]
CSRF_TRUSTED_ORIGINS = list(set(_env_csrf + _default_prod_origins + _extra_origins + (_default_dev_origins if DEBUG else [])))

# CSRF and Session Cookie Settings
CSRF_COOKIE_HTTPONLY = False
CSRF_COOKIE_NAME = 'csrftoken'

IS_PRODUCTION = not DEBUG or os.getenv('DJANGO_ENV', '').lower() == 'production'

# In development over HTTP: SameSite='Lax', Secure=False.
# In production over HTTPS: SameSite='None', Secure=True.
CSRF_COOKIE_SAMESITE = 'None' if IS_PRODUCTION else 'Lax'
SESSION_COOKIE_SAMESITE = 'None' if IS_PRODUCTION else 'Lax'

CSRF_COOKIE_SECURE = IS_PRODUCTION
SESSION_COOKIE_SECURE = IS_PRODUCTION
SESSION_COOKIE_HTTPONLY = True

# Production HTTPS / proxy
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")


# Google OAuth Configuration
GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID', '')
GOOGLE_CLIENT_SECRET = os.getenv('GOOGLE_CLIENT_SECRET', '')
GOOGLE_REDIRECT_URI = os.getenv('GOOGLE_REDIRECT_URI', 'http://localhost:8000/api/auth/google/callback/')


# Groq API Configuration
GROQ_API_KEY = os.getenv('GROQ_API_KEY', '')


# Logging configuration
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': os.getenv('DJANGO_LOG_LEVEL', 'INFO'),
            'propagate': False,
        },
    },
}


# Backblaze B2 Cloud Object Storage Configuration (S3-Compatible)
B2_KEY_ID = os.getenv('B2_KEY_ID', os.getenv('R2_ACCESS_KEY_ID', ''))
B2_APPLICATION_KEY = os.getenv('B2_APPLICATION_KEY', os.getenv('R2_SECRET_ACCESS_KEY', ''))
B2_BUCKET_NAME = os.getenv('B2_BUCKET_NAME', 'applytrack-ai-emails')
B2_ENDPOINT_URL = os.getenv('B2_ENDPOINT_URL', os.getenv('R2_ENDPOINT_URL', ''))
B2_REGION = os.getenv('B2_REGION', 'us-east-005')

# Backward compatibility aliases for legacy R2 settings
R2_ACCESS_KEY_ID = B2_KEY_ID
R2_SECRET_ACCESS_KEY = B2_APPLICATION_KEY
R2_BUCKET_NAME = B2_BUCKET_NAME
R2_ENDPOINT_URL = B2_ENDPOINT_URL
R2_ACCOUNT_ID = os.getenv('R2_ACCOUNT_ID', '')

# AI Pipeline Configuration (Phase 5: Multi-Layer Intelligence Pipeline)
HF_TOKEN = os.getenv('HF_TOKEN', os.getenv('HUGGINGFACE_API_KEY', ''))
HUGGINGFACE_API_KEY = HF_TOKEN  # Alias for backward compatibility
HF_MODEL_NAME = os.getenv('HF_MODEL_NAME', 'facebook/bart-large-mnli')

GROQ_API_KEY = os.getenv('GROQ_API_KEY', '')
GROQ_MODEL = os.getenv('GROQ_MODEL', 'llama-3.3-70b-versatile')

GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', '')
GEMINI_MODEL = os.getenv('GEMINI_MODEL', 'gemini-1.5-flash')

OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY', '')
OPENROUTER_MODEL = os.getenv('OPENROUTER_MODEL', 'meta-llama/llama-3.3-70b-instruct')

# Configurable provider fallback order (default: groq -> gemini -> openrouter)
AI_PROVIDER_ORDER = [p.strip().lower() for p in os.getenv('AI_PROVIDER_ORDER', 'groq,gemini,openrouter').split(',') if p.strip()]

# Provider HTTP request timeouts (seconds)
AI_PROVIDER_TIMEOUT_SECONDS = int(os.getenv('AI_PROVIDER_TIMEOUT_SECONDS', '15'))

# Application settings
APP_NAME = 'ApplyTrack AI'

# Gmail Sync & Retention Configuration
GMAIL_SYNC_PAGE_SIZE = int(os.getenv('GMAIL_SYNC_PAGE_SIZE', '25'))
GMAIL_INITIAL_SYNC_DAYS = int(os.getenv('GMAIL_INITIAL_SYNC_DAYS', os.getenv('GMAIL_SYNC_INITIAL_DAYS', '365')))
GMAIL_SYNC_INITIAL_DAYS = GMAIL_INITIAL_SYNC_DAYS  # Backward compatibility alias
RAW_EMAIL_RETENTION_DAYS = int(os.getenv('RAW_EMAIL_RETENTION_DAYS', '90'))  # Default 3 months
STALE_APPLICATION_DAYS = 14  # Default threshold for stale applications

# Queue, Worker & Concurrency Configuration (Phase 3)
QUEUE_BATCH_SIZE = int(os.getenv('QUEUE_BATCH_SIZE', '25'))  # Conservative starting batch: 25
MAX_CONCURRENT_WORKERS = int(os.getenv('MAX_CONCURRENT_WORKERS', '1'))  # Conservative starting workers: 1
WORKER_LOCK_TIMEOUT_SECONDS = int(os.getenv('WORKER_LOCK_TIMEOUT_SECONDS', '600'))  # 10 minutes
MAX_JOB_RETRIES = int(os.getenv('MAX_JOB_RETRIES', '3'))  # Max retry attempts before DEAD_LETTER
BASE_RETRY_BACKOFF_SECONDS = int(os.getenv('BASE_RETRY_BACKOFF_SECONDS', '30'))  # 30 seconds base exponential backoff
