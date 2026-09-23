from django.test import RequestFactory, TestCase

from apps.authentication.models.user_profile import UserProfile
from apps.authentication.services.django_login import DjangoLoginService
from apps.shared.exceptions import ValidationError


class DjangoLoginServiceTests(TestCase):
    def setUp(self) -> None:
        self.factory = RequestFactory()
        self.service = DjangoLoginService()

    def test_authenticate_returns_profile_when_credentials_are_valid(self) -> None:
        UserProfile.objects.create_user(email="ada@example.com", password="password123")
        request = self.factory.post("/auth/login/")

        profile = self.service.authenticate(request, email="ada@example.com", password="password123")

        self.assertEqual(profile.email, "ada@example.com")

    def test_authenticate_raises_validation_error_when_password_is_wrong(self) -> None:
        UserProfile.objects.create_user(email="ada@example.com", password="password123")
        request = self.factory.post("/auth/login/")

        with self.assertRaises(ValidationError):
            self.service.authenticate(request, email="ada@example.com", password="wrong-password")

    def test_authenticate_raises_validation_error_when_email_is_unknown(self) -> None:
        request = self.factory.post("/auth/login/")

        with self.assertRaises(ValidationError):
            self.service.authenticate(request, email="unknown@example.com", password="password123")

    def test_authenticate_raises_validation_error_when_profile_is_inactive(self) -> None:
        profile = UserProfile.objects.create_user(email="ada@example.com", password="password123")
        profile.is_active = False
        profile.save(update_fields=["is_active"])
        request = self.factory.post("/auth/login/")

        with self.assertRaises(ValidationError):
            self.service.authenticate(request, email="ada@example.com", password="password123")
