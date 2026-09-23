from django.db import models

from apps.shared.models import TimeStampedModel


class MFADeviceQuerySet(models.QuerySet):
    def confirmed(self) -> "MFADeviceQuerySet":
        return self.filter(confirmed_at__isnull=False)


class MFADeviceManager(models.Manager.from_queryset(MFADeviceQuerySet)):
    pass


class MFADevice(TimeStampedModel):
    user: models.OneToOneField = models.OneToOneField(
        "authentication.UserProfile", related_name="mfa_device", on_delete=models.CASCADE
    )
    secret: models.CharField = models.CharField(max_length=64)
    confirmed_at: models.DateTimeField = models.DateTimeField(null=True, blank=True)

    objects = MFADeviceManager()

    def __str__(self) -> str:
        return f"MFA device for {self.user_id}"


class MFABackupCodeQuerySet(models.QuerySet):
    def unused(self) -> "MFABackupCodeQuerySet":
        return self.filter(used_at__isnull=True)


class MFABackupCodeManager(models.Manager.from_queryset(MFABackupCodeQuerySet)):
    pass


class MFABackupCode(TimeStampedModel):
    device: models.ForeignKey = models.ForeignKey(MFADevice, related_name="backup_codes", on_delete=models.CASCADE)
    code_hash: models.CharField = models.CharField(max_length=128)
    used_at: models.DateTimeField = models.DateTimeField(null=True, blank=True)

    objects = MFABackupCodeManager()

    def __str__(self) -> str:
        return f"Backup code for device {self.device_id}"
