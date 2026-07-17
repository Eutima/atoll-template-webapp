from django.test import SimpleTestCase

from apps.shared.exceptions import SerializerValidationError
from apps.shared.serializers import BaseSerializer


class _NameSerializer(BaseSerializer):
    def fields(self) -> list[str]:
        return ["name"]

    def validate_name(self, value: str | None) -> str:
        if not value:
            raise SerializerValidationError(["name is required."])
        return value.strip()

    def to_representation(self, instance: dict) -> dict:
        return {"name": instance["name"].upper()}


class BaseSerializerTests(SimpleTestCase):
    def test_is_valid_true_and_populates_validated_data(self) -> None:
        serializer = _NameSerializer(data={"name": "  ada  "})
        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data, {"name": "ada"})
        self.assertEqual(serializer.errors, {})

    def test_is_valid_false_and_populates_errors(self) -> None:
        serializer = _NameSerializer(data={"name": ""})
        self.assertFalse(serializer.is_valid())
        self.assertIn("name", serializer.errors)

    def test_data_property_uses_validated_data_without_instance(self) -> None:
        serializer = _NameSerializer(data={"name": "ada"})
        serializer.is_valid()
        self.assertEqual(serializer.data, {"name": "ada"})

    def test_data_property_uses_representation_with_instance(self) -> None:
        serializer = _NameSerializer(instance={"name": "ada"})
        self.assertEqual(serializer.data, {"name": "ADA"})
