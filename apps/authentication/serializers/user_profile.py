from typing import Any

from apps.authentication.models.user_profile import UserProfile
from apps.shared.serializers import BaseSerializer


class UserProfileSerializer(BaseSerializer):
    def fields(self) -> list[str]:
        return []

    def to_representation(self, instance: UserProfile) -> dict[str, Any]:
        return {
            "id": instance.id,
            "email": instance.email,
            "full_name": instance.full_name(),
            "is_active": instance.is_active,
        }
