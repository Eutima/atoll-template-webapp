from django.test import TestCase

from apps.authentication.filters.user_profile import UserProfileFilterSet
from apps.authentication.models.user_profile import UserProfile


class UserProfileFilterSetTests(TestCase):
    def setUp(self) -> None:
        self.ada = UserProfile.objects.create_user(
            email="ada@example.com", password="password123", first_name="Ada", last_name="Lovelace"
        )
        self.bob = UserProfile.objects.create_user(
            email="bob@example.com", password="password123", first_name="Bob", last_name="Smith", is_active=False
        )

    def test_search_matches_across_fields(self) -> None:
        filterset = UserProfileFilterSet(data={"search": "Lovelace"}, queryset=UserProfile.objects.all())
        self.assertQuerySetEqual(filterset.qs, [self.ada])

    def test_is_active_filter(self) -> None:
        filterset = UserProfileFilterSet(data={"is_active": "false"}, queryset=UserProfile.objects.all())
        self.assertQuerySetEqual(filterset.qs, [self.bob])

    def test_ordering_by_email_descending(self) -> None:
        filterset = UserProfileFilterSet(data={"ordering": "-email"}, queryset=UserProfile.objects.all())
        self.assertEqual(list(filterset.qs), [self.bob, self.ada])
