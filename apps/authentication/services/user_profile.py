from typing import Any

from django.conf import settings
from django.db.models import QuerySet
from l4py import get_logger

from apps.authentication.models.user_profile import UserProfile
from apps.shared.exceptions import NotFoundError, ValidationError

logger = get_logger()


class UserProfileService:
    def filter(self, **criteria: Any) -> QuerySet[UserProfile]:
        return UserProfile.objects.filter(**criteria)

    def search(self, term: str) -> QuerySet[UserProfile]:
        queryset = UserProfile.objects.active()
        return queryset.search(term) if term else queryset

    def by_id(self, profile_id: int) -> UserProfile:
        try:
            return UserProfile.objects.get(pk=profile_id)
        except UserProfile.DoesNotExist as exc:
            raise NotFoundError(f"UserProfile {profile_id} not found") from exc

    def create(
        self,
        *,
        email: str,
        password: str,
        first_name: str = "",
        last_name: str = "",
    ) -> UserProfile:
        if UserProfile.objects.with_email(email).exists():
            raise ValidationError({"email": ["A user with this email already exists."]})
        profile = UserProfile.objects.create_user(
            email=email, password=password, first_name=first_name, last_name=last_name
        )
        logger.info("Created UserProfile id=%s email=%s", profile.id, profile.email)
        return profile

    def update(self, profile_id: int, **fields: Any) -> UserProfile:
        profile = self.by_id(profile_id)
        for key, value in fields.items():
            setattr(profile, key, value)
        profile.save(update_fields=[*fields.keys(), "updated_at"])
        return profile

    def delete(self, profile_id: int) -> None:
        profile = self.by_id(profile_id)
        profile.delete()

    def create_initial_superuser(self) -> UserProfile | None:
        if UserProfile.objects.exists():
            return None
        email = settings.ADMIN_EMAIL
        password = settings.ADMIN_PASSWORD
        if not email or not password:
            return None
        profile = UserProfile.objects.create_superuser(email=email, password=password)
        logger.info("Created initial superuser id=%s email=%s", profile.id, profile.email)
        return profile

    def activate(self, profile_id: int) -> UserProfile:
        return self.update(profile_id, is_active=True)

    def deactivate(self, profile_id: int) -> UserProfile:
        return self.update(profile_id, is_active=False)
