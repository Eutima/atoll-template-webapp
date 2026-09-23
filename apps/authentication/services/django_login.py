from django.contrib.auth import authenticate
from django.http import HttpRequest

from apps.authentication.models.user_profile import UserProfile
from apps.shared.exceptions import ValidationError


class DjangoLoginService:
    def authenticate(self, request: HttpRequest, *, email: str, password: str) -> UserProfile:
        profile = authenticate(request, username=email, password=password)
        if profile is None:
            raise ValidationError({"__all__": ["Invalid email or password."]})
        return profile
