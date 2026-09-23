import logging

from l4py import LogConfigBuilderDjango

from .base import *  # noqa: F401,F403
from .base import BASE_DIR, INSTALLED_APPS, MIDDLEWARE

DEBUG = True

ALLOWED_HOSTS = [host.strip()
                 for host in os.environ.get("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",") if host.strip()]

CSRF_TRUSTED_ORIGINS = [host.strip()
                        for host in os.environ.get("CSRF_TRUSTED_ORIGINS", "http://localhost:8000,http://127.0.0.1:8000").split(",") if host.strip()]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

HUEY = {
    "huey_class": "huey.SqliteHuey",
    "name": "django_template_dev",
    "filename": str(BASE_DIR / "huey.sqlite3"),
    "immediate": False,
}

# Debug Toolbar is added ONLY in development settings, never conditionally in
# base.py, so it structurally cannot leak into production even if DEBUG is
# accidentally flipped to True there.
INSTALLED_APPS = [*INSTALLED_APPS, "debug_toolbar"]
MIDDLEWARE = ["debug_toolbar.middleware.DebugToolbarMiddleware", *MIDDLEWARE]
INTERNAL_IPS = ["127.0.0.1"]

LOGGING = (
    LogConfigBuilderDjango()
    .django_log_level(logging.INFO)
    .show_sql(False)
    .file_enabled(False)  # containers log to stdout; no log files on disk
    .add_logger("apps", logging.DEBUG)
    .build_config()
)
