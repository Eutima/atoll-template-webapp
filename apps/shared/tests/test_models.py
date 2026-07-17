import uuid

from django.test import SimpleTestCase

from apps.shared.models import TimeStampedModel, UUIDModel


class TimeStampedModelTests(SimpleTestCase):
    def test_is_abstract(self) -> None:
        self.assertTrue(TimeStampedModel._meta.abstract)

    def test_has_created_at_auto_now_add(self) -> None:
        field = TimeStampedModel._meta.get_field("created_at")
        self.assertTrue(field.auto_now_add)

    def test_has_updated_at_auto_now(self) -> None:
        field = TimeStampedModel._meta.get_field("updated_at")
        self.assertTrue(field.auto_now)


class UUIDModelTests(SimpleTestCase):
    def test_is_abstract(self) -> None:
        self.assertTrue(UUIDModel._meta.abstract)

    def test_id_field_is_uuid_primary_key(self) -> None:
        field = UUIDModel._meta.get_field("id")
        self.assertTrue(field.primary_key)
        self.assertFalse(field.editable)
        self.assertIsInstance(field.default(), uuid.UUID)
