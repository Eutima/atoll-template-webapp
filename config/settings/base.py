import logging
import os
from pathlib import Path

from dotenv import load_dotenv
from l4py import LogConfigBuilderDjango

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent.parent

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "insecure-dev-secret-key")

DEBUG = False

ALLOWED_HOSTS: list[str] = []
CSRF_TRUSTED_ORIGINS: list[str] = []
DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

THIRD_PARTY_APPS = [
    "django_cotton",
    "django_htmx",
    "django_filters",
    "huey.contrib.djhuey",
]

LOCAL_APPS = [
    "apps.shared",
    "apps.authentication",
    "apps.jobs",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "apps.authentication.middleware.MFAEnforcementMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "django_htmx.middleware.HtmxMiddleware",
    "apps.shared.middleware.LoggingContextMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

AUTH_USER_MODEL = "authentication.UserProfile"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LOGIN_URL = "authentication:login"
LOGIN_REDIRECT_URL = "home"
LOGOUT_REDIRECT_URL = "authentication:login"

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True
LOCALE_PATHS = [BASE_DIR / "locale"]

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

AUTH_PROVIDER = os.environ.get("AUTH_PROVIDER", "django")

MFA_ENABLED = os.environ.get("MFA_ENABLED", "False").lower() == "true"

ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "")

HELIX_BASE_URL = "https://helix.eutima.ch"
HELIX_OAUTH_CLIENT_ID = os.environ.get("HELIX_OAUTH_CLIENT_ID", "")
HELIX_OAUTH_CLIENT_SECRET = os.environ.get("HELIX_OAUTH_CLIENT_SECRET", "")
HELIX_OAUTH_TENANT = os.environ.get("HELIX_OAUTH_TENANT", "")
HELIX_OAUTH_REDIRECT_URI = os.environ.get("HELIX_OAUTH_REDIRECT_URI", "")
HELIX_WORKSPACE_TENANT = os.environ.get("HELIX_WORKSPACE_TENANT", "")

LOGGING = (
    LogConfigBuilderDjango()
    .django_log_level(logging.INFO)
    .show_sql(False)
    .file_enabled(False)  # containers log to stdout; no log files on disk
    .add_logger("apps", logging.DEBUG)
    .build_config()
)
