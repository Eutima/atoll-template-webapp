import os

from .base import *  # noqa: F401,F403
from .base import INSTALLED_APPS, MIDDLEWARE

DEBUG = False

# No fallback: a production boot without a real secret must fail loudly rather
# than silently run on base.py's shared insecure development key.
SECRET_KEY = os.environ["DJANGO_SECRET_KEY"]

ALLOWED_HOSTS = [host.strip()
                 for host in os.environ["ALLOWED_HOSTS"].split(",") if host.strip()]
CSRF_TRUSTED_ORIGINS = [host.strip()
                        for host in os.environ["CSRF_TRUSTED_ORIGINS"].split(",") if host.strip()]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ["DB_NAME"],
        "USER": os.environ["DB_USER"],
        "PASSWORD": os.environ["DB_PASSWORD"],
        "HOST": os.environ["DB_HOST"],
        "PORT": os.environ.get("DB_PORT", "5432"),
    }
}

# Defaults on in production, overriding base.py's off-by-default value for local dev.
MFA_ENABLED = os.environ.get("MFA_ENABLED", "True") == "True"

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

# Temporarily disabled for HTTP-only testing (no TLS-terminating reverse proxy
# in front of gunicorn yet). Re-enable (env-configurable, default "True") once
# TLS termination is in place, otherwise every request 301s to https with
# nothing listening on it. SECURE_PROXY_SSL_HEADER must stay off along with
# these too: with no trusted proxy stripping/setting X-Forwarded-Proto, a
# client could spoof that header directly against gunicorn's exposed port.
# SECURE_SSL_REDIRECT = os.environ.get("SECURE_SSL_REDIRECT", "True") == "True"
# SESSION_COOKIE_SECURE = os.environ.get("SESSION_COOKIE_SECURE", "True") == "True"
# CSRF_COOKIE_SECURE = os.environ.get("CSRF_COOKIE_SECURE", "True") == "True"
# SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# Defensive guard: Debug Toolbar must never load in production, even if this
# module is accidentally combined with development.py's INSTALLED_APPS.
assert "debug_toolbar" not in INSTALLED_APPS, "Debug toolbar must never load in production settings"
