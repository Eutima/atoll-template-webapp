class ServiceError(Exception):
    """Base class for all service-layer errors."""


class NotFoundError(ServiceError):
    pass


class ValidationError(ServiceError):
    def __init__(self, errors: dict[str, list[str]]) -> None:
        self.errors = errors
        super().__init__(str(errors))


class PermissionDeniedError(ServiceError):
    pass


class SerializerValidationError(Exception):
    def __init__(self, messages: list[str]) -> None:
        self.messages = messages
        super().__init__("; ".join(messages))
