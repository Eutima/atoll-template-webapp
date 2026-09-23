from django.conf import settings
from django.contrib.auth import login
from django.http import HttpRequest
from django.utils import timezone
from l4py import get_logger

from apps.authentication.lib import totp
from apps.authentication.models.mfa_device import MFABackupCode, MFADevice
from apps.authentication.models.user_profile import UserProfile
from apps.shared.exceptions import NotFoundError, ValidationError

logger = get_logger()

PENDING_SESSION_KEY = "mfa_pending_user_id"


class MFAService:
    def enroll(self, user: UserProfile) -> MFADevice:
        if MFADevice.objects.confirmed().filter(user=user).exists():
            raise ValidationError({"__all__": ["MFA is already enabled."]})
        device, _ = MFADevice.objects.update_or_create(
            user=user, defaults={"secret": totp.generate_secret(), "confirmed_at": None}
        )
        return device

    def confirm(self, user: UserProfile, code: str) -> list[str]:
        device = MFADevice.objects.filter(user=user, confirmed_at__isnull=True).first()
        if device is None:
            raise ValidationError({"__all__": ["No pending MFA enrollment."]})
        if not totp.verify_code(device.secret, code):
            raise ValidationError({"code": ["Invalid code."]})

        device.confirmed_at = timezone.now()
        device.save(update_fields=["confirmed_at", "updated_at"])

        backup_codes = totp.generate_backup_codes()
        MFABackupCode.objects.bulk_create(
            MFABackupCode(device=device, code_hash=totp.hash_backup_code(backup_code)) for backup_code in backup_codes
        )
        logger.info("Confirmed MFA device for UserProfile id=%s", user.id)
        return backup_codes

    def disable(self, user: UserProfile) -> None:
        deleted, _ = MFADevice.objects.filter(user=user).delete()
        if not deleted:
            raise NotFoundError("MFA is not enabled for this user.")
        logger.info("Disabled MFA for UserProfile id=%s", user.id)

    def complete_login(self, request: HttpRequest, profile: UserProfile) -> bool:
        device = MFADevice.objects.confirmed().filter(user=profile).first()
        if settings.MFA_ENABLED and device is not None:
            request.session[PENDING_SESSION_KEY] = profile.pk
            return False
        login(request, profile)
        return True

    def verify_login_code(self, request: HttpRequest, code: str) -> UserProfile:
        pending_id = request.session.get(PENDING_SESSION_KEY)
        if pending_id is None:
            raise ValidationError({"__all__": ["No pending login."]})

        try:
            profile = UserProfile.objects.get(pk=pending_id)
        except UserProfile.DoesNotExist as exc:
            raise ValidationError({"__all__": ["No pending login."]}) from exc

        device = MFADevice.objects.confirmed().filter(user=profile).first()
        if device is None or not self._code_matches(device, code):
            raise ValidationError({"code": ["Invalid code."]})

        del request.session[PENDING_SESSION_KEY]
        login(request, profile)
        return profile

    def _code_matches(self, device: MFADevice, code: str) -> bool:
        if totp.verify_code(device.secret, code):
            return True

        code_hash = totp.hash_backup_code(code)
        backup_code = device.backup_codes.unused().filter(code_hash=code_hash).first()
        if backup_code is None:
            return False
        backup_code.used_at = timezone.now()
        backup_code.save(update_fields=["used_at", "updated_at"])
        return True
