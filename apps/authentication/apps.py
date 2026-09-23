from django.apps import AppConfig
from django.db.models.signals import post_migrate


class AuthenticationConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.authentication"
    label = "authentication"

    def ready(self) -> None:
        post_migrate.connect(_create_initial_superuser, sender=self)


def _create_initial_superuser(sender: AppConfig, **kwargs: object) -> None:
    from apps.authentication.services.user_profile import UserProfileService

    UserProfileService().create_initial_superuser()
