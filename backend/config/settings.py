"""
Django settings for Solar CRM project.
"""

import os
import sys
from datetime import timedelta
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

# Load environment variables from backend/.env
load_dotenv(BASE_DIR / '.env')

APP_ENV = os.getenv('APP_ENV', 'development').lower().strip()
SECRET_KEY = os.getenv('SECRET_KEY', 'django-insecure-default-dev-key')

if APP_ENV == 'production':
    DEBUG = os.getenv('DEBUG', 'False').strip().lower() in ('true', '1')
    if not SECRET_KEY or SECRET_KEY == 'django-insecure-default-dev-key' or len(SECRET_KEY) < 32:
        from django.core.exceptions import ImproperlyConfigured
        raise ImproperlyConfigured(
            "Production mode (APP_ENV=production) requires a strong, unique SECRET_KEY (minimum 32 characters)."
        )
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = 'DENY'
    SESSION_COOKIE_SECURE = os.getenv('SESSION_COOKIE_SECURE', 'True').strip().lower() in ('true', '1')
    CSRF_COOKIE_SECURE = os.getenv('CSRF_COOKIE_SECURE', 'True').strip().lower() in ('true', '1')
    SECURE_HSTS_SECONDS = int(os.getenv('SECURE_HSTS_SECONDS', '31536000'))
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
else:
    DEBUG = os.getenv('DEBUG', 'True') == 'True'

ALLOWED_HOSTS = [host.strip() for host in os.getenv('ALLOWED_HOSTS', 'localhost,127.0.0.1,testserver').split(',') if host.strip()]

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
    'rest_framework_simplejwt',
    'corsheaders',
    'django_filters',
    'drf_spectacular',

    # Local apps
    'accounts',
    'masters',
    'leads',
    'activities',
    'surveys',
    'quotes',
    'notifications',
    'messaging',
    'helpbot',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'config.i18n_middleware.AppLanguageMiddleware',
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
        'DIRS': [BASE_DIR / 'templates'],
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

# Database
if 'test' in sys.argv or 'pytest' in sys.modules or os.getenv('USE_SQLITE_FOR_TESTS') == 'True':
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': ':memory:',
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': os.getenv('DB_NAME', 'solar_crm'),
            'USER': os.getenv('DB_USER', 'solar_user'),
            'PASSWORD': os.getenv('DB_PASSWORD', ''),
            'HOST': os.getenv('DB_HOST', 'localhost'),
            'PORT': os.getenv('DB_PORT', '5432'),
        }
    }

# Custom User Model
AUTH_USER_MODEL = 'accounts.User'

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# Internationalization
LANGUAGE_CODE = 'en'
TIME_ZONE = 'Asia/Kolkata'
USE_I18N = True
USE_TZ = True

LANGUAGES = [
    ('en', 'English'),
    ('hi', 'Hindi'),
    ('en-au', 'English (Australia)'),
    ('en-in', 'English (India)'),
]
LOCALE_PATHS = [
    BASE_DIR / 'locale',
]

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
FRONTEND_DIST = BASE_DIR.parent / 'frontend' / 'dist'
if FRONTEND_DIST.exists():
    STATICFILES_DIRS = [FRONTEND_DIST]
    WHITENOISE_ROOT = str(FRONTEND_DIST)
else:
    STATICFILES_DIRS = []
    WHITENOISE_ROOT = None

STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'
WHITENOISE_INDEX_FILE = True

# Logging Configuration with Structured Log Rotation & Sensitive Data Scrubbing
LOGS_DIR = BASE_DIR / 'logs'
LOGS_DIR.mkdir(exist_ok=True)

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'filters': {
        'sensitive_data_filter': {
            '()': 'config.logging_filters.SensitiveDataFilter',
        },
    },
    'formatters': {
        'standard': {
            'format': '[{asctime}] {levelname} [{name}:{lineno}] {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'filters': ['sensitive_data_filter'],
            'formatter': 'standard',
        },
        'file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': str(LOGS_DIR / 'solar_crm.log'),
            'maxBytes': 5 * 1024 * 1024,  # 5 MB
            'backupCount': 5,
            'filters': ['sensitive_data_filter'],
            'formatter': 'standard',
            'encoding': 'utf-8',
        },
    },
    'root': {
        'handlers': ['console', 'file'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
        'django.server': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}

# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# CORS settings
CORS_ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.getenv('CORS_ALLOWED_ORIGINS', 'http://localhost:5173,http://127.0.0.1:5173').split(',')
    if origin.strip()
]
CORS_ALLOW_CREDENTIALS = True

# Django REST Framework
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_FILTER_BACKENDS': (
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ),
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
}

# SimpleJWT Settings
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=60),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'AUTH_HEADER_TYPES': ('Bearer',),
}

# DRF Spectacular (OpenAPI 3 / Swagger)
SPECTACULAR_SETTINGS = {
    'TITLE': 'Solar CRM API',
    'DESCRIPTION': 'API documentation for Solar CRM for residential and commercial solar installations in India.',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
}

# AI Assist Configuration
AI_PROVIDER = os.getenv('AI_PROVIDER', 'rules').lower()
ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY', '').strip()
AI_MODEL = os.getenv('AI_MODEL', 'claude-sonnet-5-5').strip()
AI_TIMEOUT_SECONDS = int(os.getenv('AI_TIMEOUT_SECONDS', '15'))
AI_MAX_CALLS_PER_USER_PER_DAY = int(os.getenv('AI_MAX_CALLS_PER_USER_PER_DAY', '50'))

# Messaging Configuration
WHATSAPP_PROVIDER = os.getenv('WHATSAPP_PROVIDER', 'console').lower()
SMS_PROVIDER = os.getenv('SMS_PROVIDER', 'console').lower()

# Multi-Country Configuration (Phase 8)
ENABLED_COUNTRIES = [
    c.strip().upper() for c in os.getenv('ENABLED_COUNTRIES', 'IN,AU').split(',') if c.strip()
]

# Web Push (VAPID) Settings (Phase 11)
VAPID_PUBLIC_KEY = os.getenv(
    'VAPID_PUBLIC_KEY',
    'BBYDXW27Rt7hD5XQ_vzAj7efBlRaBP8rfAXQqO0vlK7_s3eykQWCFJXzEX2rfxTi10kCOQmI1IivqttUENZUtkE',
).strip()
VAPID_PRIVATE_KEY = os.getenv(
    'VAPID_PRIVATE_KEY',
    '-----BEGIN PRIVATE KEY-----\nMIGHAgEAMBMGByqGSM49AgEGCCqGSM49AwEHBG0wawIBAQQg3vspuPhbkG/AeXAT\nT0jbcJVl3AyyJyTr3zX3H3Hj41qhRANCAAQWA11tu0be4Q+V0P78wI+3nwZUWgT/\nK3wF0KjtL5Su/7N3spEFghSV8xF9q38U4tdJAjkJiNSIr6rbVBDWVLZB\n-----END PRIVATE KEY-----',
).strip()
VAPID_ADMIN_EMAIL = os.getenv('VAPID_ADMIN_EMAIL', 'admin@solarcrm.com').strip()

# Email (SMTP) Configuration (Phase 12)
_raw_backend = os.getenv('EMAIL_BACKEND', '').strip().lower()
EMAIL_HOST = os.getenv('EMAIL_HOST', '').strip()
EMAIL_PORT = int(os.getenv('EMAIL_PORT', '587'))
EMAIL_USE_TLS = os.getenv('EMAIL_USE_TLS', 'False').strip().lower() in ('true', '1', 'yes')
EMAIL_USE_SSL = os.getenv('EMAIL_USE_SSL', 'False').strip().lower() in ('true', '1', 'yes')
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER', '').strip()
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD', '').strip()
DEFAULT_FROM_EMAIL = os.getenv('DEFAULT_FROM_EMAIL', 'Solar CRM <noreply@solarcrm.com>').strip()
EMAIL_TIMEOUT = int(os.getenv('EMAIL_TIMEOUT', '15'))

if EMAIL_USE_TLS and EMAIL_USE_SSL:
    from django.core.exceptions import ImproperlyConfigured
    raise ImproperlyConfigured(
        "Both EMAIL_USE_TLS and EMAIL_USE_SSL are enabled in settings. "
        "Only one security protocol (STARTTLS or SSL) can be active at a time."
    )

if _raw_backend in ('smtp', 'django.core.mail.backends.smtp.emailbackend') and EMAIL_HOST:
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
elif _raw_backend in ('console', 'django.core.mail.backends.console.emailbackend'):
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
elif _raw_backend in ('locmem', 'django.core.mail.backends.locmem.emailbackend'):
    EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'
else:
    # Default to console in development so nothing breaks without SMTP settings
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Password Reset Token Timeout (1 hour = 3600 seconds)
PASSWORD_RESET_TIMEOUT = 3600

# Help Chatbot Configuration (Phase 13)
HELPBOT_PROVIDER = os.getenv('HELPBOT_PROVIDER', 'local').lower().strip()
HELPBOT_MODEL = os.getenv('HELPBOT_MODEL', 'claude-haiku-5-5').strip()
HELPBOT_TIMEOUT_SECONDS = int(os.getenv('HELPBOT_TIMEOUT_SECONDS', '15'))
HELPBOT_MAX_QUESTIONS_PER_USER_PER_DAY = int(os.getenv('HELPBOT_MAX_QUESTIONS_PER_USER_PER_DAY', '50'))

