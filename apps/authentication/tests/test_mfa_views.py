import pyotp
from django.test import TestCase, override_settings
from django.urls import reverse

from apps.authentication.models.mfa_device import MFADevice
from apps.authentication.models.user_profile import UserProfile
from apps.authentication.services.mfa import MFAService


def _create_user() -> UserProfile:
    return UserProfile.objects.create_user(email="ada@example.com", password="password123")


class MFASetupViewTests(TestCase):
    def test_returns_404_when_mfa_disabled(self) -> None:
        self.client.force_login(_create_user())
        response = self.client.get(reverse("authentication:mfa-setup"))
        self.assertEqual(response.status_code, 404)

    def test_redirects_anonymous_user_to_login(self) -> None:
        response = self.client.get(reverse("authentication:mfa-setup"))
        self.assertRedirects(response, f"{reverse('authentication:login')}?next={reverse('authentication:mfa-setup')}")

    @override_settings(MFA_ENABLED=True)
    def test_get_shows_qr_code_for_fresh_enrollment(self) -> None:
        self.client.force_login(_create_user())
        response = self.client.get(reverse("authentication:mfa-setup"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "<svg")

    @override_settings(MFA_ENABLED=True)
    def test_get_shows_status_page_when_already_confirmed(self) -> None:
        user = _create_user()
        device = MFAService().enroll(user)
        MFAService().confirm(user, pyotp.totp.TOTP(device.secret).now())

        self.client.force_login(user)
        response = self.client.get(reverse("authentication:mfa-setup"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "MFA is on")

    @override_settings(MFA_ENABLED=True)
    def test_post_with_valid_code_confirms_and_shows_backup_codes(self) -> None:
        user = _create_user()
        self.client.force_login(user)
        self.client.get(reverse("authentication:mfa-setup"))
        secret = MFADevice.objects.get(user=user).secret

        response = self.client.post(
            reverse("authentication:mfa-setup"), {"code": pyotp.totp.TOTP(secret).now()}
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "backup codes")
        self.assertTrue(MFADevice.objects.confirmed().filter(user=user).exists())

    @override_settings(MFA_ENABLED=True)
    def test_post_with_invalid_code_rerenders_with_error(self) -> None:
        user = _create_user()
        self.client.force_login(user)
        self.client.get(reverse("authentication:mfa-setup"))

        response = self.client.post(reverse("authentication:mfa-setup"), {"code": "000000"})

        self.assertEqual(response.status_code, 400)
        self.assertContains(response, "Invalid code.", status_code=400)
        self.assertFalse(MFADevice.objects.confirmed().filter(user=user).exists())


@override_settings(MFA_ENABLED=True)
class MFADisableViewTests(TestCase):
    def test_deletes_the_device_and_redirects(self) -> None:
        user = _create_user()
        device = MFAService().enroll(user)
        MFAService().confirm(user, pyotp.totp.TOTP(device.secret).now())
        self.client.force_login(user)

        response = self.client.post(reverse("authentication:mfa-disable"))

        self.assertRedirects(response, reverse("authentication:mfa-setup"), fetch_redirect_response=False)
        self.assertFalse(MFADevice.objects.confirmed().filter(user=user).exists())

    def test_returns_404_when_no_device_exists(self) -> None:
        self.client.force_login(_create_user())
        response = self.client.post(reverse("authentication:mfa-disable"))
        self.assertEqual(response.status_code, 404)


@override_settings(MFA_ENABLED=True)
class MFAVerifyViewTests(TestCase):
    def _log_in_with_mfa(self) -> tuple[UserProfile, str]:
        user = _create_user()
        device = MFAService().enroll(user)
        MFAService().confirm(user, pyotp.totp.TOTP(device.secret).now())
        self.client.post(reverse("authentication:login"), {"email": user.email, "password": "password123"})
        return user, device.secret

    def test_get_redirects_to_login_without_a_pending_login(self) -> None:
        response = self.client.get(reverse("authentication:mfa-verify"))
        self.assertRedirects(response, reverse("authentication:login"))

    def test_login_with_mfa_enabled_does_not_authenticate_immediately(self) -> None:
        user, _ = self._log_in_with_mfa()
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_get_renders_challenge_form_with_pending_login(self) -> None:
        self._log_in_with_mfa()
        response = self.client.get(reverse("authentication:mfa-verify"))
        self.assertEqual(response.status_code, 200)

    def test_post_with_valid_code_logs_in_and_redirects_home(self) -> None:
        user, secret = self._log_in_with_mfa()
        response = self.client.post(reverse("authentication:mfa-verify"), {"code": pyotp.totp.TOTP(secret).now()})
        self.assertRedirects(response, "/")
        self.assertIn("_auth_user_id", self.client.session)

    def test_post_with_invalid_code_rerenders_with_error(self) -> None:
        self._log_in_with_mfa()
        response = self.client.post(reverse("authentication:mfa-verify"), {"code": "000000"})
        self.assertEqual(response.status_code, 400)
        self.assertNotIn("_auth_user_id", self.client.session)
