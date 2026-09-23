from apps.shared.exceptions import SerializerValidationError
from apps.shared.serializers import BaseSerializer


class LoginSerializer(BaseSerializer):
    def fields(self) -> list[str]:
        return ["email", "password"]

    def validate_email(self, value: str | None) -> str:
        if not value:
            raise SerializerValidationError(["This field is required."])
        return value

    def validate_password(self, value: str | None) -> str:
        if not value:
            raise SerializerValidationError(["This field is required."])
        return value
