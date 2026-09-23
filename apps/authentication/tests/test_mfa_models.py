from django.test import TestCase
from django.utils import timezone

from apps.authentication.models.mfa_device import MFABackupCode, MFADevice
from apps.authentication.models.user_profile import UserProfile


def _create_user() -> UserProfile:
    return UserProfile.objects.create_user(email="ada@example.com", password="password123")


class MFADeviceModelTests(TestCase):
    def test_str_includes_user_id(self) -> None:
        user = _create_user()
        device = MFADevice.objects.create(user=user, secret="JBSWY3DPEHPK3PXP")
        self.assertEqual(str(device), f"MFA device for {user.id}")


class MFADeviceQuerySetTests(TestCase):
    def test_confirmed_excludes_unconfirmed_devices(self) -> None:
        confirmed_user = _create_user()
        unconfirmed_user = UserProfile.objects.create_user(email="bob@example.com", password="password123")
        confirmed = MFADevice.objects.create(
            user=confirmed_user, secret="JBSWY3DPEHPK3PXP", confirmed_at=timezone.now()
        )
        MFADevice.objects.create(user=unconfirmed_user, secret="JBSWY3DPEHPK3PXP")

        self.assertQuerySetEqual(MFADevice.objects.confirmed(), [confirmed], ordered=False)


class MFABackupCodeQuerySetTests(TestCase):
    def test_unused_excludes_used_codes(self) -> None:
        device = MFADevice.objects.create(user=_create_user(), secret="JBSWY3DPEHPK3PXP")
        unused = MFABackupCode.objects.create(device=device, code_hash="hash-a")
        MFABackupCode.objects.create(device=device, code_hash="hash-b", used_at=timezone.now())

        self.assertQuerySetEqual(device.backup_codes.unused(), [unused], ordered=False)
