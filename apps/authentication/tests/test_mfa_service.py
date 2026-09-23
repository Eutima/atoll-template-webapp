import pyotp
from django.contrib.sessions.middleware import SessionMiddleware
from django.http import HttpRequest
from django.test import RequestFactory, TestCase, override_settings

from apps.authentication.lib import totp
from apps.authentication.models.mfa_device import MFABackupCode, MFADevice
from apps.authentication.models.user_profile import UserProfile
from apps.authentication.services.mfa import PENDING_SESSION_KEY, MFAService
from apps.shared.exceptions import NotFoundError, ValidationError


def _create_user() -> UserProfile:
    return UserProfile.objects.create_user(email="ada@example.com", password="password123")


def _request() -> HttpRequest:
    request = RequestFactory().get("/")
    SessionMiddleware(lambda r: None).process_request(request)
    request.session.save()
    return request


class EnrollTests(TestCase):
    def setUp(self) -> None:
        self.service = MFAService()
        self.user = _create_user()

    def test_creates_unconfirmed_device_with_a_secret(self) -> None:
        device = self.service.enroll(self.user)
        self.assertIsNone(device.confirmed_at)
        self.assertTrue(device.secret)

    def test_re_enrolling_while_unconfirmed_regenerates_the_secret(self) -> None:
        first = self.service.enroll(self.user)
        second = self.service.enroll(self.user)
        self.assertEqual(MFADevice.objects.filter(user=self.user).count(), 1)
        self.assertNotEqual(first.secret, second.secret)

    def test_raises_when_already_confirmed(self) -> None:
        device = self.service.enroll(self.user)
        self.service.confirm(self.user, pyotp.totp.TOTP(device.secret).now())

        with self.assertRaises(ValidationError):
            self.service.enroll(self.user)


class ConfirmTests(TestCase):
    def setUp(self) -> None:
        self.service = MFAService()
        self.user = _create_user()

    def test_confirms_device_and_returns_ten_backup_codes(self) -> None:
        device = self.service.enroll(self.user)
        codes = self.service.confirm(self.user, pyotp.totp.TOTP(device.secret).now())

        device.refresh_from_db()
        self.assertIsNotNone(device.confirmed_at)
        self.assertEqual(len(codes), 10)
        self.assertEqual(MFABackupCode.objects.filter(device=device).count(), 10)

    def test_raises_when_no_pending_enrollment(self) -> None:
        with self.assertRaises(ValidationError):
            self.service.confirm(self.user, "123456")

    def test_raises_when_code_is_invalid(self) -> None:
        self.service.enroll(self.user)
        with self.assertRaises(ValidationError):
            self.service.confirm(self.user, "000000")


class DisableTests(TestCase):
    def setUp(self) -> None:
        self.service = MFAService()
        self.user = _create_user()

    def test_deletes_the_device(self) -> None:
        device = self.service.enroll(self.user)
        self.service.confirm(self.user, pyotp.totp.TOTP(device.secret).now())

        self.service.disable(self.user)

        self.assertFalse(MFADevice.objects.filter(user=self.user).exists())

    def test_raises_when_no_device_exists(self) -> None:
        with self.assertRaises(NotFoundError):
            self.service.disable(self.user)


class CompleteLoginTests(TestCase):
    def setUp(self) -> None:
        self.service = MFAService()
        self.user = _create_user()

    @override_settings(MFA_ENABLED=False)
    def test_logs_in_directly_when_mfa_disabled_globally(self) -> None:
        request = _request()
        result = self.service.complete_login(request, self.user)
        self.assertTrue(result)
        self.assertIn("_auth_user_id", request.session)

    @override_settings(MFA_ENABLED=True)
    def test_logs_in_directly_when_user_has_no_confirmed_device(self) -> None:
        request = _request()
        result = self.service.complete_login(request, self.user)
        self.assertTrue(result)
        self.assertIn("_auth_user_id", request.session)

    @override_settings(MFA_ENABLED=True)
    def test_challenges_when_user_has_a_confirmed_device(self) -> None:
        device = self.service.enroll(self.user)
        self.service.confirm(self.user, pyotp.totp.TOTP(device.secret).now())
        request = _request()

        result = self.service.complete_login(request, self.user)

        self.assertFalse(result)
        self.assertNotIn("_auth_user_id", request.session)
        self.assertEqual(request.session[PENDING_SESSION_KEY], self.user.pk)


class VerifyLoginCodeTests(TestCase):
    def setUp(self) -> None:
        self.service = MFAService()
        self.user = _create_user()
        device = self.service.enroll(self.user)
        self.backup_codes = self.service.confirm(self.user, pyotp.totp.TOTP(device.secret).now())
        self.device = device

    def _pending_request(self) -> HttpRequest:
        request = _request()
        request.session[PENDING_SESSION_KEY] = self.user.pk
        return request

    def test_raises_when_no_pending_login(self) -> None:
        request = _request()
        with self.assertRaises(ValidationError):
            self.service.verify_login_code(request, "123456")

    def test_logs_in_and_clears_pending_state_on_valid_totp_code(self) -> None:
        request = self._pending_request()
        code = pyotp.totp.TOTP(self.device.secret).now()

        profile = self.service.verify_login_code(request, code)

        self.assertEqual(profile, self.user)
        self.assertIn("_auth_user_id", request.session)
        self.assertNotIn(PENDING_SESSION_KEY, request.session)

    def test_raises_on_invalid_code(self) -> None:
        request = self._pending_request()
        with self.assertRaises(ValidationError):
            self.service.verify_login_code(request, "000000")

    def test_logs_in_with_a_backup_code_and_consumes_it(self) -> None:
        request = self._pending_request()
        backup_code = self.backup_codes[0]

        self.service.verify_login_code(request, backup_code)

        used = MFABackupCode.objects.get(code_hash=totp.hash_backup_code(backup_code))
        self.assertIsNotNone(used.used_at)

    def test_a_backup_code_cannot_be_reused(self) -> None:
        backup_code = self.backup_codes[0]
        self.service.verify_login_code(self._pending_request(), backup_code)

        with self.assertRaises(ValidationError):
            self.service.verify_login_code(self._pending_request(), backup_code)
