from typing import Any

from apps.shared.exceptions import SerializerValidationError


class BaseSerializer:
    """Lightweight, non-DRF serializer for request validation and response
    shaping. Subclasses override `fields()` and, for input validation, one
    `validate_<field_name>` method per field. For output, override
    `to_representation()`."""

    def __init__(self, instance: Any = None, data: dict[str, Any] | None = None) -> None:
        self.instance = instance
        self.initial_data: dict[str, Any] = data or {}
        self.validated_data: dict[str, Any] = {}
        self.errors: dict[str, list[str]] = {}

    def fields(self) -> list[str]:
        raise NotImplementedError

    def to_representation(self, instance: Any) -> dict[str, Any]:
        raise NotImplementedError

    def is_valid(self) -> bool:
        self.errors = {}
        self.validated_data = {}
        for field_name in self.fields():
            value = self.initial_data.get(field_name)
            validator = getattr(self, f"validate_{field_name}", None)
            try:
                self.validated_data[field_name] = validator(value) if validator else value
            except SerializerValidationError as exc:
                self.errors[field_name] = exc.messages
        return not self.errors

    @property
    def data(self) -> dict[str, Any]:
        if self.instance is not None:
            return self.to_representation(self.instance)
        return self.validated_data
