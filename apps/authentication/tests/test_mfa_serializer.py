from django.test import SimpleTestCase

from apps.authentication.serializers.mfa import MFACodeSerializer


class MFACodeSerializerTests(SimpleTestCase):
    def test_is_valid_when_code_is_present(self) -> None:
        serializer = MFACodeSerializer(data={"code": "123456"})

        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data, {"code": "123456"})

    def test_is_invalid_when_code_is_missing(self) -> None:
        serializer = MFACodeSerializer(data={})

        self.assertFalse(serializer.is_valid())
        self.assertIn("code", serializer.errors)

    def test_strips_surrounding_whitespace(self) -> None:
        serializer = MFACodeSerializer(data={"code": "  123456  "})

        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data["code"], "123456")
