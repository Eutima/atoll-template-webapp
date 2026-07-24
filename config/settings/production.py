import os

from .base import *  # noqa: F401,F403
from .base import INSTALLED_APPS, MIDDLEWARE

DEBUG = False

ALLOWED_HOSTS = [host.strip()
                 for host in os.environ["ALLOWED_HOSTS"].split(",") if host.strip()]
CSRF_TRUSTED_ORIGINS = [host.strip()
                        for host in os.environ["CSRF_TRUSTED_ORIGINS"].split(",") if host.strip()]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ["POSTGRES_DB"],
        "USER": os.environ["POSTGRES_USER"],
        "PASSWORD": os.environ["POSTGRES_PASSWORD"],
        "HOST": os.environ["POSTGRES_HOST"],
        "PORT": os.environ.get("POSTGRES_PORT", "5432"),
    }
}

HUEY = {
    "huey_class": "huey.RedisHuey",
    "name": "django_template_prod",
    "connection": {
        "host": os.environ.get("REDIS_HOST", "redis"),
        "port": int(os.environ.get("REDIS_PORT", "6379")),
        "db": int(os.environ.get("REDIS_DB", "0")),
    },
    "immediate": False,
}

EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"

# WhiteNoise serves compiled static assets directly from the app process in
# production, right after SecurityMiddleware per WhiteNoise's own setup docs.
MIDDLEWARE = [
    MIDDLEWARE[0],
    "whitenoise.middleware.WhiteNoiseMiddleware",
    *MIDDLEWARE[1:],
]
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# Defensive guard: Debug Toolbar must never load in production, even if this
# module is accidentally combined with development.py's INSTALLED_APPS.
assert "debug_toolbar" not in INSTALLED_APPS, "Debug toolbar must never load in production settings"
