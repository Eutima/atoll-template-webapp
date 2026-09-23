from unittest.mock import patch

import pyotp
from django.test import TestCase, override_settings
from django.urls import reverse

from apps.authentication.models.user_profile import UserProfile
from apps.authentication.services.mfa import MFAService
from apps.shared.interfaces.helix.client import HelixInterface

HELIX_SETTINGS = {
    "AUTH_PROVIDER": "helix",
    "HELIX_BASE_URL": "https://helix.example.com",
    "HELIX_OAUTH_CLIENT_ID": "client-id",
    "HELIX_OAUTH_CLIENT_SECRET": "client-secret",
    "HELIX_OAUTH_TENANT": "registration-workspace",
    "HELIX_OAUTH_REDIRECT_URI": "https://app.example.com/auth/helix/callback/",
    "HELIX_WORKSPACE_TENANT": "acme-corp",
}


class LoginPageViewTests(TestCase):
    def test_login_page_renders_django_form_by_default(self) -> None:
        response = self.client.get(reverse("authentication:login"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "id_email")
        self.assertContains(response, "id_password")
        self.assertNotContains(response, "Log in with Helix")

    @override_settings(**HELIX_SETTINGS)
    def test_login_page_renders_helix_button_when_configured(self) -> None:
        response = self.client.get(reverse("authentication:login"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Log in with Helix")
        self.assertNotContains(response, "id_email")

    def test_post_logs_in_with_valid_credentials(self) -> None:
        UserProfile.objects.create_user(email="ada@example.com", password="password123")
        response = self.client.post(
            reverse("authentication:login"), {"email": "ada@example.com", "password": "password123"}
        )
        self.assertRedirects(response, "/")
        self.assertIn("_auth_user_id", self.client.session)

    @override_settings(MFA_ENABLED=True)
    def test_post_redirects_to_mfa_verify_when_profile_has_confirmed_device(self) -> None:
        user = UserProfile.objects.create_user(email="ada@example.com", password="password123")
        device = MFAService().enroll(user)
        MFAService().confirm(user, pyotp.totp.TOTP(device.secret).now())

        response = self.client.post(
            reverse("authentication:login"), {"email": "ada@example.com", "password": "password123"}
        )

        self.assertRedirects(response, reverse("authentication:mfa-verify"))
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_post_with_invalid_credentials_rerenders_with_error(self) -> None:
        UserProfile.objects.create_user(email="ada@example.com", password="password123")
        response = self.client.post(
            reverse("authentication:login"), {"email": "ada@example.com", "password": "wrong-password"}
        )
        self.assertEqual(response.status_code, 400)
        self.assertContains(response, "Invalid email or password.", status_code=400)
        self.assertNotIn("_auth_user_id", self.client.session)

    @override_settings(**HELIX_SETTINGS)
    def test_post_returns_404_when_provider_is_helix(self) -> None:
        response = self.client.post(
            reverse("authentication:login"), {"email": "ada@example.com", "password": "password123"}
        )
        self.assertEqual(response.status_code, 404)

    def test_helix_login_returns_404_when_provider_is_django(self) -> None:
        response = self.client.get(reverse("authentication:helix-login"))
        self.assertEqual(response.status_code, 404)

    def test_helix_callback_returns_404_when_provider_is_django(self) -> None:
        response = self.client.get(reverse("authentication:helix-callback"), {"code": "auth-code", "state": "x"})
        self.assertEqual(response.status_code, 404)


@override_settings(**HELIX_SETTINGS)
class HelixLoginViewTests(TestCase):
    def test_get_redirects_to_helix_authorize_and_stores_session(self) -> None:
        response = self.client.get(reverse("authentication:helix-login"))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith("https://helix.example.com/auth/oauth/authorize/"))
        self.assertIn("tenant=registration-workspace", response.url)

        pending = self.client.session["helix_oauth"]
        self.assertIn("state", pending)
        self.assertIn("code_verifier", pending)
        self.assertIn(f"state={pending['state']}", response.url)


@override_settings(**HELIX_SETTINGS)
class HelixCallbackViewTests(TestCase):
    def _start_login(self) -> str:
        self.client.get(reverse("authentication:helix-login"))
        return self.client.session["helix_oauth"]["state"]

    def test_callback_creates_and_logs_in_new_user(self) -> None:
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

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "/")
        self.assertIn("_auth_user_id", self.client.session)
        profile = UserProfile.objects.get(email="ada@example.com")
        self.assertEqual(profile.helix_sub, "helix-sub-1")
        self.assertFalse(profile.has_usable_password())

    def test_callback_links_existing_account_by_email(self) -> None:
        existing = UserProfile.objects.create_user(email="ada@example.com", password="password123")
        state = self._start_login()
        with (
            patch.object(HelixInterface, "exchange_code", return_value={"access_token": "access-token"}),
            patch.object(
                HelixInterface, "userinfo", return_value={"sub": "helix-sub-1", "email": "ada@example.com"}
            ),
            patch.object(HelixInterface, "tenant_slugs", return_value=["acme-corp"]),
        ):
            self.client.get(reverse("authentication:helix-callback"), {"code": "auth-code", "state": state})

        self.assertEqual(UserProfile.objects.count(), 1)
        existing.refresh_from_db()
        self.assertEqual(existing.helix_sub, "helix-sub-1")

    @override_settings(MFA_ENABLED=True)
    def test_callback_redirects_to_mfa_verify_when_profile_has_confirmed_device(self) -> None:
        existing = UserProfile.objects.create_user(email="ada@example.com", password="password123")
        device = MFAService().enroll(existing)
        MFAService().confirm(existing, pyotp.totp.TOTP(device.secret).now())
        state = self._start_login()
        with (
            patch.object(HelixInterface, "exchange_code", return_value={"access_token": "access-token"}),
            patch.object(
                HelixInterface, "userinfo", return_value={"sub": "helix-sub-1", "email": "ada@example.com"}
            ),
            patch.object(HelixInterface, "tenant_slugs", return_value=["acme-corp"]),
        ):
            response = self.client.get(
                reverse("authentication:helix-callback"), {"code": "auth-code", "state": state}
            )

        self.assertRedirects(response, reverse("authentication:mfa-verify"))
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_callback_with_invalid_state_redirects_to_login(self) -> None:
        response = self.client.get(
            reverse("authentication:helix-callback"), {"code": "auth-code", "state": "bogus"}
        )
        self.assertRedirects(response, reverse("authentication:login"))
        self.assertNotIn("_auth_user_id", self.client.session)

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
        self.assertFalse(UserProfile.objects.filter(email="ada@example.com").exists())
        self.assertNotIn("_auth_user_id", self.client.session)


class LogoutViewTests(TestCase):
    def test_logout_clears_session(self) -> None:
        user = UserProfile.objects.create_user(email="ada@example.com", password="password123")
        self.client.force_login(user)
        response = self.client.post(reverse("authentication:logout"))
        self.assertRedirects(response, reverse("authentication:login"))
        self.assertNotIn("_auth_user_id", self.client.session)
