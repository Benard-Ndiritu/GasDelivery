"""
Django settings for the GasDelivery backend.

All deployment-specific values come from environment variables.
See `.env.example` in the repository root for the full list.
"""

import os
from datetime import timedelta
from pathlib import Path

import dj_database_url
from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent


def env(name, default=None):
    value = os.environ.get(name)
    return default if value in (None, '') else value


def env_bool(name, default=False):
    value = os.environ.get(name)
    if value in (None, ''):
        return default
    return value.strip().lower() in ('1', 'true', 'yes', 'on')


def env_list(name, default=''):
    raw = os.environ.get(name, default) or ''
    return [item.strip() for item in raw.split(',') if item.strip()]


def env_int(name, default):
    value = os.environ.get(name)
    return default if value in (None, '') else int(value)


# ---------------------------------------------------------------------------
# Core
# ---------------------------------------------------------------------------

DEBUG = env_bool('DEBUG', False)

SECRET_KEY = env('SECRET_KEY')
if not SECRET_KEY:
    if DEBUG:
        SECRET_KEY = 'django-insecure-local-development-only-key'
    else:
        raise ImproperlyConfigured('SECRET_KEY environment variable is required when DEBUG is off.')

ALLOWED_HOSTS = env_list('ALLOWED_HOSTS', '127.0.0.1,localhost')
# Render sets this automatically for every web service.
RENDER_EXTERNAL_HOSTNAME = env('RENDER_EXTERNAL_HOSTNAME')
if RENDER_EXTERNAL_HOSTNAME:
    ALLOWED_HOSTS.append(RENDER_EXTERNAL_HOSTNAME)

INSTALLED_APPS = [
    'daphne',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    'rest_framework',
    'rest_framework_simplejwt.token_blacklist',
    'corsheaders',
    'channels',
    'anymail',

    'users',
    'dealers',
    'gas',
    'orders',
    'payments',
    'realtime',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'GasDelivery.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'GasDelivery.wsgi.application'
ASGI_APPLICATION = 'GasDelivery.asgi.application'

ADMIN_URL = env('ADMIN_URL', 'admin/')

# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------

DATABASE_URL = env('DATABASE_URL')
if DATABASE_URL:
    DATABASES = {
        'default': dj_database_url.parse(
            DATABASE_URL,
            conn_max_age=env_int('DB_CONN_MAX_AGE', 60),
            conn_health_checks=True,
            ssl_require=env_bool('DB_SSL_REQUIRE', False),
        )
    }
else:
    if not DEBUG:
        raise ImproperlyConfigured('DATABASE_URL environment variable is required when DEBUG is off.')
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
AUTH_USER_MODEL = 'users.User'

# ---------------------------------------------------------------------------
# Redis: channel layer + cache (falls back to in-memory for local dev)
# ---------------------------------------------------------------------------

REDIS_URL = env('REDIS_URL')

if REDIS_URL:
    CHANNEL_LAYERS = {
        'default': {
            'BACKEND': 'channels_redis.core.RedisChannelLayer',
            'CONFIG': {'hosts': [REDIS_URL]},
        },
    }
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.redis.RedisCache',
            'LOCATION': REDIS_URL,
        }
    }
else:
    CHANNEL_LAYERS = {'default': {'BACKEND': 'channels.layers.InMemoryChannelLayer'}}
    CACHES = {'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}}

# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_RENDERER_CLASSES': (
        ('rest_framework.renderers.JSONRenderer', 'rest_framework.renderers.BrowsableAPIRenderer')
        if DEBUG else ('rest_framework.renderers.JSONRenderer',)
    ),
    'DEFAULT_THROTTLE_CLASSES': (
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
        'rest_framework.throttling.ScopedRateThrottle',
    ),
    'DEFAULT_THROTTLE_RATES': {
        # Per client IP. Kept generous because mobile carriers put many users behind
        # one IP (CGNAT); OTP brute force is stopped by per-code attempt limits instead.
        'anon': env('THROTTLE_ANON', '120/min'),
        'user': env('THROTTLE_USER', '300/min'),
        'auth': env('THROTTLE_AUTH', '30/min'),
        'otp': env('THROTTLE_OTP', '20/hour'),
    },
    # Number of trusted reverse proxies in front of the app, used to read the real
    # client IP from X-Forwarded-For for throttling. Leave unset unless you know it.
    'NUM_PROXIES': env_int('NUM_PROXIES', 0) or None,
    'EXCEPTION_HANDLER': 'GasDelivery.exceptions.api_exception_handler',
}

SIMPLE_JWT = {
    'USER_ID_FIELD': 'phone_number',
    'USER_ID_CLAIM': 'phone_number',
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=env_int('JWT_ACCESS_MINUTES', 60)),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=env_int('JWT_REFRESH_DAYS', 30)),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'UPDATE_LAST_LOGIN': True,
}

PASSWORD_RESET_OTP_MINUTES = 10
PASSWORD_RESET_OTP_MAX_ATTEMPTS = 5

# ---------------------------------------------------------------------------
# CORS / CSRF
# ---------------------------------------------------------------------------

CORS_ALLOWED_ORIGINS = env_list(
    'CORS_ALLOWED_ORIGINS',
    'http://localhost:3000,http://127.0.0.1:3000' if DEBUG else '',
)
# Optional regex list, e.g. to allow Vercel preview deployments:
# CORS_ALLOWED_ORIGIN_REGEXES=^https://gas-admin-[a-z0-9-]+\.vercel\.app$
CORS_ALLOWED_ORIGIN_REGEXES = env_list('CORS_ALLOWED_ORIGIN_REGEXES')
CSRF_TRUSTED_ORIGINS = env_list('CSRF_TRUSTED_ORIGINS')
if RENDER_EXTERNAL_HOSTNAME:
    CSRF_TRUSTED_ORIGINS.append(f'https://{RENDER_EXTERNAL_HOSTNAME}')

# ---------------------------------------------------------------------------
# HTTPS / security headers (active when DEBUG is off)
# ---------------------------------------------------------------------------

if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SECURE_SSL_REDIRECT = env_bool('SECURE_SSL_REDIRECT', True)
    SECURE_REDIRECT_EXEMPT = [r'^healthz/$']
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = env_int('SECURE_HSTS_SECONDS', 60 * 60 * 24 * 30)
    SECURE_HSTS_INCLUDE_SUBDOMAINS = False
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_REFERRER_POLICY = 'same-origin'
    X_FRAME_OPTIONS = 'DENY'

# ---------------------------------------------------------------------------
# I18N
# ---------------------------------------------------------------------------

LANGUAGE_CODE = 'en-us'
TIME_ZONE = env('TIME_ZONE', 'Africa/Nairobi')
USE_I18N = True
USE_TZ = True

# ---------------------------------------------------------------------------
# Static files
# ---------------------------------------------------------------------------

STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STORAGES = {
    'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
    'staticfiles': {
        'BACKEND': (
            'django.contrib.staticfiles.storage.StaticFilesStorage' if DEBUG
            else 'whitenoise.storage.CompressedManifestStaticFilesStorage'
        ),
    },
}

# ---------------------------------------------------------------------------
# Email (Resend via Anymail; console backend when no API key is configured)
# ---------------------------------------------------------------------------

RESEND_API_KEY = env('RESEND_API_KEY')
if RESEND_API_KEY:
    EMAIL_BACKEND = 'anymail.backends.resend.EmailBackend'
    ANYMAIL = {'RESEND_API_KEY': RESEND_API_KEY}
else:
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
DEFAULT_FROM_EMAIL = env('DEFAULT_FROM_EMAIL', 'onboarding@resend.dev')
SERVER_EMAIL = DEFAULT_FROM_EMAIL

# ---------------------------------------------------------------------------
# M-Pesa (Daraja)
# ---------------------------------------------------------------------------

MPESA_ENV = env('MPESA_ENV', 'sandbox')  # 'sandbox' or 'production'
MPESA_CONSUMER_KEY = env('MPESA_CONSUMER_KEY', '')
MPESA_CONSUMER_SECRET = env('MPESA_CONSUMER_SECRET', '')
# 174379 and its passkey are Safaricom's public sandbox test credentials.
MPESA_SHORTCODE = env('MPESA_SHORTCODE', '174379' if MPESA_ENV == 'sandbox' else '')
MPESA_PASSKEY = env(
    'MPESA_PASSKEY',
    'bfb279f9aa9bdbcf158e97dd71a467cd2e0c893059b10f78e6b72ada1ed2c919' if MPESA_ENV == 'sandbox' else '',
)
# 'CustomerPayBillOnline' for a paybill, 'CustomerBuyGoodsOnline' for a till number.
MPESA_TRANSACTION_TYPE = env('MPESA_TRANSACTION_TYPE', 'CustomerPayBillOnline')
# For Buy Goods, PartyB is the till number (which differs from the shortcode).
MPESA_PARTY_B = env('MPESA_PARTY_B', MPESA_SHORTCODE)
MPESA_CALLBACK_URL = env('MPESA_CALLBACK_URL', '')
# Optional shared secret. When set, the callback URL must end with /<token>/.
MPESA_CALLBACK_TOKEN = env('MPESA_CALLBACK_TOKEN', '')
MPESA_TIMEOUT_SECONDS = env_int('MPESA_TIMEOUT_SECONDS', 30)

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'simple': {'format': '{asctime} {levelname} {name}: {message}', 'style': '{'},
    },
    'handlers': {
        'console': {'class': 'logging.StreamHandler', 'formatter': 'simple'},
    },
    'root': {'handlers': ['console'], 'level': env('LOG_LEVEL', 'INFO')},
    'loggers': {
        'django.request': {'handlers': ['console'], 'level': 'WARNING', 'propagate': False},
    },
}
