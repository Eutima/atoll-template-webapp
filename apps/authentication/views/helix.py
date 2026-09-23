from typing import Any

from django.contrib import messages
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.views import View

from apps.authentication.services.helix_login import USER_SESSION_KEY, HelixLoginService
from apps.shared.exceptions import PermissionDeniedError, ValidationError


class LoginPageView(View):
    template_name = "authentication/login.html"

    def get(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        return render(request, self.template_name, {})


class HelixLoginView(View):
    service = HelixLoginService()

    def get(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        if not self.service.is_configured():
            messages.info(request, "Login with Helix isn't available for this deployment.")
            return redirect("home")
        return self.service.build_authorize_redirect(request)


class HelixCallbackView(View):
    service = HelixLoginService()

    def get(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        if not self.service.is_configured():
            messages.info(request, "Login with Helix isn't available for this deployment.")
            return redirect("home")
        try:
            self.service.complete_login(request)
        except ValidationError:
            messages.error(request, "Login with Helix failed. Please try again.")
            return redirect("authentication:login")
        except PermissionDeniedError:
            return render(request, "authentication/helix_forbidden.html", status=403)
        return redirect("home")


class LogoutView(View):
    def post(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        request.session.pop(USER_SESSION_KEY, None)
        request.session.cycle_key()
        return redirect("home")
