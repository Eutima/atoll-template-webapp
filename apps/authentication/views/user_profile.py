from typing import Any

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import logout
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.views import View

from apps.authentication.serializers.login import LoginSerializer
from apps.authentication.services.django_login import DjangoLoginService
from apps.authentication.services.helix_login import HelixLoginService
from apps.authentication.services.mfa import MFAService
from apps.shared.exceptions import PermissionDeniedError, ValidationError


class LoginPageView(View):
    template_name = "authentication/login.html"
    service = DjangoLoginService()
    mfa_service = MFAService()

    def get(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        return render(request, self.template_name, {"auth_provider": settings.AUTH_PROVIDER})

    def post(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        if settings.AUTH_PROVIDER != "django":
            raise Http404

        serializer = LoginSerializer(data=request.POST)
        if not serializer.is_valid():
            context = {"auth_provider": settings.AUTH_PROVIDER, "errors": serializer.errors}
            return render(request, self.template_name, context, status=400)

        try:
            profile = self.service.authenticate(request, **serializer.validated_data)
        except ValidationError as exc:
            context = {"auth_provider": settings.AUTH_PROVIDER, "errors": exc.errors}
            return render(request, self.template_name, context, status=400)

        if not self.mfa_service.complete_login(request, profile):
            return redirect("authentication:mfa-verify")
        return redirect("/")


class HelixLoginView(View):
    service = HelixLoginService()

    def get(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        if settings.AUTH_PROVIDER != "helix":
            raise Http404
        return self.service.build_authorize_redirect(request)


class HelixCallbackView(View):
    service = HelixLoginService()
    mfa_service = MFAService()

    def get(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        if settings.AUTH_PROVIDER != "helix":
            raise Http404
        try:
            profile = self.service.complete_login(request)
        except ValidationError:
            messages.error(request, "Login with Helix failed. Please try again.")
            return redirect("authentication:login")
        except PermissionDeniedError:
            return render(request, "authentication/helix_forbidden.html", status=403)
        if not self.mfa_service.complete_login(request, profile):
            return redirect("authentication:mfa-verify")
        return redirect("/")


class LogoutView(View):
    def post(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        logout(request)
        return redirect("authentication:login")
