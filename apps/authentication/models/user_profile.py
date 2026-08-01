from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import PermissionsMixin
from django.db import models

from apps.shared.models import TimeStampedModel


class UserProfileQuerySet(models.QuerySet):
    def active(self) -> "UserProfileQuerySet":
        return self.filter(is_active=True)

    def staff(self) -> "UserProfileQuerySet":
        return self.filter(is_staff=True)

    def with_email(self, email: str) -> "UserProfileQuerySet":
        return self.filter(email__iexact=email)

    def search(self, term: str) -> "UserProfileQuerySet":
        return self.filter(
            models.Q(email__icontains=term)
            | models.Q(first_name__icontains=term)
            | models.Q(last_name__icontains=term)
        )


class UserProfileManager(BaseUserManager.from_queryset(UserProfileQuerySet)):
    use_in_migrations = True

    def _create_user(self, email: str, password: str | None, **extra_fields: object) -> "UserProfile":
        if not email:
            raise ValueError("The email must be set")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email: str, password: str | None = None, **extra_fields: object) -> "UserProfile":
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email: str, password: str | None = None, **extra_fields: object) -> "UserProfile":
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")
        return self._create_user(email, password, **extra_fields)


class UserProfile(AbstractBaseUser, PermissionsMixin, TimeStampedModel):
    email: models.EmailField = models.EmailField(unique=True)
    first_name: models.CharField = models.CharField(max_length=150, blank=True)
    last_name: models.CharField = models.CharField(max_length=150, blank=True)
    is_active: models.BooleanField = models.BooleanField(default=True)
    is_staff: models.BooleanField = models.BooleanField(default=False)
    helix_sub: models.CharField = models.CharField(max_length=255, unique=True, null=True, blank=True)

    objects = UserProfileManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS: list[str] = []

    class Meta:
        ordering = ["email"]

    def __str__(self) -> str:
        return self.email

    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip() or self.email
