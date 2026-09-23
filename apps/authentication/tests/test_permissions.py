from django.http import HttpRequest, HttpResponse
from django.test import RequestFactory, SimpleTestCase
from django.views import View

from apps.authentication.permissions.helix import (
    HelixLoginRequiredMixin,
    get_helix_user,
    helix_login_required,
    is_helix_authenticated,
)
from apps.authentication.services.helix_login import USER_SESSION_KEY


def _request_with_session(session: dict | None = None) -> HttpRequest:
    request = RequestFactory().get("/")
    request.session = {} if session is None else session
    return request


class _GatedView(HelixLoginRequiredMixin, View):
    def get(self, request, *args, **kwargs) -> HttpResponse:
        return HttpResponse("ok")


@helix_login_required
def _gated_function_view(request) -> HttpResponse:
    return HttpResponse("ok")


class GetHelixUserTests(SimpleTestCase):
    def test_returns_none_when_not_signed_in(self) -> None:
        request = _request_with_session()
        self.assertIsNone(get_helix_user(request))

    def test_returns_claims_when_signed_in(self) -> None:
        claims = {"sub": "helix-sub-1", "email": "ada@example.com"}
        request = _request_with_session({USER_SESSION_KEY: claims})
        self.assertEqual(get_helix_user(request), claims)


class IsHelixAuthenticatedTests(SimpleTestCase):
    def test_false_when_no_session_claims(self) -> None:
        self.assertFalse(is_helix_authenticated(_request_with_session()))

    def test_true_when_session_has_claims(self) -> None:
        request = _request_with_session({USER_SESSION_KEY: {"sub": "helix-sub-1"}})
        self.assertTrue(is_helix_authenticated(request))


class HelixLoginRequiredDecoratorTests(SimpleTestCase):
    def test_redirects_when_not_signed_in(self) -> None:
        response = _gated_function_view(_request_with_session())
        self.assertEqual(response.status_code, 302)

    def test_passes_through_when_signed_in(self) -> None:
        request = _request_with_session({USER_SESSION_KEY: {"sub": "helix-sub-1"}})
        response = _gated_function_view(request)
        self.assertEqual(response.status_code, 200)


class HelixLoginRequiredMixinTests(SimpleTestCase):
    def test_redirects_when_not_signed_in(self) -> None:
        response = _GatedView().dispatch(_request_with_session())
        self.assertEqual(response.status_code, 302)

    def test_passes_through_when_signed_in(self) -> None:
        request = _request_with_session({USER_SESSION_KEY: {"sub": "helix-sub-1"}})
        response = _GatedView().dispatch(request)
        self.assertEqual(response.status_code, 200)
