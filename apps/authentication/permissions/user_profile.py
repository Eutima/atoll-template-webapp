from typing import Any

from django.core.exceptions import PermissionDenied
from django.http import HttpRequest, HttpResponse

from apps.authentication.models.user_profile import UserProfile


def is_self_or_staff(user: UserProfile, target: UserProfile) -> bool:
    return user.is_authenticated and (user.pk == target.pk or user.is_staff)


class StaffRequiredMixin:
    """View mixin: raises PermissionDenied unless request.user is authenticated staff."""

    def dispatch(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        if not (request.user.is_authenticated and request.user.is_staff):
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)  # type: ignore[misc]
