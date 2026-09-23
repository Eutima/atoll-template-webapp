import base64
import hashlib
import secrets

from django.conf import settings
from django.http import HttpRequest, HttpResponseRedirect

from apps.authentication.lib.helix_claims import build_session_claims
from apps.shared.exceptions import PermissionDeniedError, ValidationError
from apps.shared.interfaces.helix.client import HelixInterface
from apps.shared.interfaces.helix.exceptions import HelixAuthError

PENDING_SESSION_KEY = "helix_oauth"
USER_SESSION_KEY = "helix_user"


class HelixLoginService:
    interface = HelixInterface()

    @staticmethod
    def is_configured() -> bool:
        return bool(settings.HELIX_OAUTH_CLIENT_ID)

    def build_authorize_redirect(self, request: HttpRequest) -> HttpResponseRedirect:
        code_verifier = secrets.token_urlsafe(64)
        state = secrets.token_urlsafe(32)
        request.session[PENDING_SESSION_KEY] = {"code_verifier": code_verifier, "state": state}
        url = self.interface.authorize_url(state=state, code_challenge=self._code_challenge(code_verifier))
        return HttpResponseRedirect(url)

    def complete_login(self, request: HttpRequest) -> dict[str, str]:
        pending = request.session.pop(PENDING_SESSION_KEY, None)
        code = request.GET.get("code")
        state = request.GET.get("state")
        if not pending or not code or not state or state != pending.get("state"):
            raise ValidationError({"state": ["Invalid or expired login attempt."]})

        try:
            tokens = self.interface.exchange_code(code=code, code_verifier=pending["code_verifier"])
            access_token = tokens["access_token"]
            userinfo = self.interface.userinfo(access_token=access_token)
            tenant_slugs = self.interface.tenant_slugs(access_token=access_token)
        except HelixAuthError as exc:
            raise ValidationError({"helix": [str(exc)]}) from exc

        if settings.HELIX_WORKSPACE_TENANT not in tenant_slugs:
            raise PermissionDeniedError("Not a member of the required Helix workspace")

        claims = build_session_claims(userinfo)
        request.session[USER_SESSION_KEY] = claims
        request.session.cycle_key()
        return claims

    @staticmethod
    def _code_challenge(code_verifier: str) -> str:
        digest = hashlib.sha256(code_verifier.encode("ascii")).digest()
        return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
