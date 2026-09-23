from typing import Callable

from django.conf import settings
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect

from apps.authentication.models.mfa_device import MFADevice

EXEMPT_PATH_PREFIXES = ("/auth/", "/static/", "/metrics", "/__debug__/")


class MFAEnforcementMiddleware:
    """When `MFA_ENABLED`, blocks any authenticated request outside the
    authentication routes until the user has a confirmed MFA device."""

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        if self._requires_enrollment(request):
            return redirect("authentication:mfa-setup")
        return self.get_response(request)

    def _requires_enrollment(self, request: HttpRequest) -> bool:
        if not settings.MFA_ENABLED or request.path.startswith(EXEMPT_PATH_PREFIXES):
            return False
        user = getattr(request, "user", None)
        if user is None or not user.is_authenticated:
            return False
        return not MFADevice.objects.confirmed().filter(user=user).exists()
