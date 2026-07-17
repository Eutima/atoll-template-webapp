from django.apps import AppConfig


class JobsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.jobs"
    label = "jobs"

    def ready(self) -> None:
        from apps.jobs.tasks import heartbeat  # noqa: F401
