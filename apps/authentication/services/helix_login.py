import base64
import hashlib
import secrets
from typing import Any

from django.conf import settings
from django.http import HttpRequest, HttpResponseRedirect
from l4py import get_logger

from apps.authentication.models.user_profile import UserProfile
from apps.shared.exceptions import PermissionDeniedError, ValidationError
from apps.shared.interfaces.helix.client import HelixInterface
from apps.shared.interfaces.helix.exceptions import HelixAuthError

logger = get_logger()

SESSION_KEY = "helix_oauth"


class HelixLoginService:
    interface = HelixInterface()

    def build_authorize_redirect(self, request: HttpRequest) -> HttpResponseRedirect:
        code_verifier = secrets.token_urlsafe(64)
        state = secrets.token_urlsafe(32)
        request.session[SESSION_KEY] = {"code_verifier": code_verifier, "state": state}
        url = self.interface.authorize_url(state=state, code_challenge=self._code_challenge(code_verifier))
        return HttpResponseRedirect(url)

    def complete_login(self, request: HttpRequest) -> UserProfile:
        pending = request.session.pop(SESSION_KEY, None)
        code = request.GET.get("code")
        state = request.GET.get("state")
        if not pending or not code or not state or state != pending.get("state"):
            raise ValidationError({"state": ["Invalid or expired login attempt."]})

        try:
            tokens = self.interface.exchange_code(code=code, code_verifier=pending["code_verifier"])
            access_token = tokens["access_token"]
            claims = self.interface.userinfo(access_token=access_token)
            tenant_slugs = self.interface.tenant_slugs(access_token=access_token)
        except HelixAuthError as exc:
            raise ValidationError({"helix": [str(exc)]}) from exc

        if settings.HELIX_WORKSPACE_TENANT not in tenant_slugs:
            raise PermissionDeniedError("Not a member of the required Helix workspace")

        return self._get_or_create_profile(claims)

    def _get_or_create_profile(self, claims: dict[str, Any]) -> UserProfile:
        helix_sub = claims["sub"]
        email = claims["email"]

        profile = UserProfile.objects.filter(helix_sub=helix_sub).first()
        if profile is None:
            profile = UserProfile.objects.with_email(email).first()
        if profile is None:
            profile = UserProfile.objects.create_user(
                email=email,
                password=None,
                first_name=claims.get("given_name", ""),
                last_name=claims.get("family_name", ""),
            )
            logger.info("Created UserProfile id=%s email=%s via Helix login", profile.id, profile.email)

        if profile.helix_sub != helix_sub:
            profile.helix_sub = helix_sub
            profile.save(update_fields=["helix_sub", "updated_at"])
        return profile

    @staticmethod
    def _code_challenge(code_verifier: str) -> str:
        digest = hashlib.sha256(code_verifier.encode("ascii")).digest()
        return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
