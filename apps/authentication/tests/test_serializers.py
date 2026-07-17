from django.test import SimpleTestCase, TestCase

from apps.authentication.models.user_profile import UserProfile
from apps.authentication.serializers.user_profile import SignUpSerializer, UserProfileSerializer


class SignUpSerializerTests(SimpleTestCase):
    def test_valid_data_passes(self) -> None:
        serializer = SignUpSerializer(
            data={"email": "Ada@Example.com", "password": "password123", "first_name": "Ada"}
        )
        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data["email"], "ada@example.com")
        self.assertEqual(serializer.validated_data["password"], "password123")

    def test_invalid_email_produces_error(self) -> None:
        serializer = SignUpSerializer(data={"email": "not-an-email", "password": "password123"})
        self.assertFalse(serializer.is_valid())
        self.assertIn("email", serializer.errors)

    def test_short_password_produces_error(self) -> None:
        serializer = SignUpSerializer(data={"email": "ada@example.com", "password": "short"})
        self.assertFalse(serializer.is_valid())
        self.assertIn("password", serializer.errors)

    def test_missing_password_produces_error(self) -> None:
        serializer = SignUpSerializer(data={"email": "ada@example.com"})
        self.assertFalse(serializer.is_valid())
        self.assertIn("password", serializer.errors)


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
