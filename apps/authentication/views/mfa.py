from typing import Any

from django.conf import settings
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.views import View

from apps.authentication.lib import totp
from apps.authentication.models.mfa_device import MFADevice
from apps.authentication.serializers.mfa import MFACodeSerializer
from apps.authentication.services.mfa import PENDING_SESSION_KEY, MFAService
from apps.shared.exceptions import NotFoundError, ValidationError


class MFASetupView(View):
    template_name = "authentication/mfa_setup.html"
    service = MFAService()

    def get(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        if not settings.MFA_ENABLED:
            raise Http404
        if MFADevice.objects.confirmed().filter(user=request.user).exists():
            return render(request, "authentication/mfa_enabled.html")
        device = self.service.enroll(request.user)
        return render(request, self.template_name, self._enrollment_context(request, device))

    def post(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        if not settings.MFA_ENABLED:
            raise Http404

        serializer = MFACodeSerializer(data=request.POST)
        if not serializer.is_valid():
            return self._render_pending(request, serializer.errors)

        try:
            backup_codes = self.service.confirm(request.user, serializer.validated_data["code"])
        except ValidationError as exc:
            return self._render_pending(request, exc.errors)

        return render(request, "authentication/mfa_backup_codes.html", {"backup_codes": backup_codes})

    def _render_pending(self, request: HttpRequest, errors: dict[str, list[str]]) -> HttpResponse:
        device = MFADevice.objects.filter(user=request.user, confirmed_at__isnull=True).first()
        if device is None:
            return redirect("authentication:mfa-setup")
        context = self._enrollment_context(request, device)
        context["errors"] = errors
        return render(request, self.template_name, context, status=400)

    @staticmethod
    def _enrollment_context(request: HttpRequest, device: MFADevice) -> dict[str, Any]:
        uri = totp.provisioning_uri(device.secret, request.user.email)
        return {"secret": device.secret, "qr_svg": totp.qr_code_svg(uri)}


class MFADisableView(View):
    service = MFAService()

    def post(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        try:
            self.service.disable(request.user)
        except NotFoundError:
            raise Http404
        return redirect("authentication:mfa-setup")


class MFAVerifyView(View):
    template_name = "authentication/mfa_verify.html"
    service = MFAService()

    def get(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        if PENDING_SESSION_KEY not in request.session:
            return redirect("authentication:login")
        return render(request, self.template_name)

    def post(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        if PENDING_SESSION_KEY not in request.session:
            return redirect("authentication:login")

        serializer = MFACodeSerializer(data=request.POST)
        if not serializer.is_valid():
            return render(request, self.template_name, {"errors": serializer.errors}, status=400)

        try:
            self.service.verify_login_code(request, serializer.validated_data["code"])
        except ValidationError as exc:
            return render(request, self.template_name, {"errors": exc.errors}, status=400)

        return redirect("/")
