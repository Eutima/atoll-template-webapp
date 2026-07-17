from django.test import TestCase

from apps.authentication.models.user_profile import UserProfile
from apps.authentication.services.user_profile import UserProfileService
from apps.shared.exceptions import NotFoundError, ValidationError


class UserProfileServiceTests(TestCase):
    def setUp(self) -> None:
        self.service = UserProfileService()

    def test_create_success(self) -> None:
        profile = self.service.create(email="ada@example.com", password="password123", first_name="Ada")
        self.assertTrue(UserProfile.objects.filter(pk=profile.pk).exists())
        self.assertTrue(profile.check_password("password123"))

    def test_create_duplicate_email_raises_validation_error(self) -> None:
        self.service.create(email="ada@example.com", password="password123")
        with self.assertRaises(ValidationError) as ctx:
            self.service.create(email="ada@example.com", password="password123")
        self.assertIn("email", ctx.exception.errors)

    def test_by_id_missing_raises_not_found(self) -> None:
        with self.assertRaises(NotFoundError):
            self.service.by_id(999999)

    def test_by_id_found(self) -> None:
        profile = self.service.create(email="ada@example.com", password="password123")
        self.assertEqual(self.service.by_id(profile.pk), profile)

    def test_update_changes_fields(self) -> None:
        profile = self.service.create(email="ada@example.com", password="password123")
        updated = self.service.update(profile.pk, first_name="Ada", last_name="Lovelace")
        self.assertEqual(updated.first_name, "Ada")
        self.assertEqual(updated.last_name, "Lovelace")

    def test_delete_removes_profile(self) -> None:
        profile = self.service.create(email="ada@example.com", password="password123")
        self.service.delete(profile.pk)
        self.assertFalse(UserProfile.objects.filter(pk=profile.pk).exists())

    def test_activate_sets_is_active_true(self) -> None:
        profile = self.service.create(email="ada@example.com", password="password123")
        self.service.deactivate(profile.pk)
        activated = self.service.activate(profile.pk)
        self.assertTrue(activated.is_active)

    def test_deactivate_sets_is_active_false(self) -> None:
        profile = self.service.create(email="ada@example.com", password="password123")
        deactivated = self.service.deactivate(profile.pk)
        self.assertFalse(deactivated.is_active)

    def test_search_filters_active_profiles_only(self) -> None:
        active = self.service.create(email="active@example.com", password="password123", first_name="Ada")
        inactive = self.service.create(email="inactive@example.com", password="password123", first_name="Ada")
        self.service.deactivate(inactive.pk)
        results = self.service.search("Ada")
        self.assertIn(active, results)
        self.assertNotIn(inactive, results)
