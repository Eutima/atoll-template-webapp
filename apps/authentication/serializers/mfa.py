from apps.shared.exceptions import SerializerValidationError
from apps.shared.serializers import BaseSerializer


class MFACodeSerializer(BaseSerializer):
    def fields(self) -> list[str]:
        return ["code"]

    def validate_code(self, value: str | None) -> str:
        if not value:
            raise SerializerValidationError(["This field is required."])
        return value.strip()
