from unittest.mock import patch

from django.contrib.sessions.middleware import SessionMiddleware
from django.http import HttpRequest
from django.test import RequestFactory, SimpleTestCase, override_settings

from apps.authentication.services.helix_login import PENDING_SESSION_KEY, USER_SESSION_KEY, HelixLoginService
from apps.shared.exceptions import PermissionDeniedError, ValidationError
from apps.shared.interfaces.helix.client import HelixInterface

HELIX_SETTINGS = {
    "HELIX_BASE_URL": "https://helix.example.com",
    "HELIX_OAUTH_CLIENT_ID": "client-id",
    "HELIX_OAUTH_CLIENT_SECRET": "client-secret",
    "HELIX_OAUTH_TENANT": "registration-workspace",
    "HELIX_OAUTH_REDIRECT_URI": "https://app.example.com/auth/helix/callback/",
    "HELIX_WORKSPACE_TENANT": "acme-corp",
}


def _with_session(request: HttpRequest) -> HttpRequest:
    SessionMiddleware(lambda r: None).process_request(request)
    request.session.save()
    return request


@override_settings(**HELIX_SETTINGS)
class HelixLoginServiceTests(SimpleTestCase):
    def setUp(self) -> None:
        self.factory = RequestFactory()
        self.service = HelixLoginService()

    def _authorized_request(self, session: object, **query: str) -> HttpRequest:
        """A callback request carrying an already-started login's session."""
        callback_request = self.factory.get("/auth/helix/callback/", query)
        callback_request.session = session
        return callback_request

    def test_is_configured_true_when_client_id_set(self) -> None:
        self.assertTrue(self.service.is_configured())

    @override_settings(HELIX_OAUTH_CLIENT_ID="")
    def test_is_configured_false_when_client_id_blank(self) -> None:
        self.assertFalse(self.service.is_configured())

    def test_build_authorize_redirect_stores_pkce_state_in_session(self) -> None:
        request = _with_session(self.factory.get("/auth/helix/login/"))
        response = self.service.build_authorize_redirect(request)
        self.assertEqual(response.status_code, 302)
        pending = request.session[PENDING_SESSION_KEY]
        self.assertIn("state", pending)
        self.assertIn("code_verifier", pending)
        self.assertIn(pending["state"], response.url)

    def test_complete_login_stores_session_claims_when_tenant_member(self) -> None:
        start_request = _with_session(self.factory.get("/auth/helix/login/"))
        self.service.build_authorize_redirect(start_request)
        state = start_request.session[PENDING_SESSION_KEY]["state"]
        request = self._authorized_request(start_request.session, code="auth-code", state=state)

        with (
            patch.object(HelixInterface, "exchange_code", return_value={"access_token": "access-token"}),
            patch.object(
                HelixInterface,
                "userinfo",
                return_value={"sub": "helix-sub-1", "email": "ada@example.com", "given_name": "Ada"},
            ),
            patch.object(HelixInterface, "tenant_slugs", return_value=["acme-corp"]),
        ):
            claims = self.service.complete_login(request)

        self.assertEqual(claims["email"], "ada@example.com")
        self.assertEqual(claims["sub"], "helix-sub-1")
        self.assertEqual(request.session[USER_SESSION_KEY], claims)
        self.assertNotIn(PENDING_SESSION_KEY, request.session)

    def test_complete_login_missing_state_raises_validation_error(self) -> None:
        request = _with_session(self.factory.get("/auth/helix/callback/", {"code": "auth-code", "state": "bogus"}))
        with self.assertRaises(ValidationError):
            self.service.complete_login(request)

    def test_complete_login_rejects_non_tenant_member(self) -> None:
        start_request = _with_session(self.factory.get("/auth/helix/login/"))
        self.service.build_authorize_redirect(start_request)
        state = start_request.session[PENDING_SESSION_KEY]["state"]
        request = self._authorized_request(start_request.session, code="auth-code", state=state)

        with (
            patch.object(HelixInterface, "exchange_code", return_value={"access_token": "access-token"}),
            patch.object(
                HelixInterface, "userinfo", return_value={"sub": "helix-sub-1", "email": "ada@example.com"}
            ),
            patch.object(HelixInterface, "tenant_slugs", return_value=["other-co"]),
        ):
            with self.assertRaises(PermissionDeniedError):
                self.service.complete_login(request)

        self.assertNotIn(USER_SESSION_KEY, request.session)
