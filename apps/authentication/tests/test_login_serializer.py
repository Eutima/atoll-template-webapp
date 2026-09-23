from django.test import SimpleTestCase

from apps.authentication.serializers.login import LoginSerializer


class LoginSerializerTests(SimpleTestCase):
    def test_is_valid_when_email_and_password_are_present(self) -> None:
        serializer = LoginSerializer(data={"email": "ada@example.com", "password": "password123"})

        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data, {"email": "ada@example.com", "password": "password123"})

    def test_is_invalid_when_email_is_missing(self) -> None:
        serializer = LoginSerializer(data={"password": "password123"})

        self.assertFalse(serializer.is_valid())
        self.assertIn("email", serializer.errors)

    def test_is_invalid_when_password_is_missing(self) -> None:
        serializer = LoginSerializer(data={"email": "ada@example.com"})

        self.assertFalse(serializer.is_valid())
        self.assertIn("password", serializer.errors)
