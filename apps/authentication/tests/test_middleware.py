import pyotp
from django.test import TestCase, override_settings
from django.urls import reverse

from apps.authentication.models.user_profile import UserProfile
from apps.authentication.services.mfa import MFAService


def _create_user() -> UserProfile:
    return UserProfile.objects.create_user(email="ada@example.com", password="password123")


class MFAEnforcementMiddlewareTests(TestCase):
    def test_does_not_redirect_when_mfa_disabled(self) -> None:
        self.client.force_login(_create_user())
        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 200)

    def test_does_not_redirect_anonymous_requests(self) -> None:
        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("authentication:login"), response["Location"])

    @override_settings(MFA_ENABLED=True)
    def test_redirects_authenticated_user_without_a_device_to_mfa_setup(self) -> None:
        self.client.force_login(_create_user())
        response = self.client.get(reverse("home"))
        self.assertRedirects(response, reverse("authentication:mfa-setup"), fetch_redirect_response=False)

    @override_settings(MFA_ENABLED=True)
    def test_does_not_redirect_user_with_a_confirmed_device(self) -> None:
        user = _create_user()
        device = MFAService().enroll(user)
        MFAService().confirm(user, pyotp.totp.TOTP(device.secret).now())
        self.client.force_login(user)

        response = self.client.get(reverse("home"))

        self.assertEqual(response.status_code, 200)

    @override_settings(MFA_ENABLED=True)
    def test_exempt_paths_stay_reachable_without_a_device(self) -> None:
        self.client.force_login(_create_user())

        for url in (reverse("authentication:logout"), reverse("authentication:mfa-setup"), "/metrics"):
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertNotEqual(response.status_code, 302)
