from .base import *  # noqa: F401,F403

DEBUG = False

ALLOWED_HOSTS = ["testserver"]

# Hardcoded, not env-derived: tests must not depend on a developer's local .env.
MFA_ENABLED = False

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

HUEY = {
    "huey_class": "huey.SqliteHuey",
    "name": "django_template_test",
    "immediate": True,
}

PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
