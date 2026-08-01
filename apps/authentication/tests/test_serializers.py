from django.test import TestCase

from apps.authentication.models.user_profile import UserProfile
from apps.authentication.serializers.user_profile import UserProfileSerializer


class UserProfileSerializerTests(TestCase):
    def test_to_representation_shape(self) -> None:
        profile = UserProfile.objects.create_user(
            email="ada@example.com", password="password123", first_name="Ada", last_name="Lovelace"
        )
        data = UserProfileSerializer(instance=profile).data
        self.assertEqual(
            data,
            {"id": profile.id, "email": "ada@example.com", "full_name": "Ada Lovelace", "is_active": True},
        )
