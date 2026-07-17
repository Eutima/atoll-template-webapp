from .base import *  # noqa: F401,F403

DEBUG = False

ALLOWED_HOSTS = ["testserver"]

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

EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
