from django.db import IntegrityError, transaction
from django.test import TestCase

from apps.authentication.models.user_profile import UserProfile


class UserProfileModelTests(TestCase):
    def test_str_returns_email(self) -> None:
        profile = UserProfile.objects.create_user(email="ada@example.com", password="password123")
        self.assertEqual(str(profile), "ada@example.com")

    def test_full_name_combines_first_and_last(self) -> None:
        profile = UserProfile.objects.create_user(
            email="ada@example.com", password="password123", first_name="Ada", last_name="Lovelace"
        )
        self.assertEqual(profile.full_name(), "Ada Lovelace")

    def test_full_name_falls_back_to_email_when_blank(self) -> None:
        profile = UserProfile.objects.create_user(email="ada@example.com", password="password123")
        self.assertEqual(profile.full_name(), "ada@example.com")

    def test_email_must_be_unique(self) -> None:
        UserProfile.objects.create_user(email="ada@example.com", password="password123")
        with self.assertRaises(IntegrityError), transaction.atomic():
            UserProfile.objects.create_user(email="ada@example.com", password="password123")

    def test_timestamps_are_populated_on_create(self) -> None:
        profile = UserProfile.objects.create_user(email="ada@example.com", password="password123")
        self.assertIsNotNone(profile.created_at)
        self.assertIsNotNone(profile.updated_at)
