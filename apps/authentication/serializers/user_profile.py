from typing import Any

from apps.authentication.models.user_profile import UserProfile
from apps.shared.exceptions import SerializerValidationError
from apps.shared.serializers import BaseSerializer
from apps.shared.validators import validate_min_length


class SignUpSerializer(BaseSerializer):
    def fields(self) -> list[str]:
        return ["email", "password", "first_name", "last_name"]

    def validate_email(self, value: str | None) -> str:
        if not value or "@" not in value:
            raise SerializerValidationError(["A valid email is required."])
        return value.lower()

    def validate_password(self, value: str | None) -> str:
        if not value:
            raise SerializerValidationError(["Password is required."])
        return validate_min_length(value, 8, field_name="Password")

    def validate_first_name(self, value: str | None) -> str:
        return value or ""

    def validate_last_name(self, value: str | None) -> str:
        return value or ""


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
