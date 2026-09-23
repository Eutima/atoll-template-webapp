import functools
from typing import Any, Callable

from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect

from apps.authentication.services.helix_login import USER_SESSION_KEY


def get_helix_user(request: HttpRequest) -> dict[str, str] | None:
    return request.session.get(USER_SESSION_KEY)


def is_helix_authenticated(request: HttpRequest) -> bool:
    return get_helix_user(request) is not None


def helix_login_required(view_func: Callable[..., HttpResponse]) -> Callable[..., HttpResponse]:
    @functools.wraps(view_func)
    def wrapped(request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        if not is_helix_authenticated(request):
            return redirect("authentication:login")
        return view_func(request, *args, **kwargs)

    return wrapped


class HelixLoginRequiredMixin:
    """View mixin: redirects to the login page unless the session carries a
    Helix login. Nothing requires this by default -- individual views opt in."""

    def dispatch(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        if not is_helix_authenticated(request):
            return redirect("authentication:login")
        return super().dispatch(request, *args, **kwargs)  # type: ignore[misc]
