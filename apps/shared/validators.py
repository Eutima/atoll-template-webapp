from apps.shared.exceptions import SerializerValidationError


def validate_min_length(value: str, min_length: int, field_name: str = "value") -> str:
    if len(value) < min_length:
        raise SerializerValidationError([f"{field_name} must be at least {min_length} characters."])
    return value
