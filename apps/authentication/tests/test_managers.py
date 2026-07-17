from django.test import TestCase

from apps.authentication.models.user_profile import UserProfile


class UserProfileManagerTests(TestCase):
    def test_create_user_normalizes_email_and_hashes_password(self) -> None:
        profile = UserProfile.objects.create_user(email="Ada@Example.COM", password="password123")
        self.assertEqual(profile.email, "Ada@example.com")
        self.assertTrue(profile.check_password("password123"))
        self.assertFalse(profile.is_staff)
        self.assertFalse(profile.is_superuser)

    def test_create_user_without_email_raises(self) -> None:
        with self.assertRaises(ValueError):
            UserProfile.objects.create_user(email="", password="password123")

    def test_create_superuser_sets_flags(self) -> None:
        profile = UserProfile.objects.create_superuser(email="admin@example.com", password="password123")
        self.assertTrue(profile.is_staff)
        self.assertTrue(profile.is_superuser)

    def test_create_superuser_rejects_is_staff_false(self) -> None:
        with self.assertRaises(ValueError):
            UserProfile.objects.create_superuser(email="admin@example.com", password="password123", is_staff=False)

    def test_create_superuser_rejects_is_superuser_false(self) -> None:
        with self.assertRaises(ValueError):
            UserProfile.objects.create_superuser(
                email="admin@example.com", password="password123", is_superuser=False
            )


class UserProfileQuerySetTests(TestCase):
    def setUp(self) -> None:
        self.active = UserProfile.objects.create_user(
            email="active@example.com", password="password123", first_name="Ada"
        )
        self.inactive = UserProfile.objects.create_user(
            email="inactive@example.com", password="password123", is_active=False
        )

    def test_active_excludes_inactive_profiles(self) -> None:
        self.assertQuerySetEqual(UserProfile.objects.active(), [self.active], ordered=False)

    def test_with_email_is_case_insensitive(self) -> None:
        self.assertEqual(UserProfile.objects.with_email("ACTIVE@example.com").get(), self.active)

    def test_search_matches_email_or_name(self) -> None:
        self.assertIn(self.active, UserProfile.objects.search("Ada"))
        self.assertIn(self.active, UserProfile.objects.search("active@example"))
        self.assertNotIn(self.inactive, UserProfile.objects.search("Ada"))
