from unittest.mock import patch

from django.conf import settings as django_settings
from django.test import SimpleTestCase, override_settings
from django.urls import reverse

from apps.shared.interfaces.helix.client import HelixInterface

HELIX_SETTINGS = {
    "HELIX_BASE_URL": "https://helix.example.com",
    "HELIX_OAUTH_CLIENT_ID": "client-id",
    "HELIX_OAUTH_CLIENT_SECRET": "client-secret",
    "HELIX_OAUTH_TENANT": "registration-workspace",
    "HELIX_OAUTH_REDIRECT_URI": "https://app.example.com/auth/helix/callback/",
    "HELIX_WORKSPACE_TENANT": "acme-corp",
}


class LoginPageViewTests(SimpleTestCase):
    def test_login_page_shows_unavailable_message_by_default(self) -> None:
        response = self.client.get(reverse("authentication:login"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Login isn't configured for this deployment.")
        self.assertNotContains(response, "Log in with Helix")

    @override_settings(**HELIX_SETTINGS)
    def test_login_page_shows_helix_button_when_configured(self) -> None:
        response = self.client.get(reverse("authentication:login"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Log in with Helix")


class HelixLoginViewTests(SimpleTestCase):
    def test_redirects_home_with_message_when_not_configured(self) -> None:
        response = self.client.get(reverse("authentication:helix-login"))
        self.assertRedirects(response, reverse("home"))

    @override_settings(**HELIX_SETTINGS)
    def test_get_redirects_to_helix_authorize_and_stores_session(self) -> None:
        response = self.client.get(reverse("authentication:helix-login"))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith("https://helix.example.com/auth/oauth/authorize/"))
        self.assertIn("tenant=registration-workspace", response.url)

        pending = self.client.session["helix_oauth"]
        self.assertIn("state", pending)
        self.assertIn("code_verifier", pending)
        self.assertIn(f"state={pending['state']}", response.url)


class HelixCallbackViewTests(SimpleTestCase):
    def test_redirects_home_with_message_when_not_configured(self) -> None:
        response = self.client.get(reverse("authentication:helix-callback"), {"code": "auth-code", "state": "x"})
        self.assertRedirects(response, reverse("home"))

    def _start_login(self) -> str:
        self.client.get(reverse("authentication:helix-login"))
        return self.client.session["helix_oauth"]["state"]

    @override_settings(**HELIX_SETTINGS)
    def test_callback_stores_session_claims_on_success(self) -> None:
        state = self._start_login()
        with (
            patch.object(HelixInterface, "exchange_code", return_value={"access_token": "access-token"}),
            patch.object(
                HelixInterface,
                "userinfo",
                return_value={"sub": "helix-sub-1", "email": "ada@example.com", "given_name": "Ada"},
            ),
            patch.object(HelixInterface, "tenant_slugs", return_value=["acme-corp"]),
        ):
            response = self.client.get(
                reverse("authentication:helix-callback"), {"code": "auth-code", "state": state}
            )

        self.assertRedirects(response, reverse("home"))
        self.assertEqual(self.client.session["helix_user"]["email"], "ada@example.com")

    @override_settings(**HELIX_SETTINGS)
    def test_callback_with_invalid_state_redirects_to_login(self) -> None:
        response = self.client.get(
            reverse("authentication:helix-callback"), {"code": "auth-code", "state": "bogus"}
        )
        self.assertRedirects(response, reverse("authentication:login"))
        self.assertNotIn("helix_user", self.client.session)

    @override_settings(**HELIX_SETTINGS)
    def test_callback_rejects_non_tenant_member(self) -> None:
        state = self._start_login()
        with (
            patch.object(HelixInterface, "exchange_code", return_value={"access_token": "access-token"}),
            patch.object(
                HelixInterface, "userinfo", return_value={"sub": "helix-sub-1", "email": "ada@example.com"}
            ),
            patch.object(HelixInterface, "tenant_slugs", return_value=["other-co"]),
        ):
            response = self.client.get(
                reverse("authentication:helix-callback"), {"code": "auth-code", "state": state}
            )

        self.assertEqual(response.status_code, 403)
        self.assertNotIn("helix_user", self.client.session)


class LogoutViewTests(SimpleTestCase):
    def test_logout_clears_session_and_redirects_home(self) -> None:
        session = self.client.session
        session["helix_user"] = {"sub": "helix-sub-1", "email": "ada@example.com"}
        session.save()
        # The signed_cookies session backend bakes the cookie value at
        # session.save() time, not when self.client.session was first read.
        self.client.cookies[django_settings.SESSION_COOKIE_NAME] = session.session_key

        response = self.client.post(reverse("authentication:logout"))

        self.assertRedirects(response, reverse("home"))
        self.assertNotIn("helix_user", self.client.session)
