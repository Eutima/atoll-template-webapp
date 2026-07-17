from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.test import RequestFactory, SimpleTestCase, TestCase
from django.views import View

from apps.authentication.models.user_profile import UserProfile
from apps.authentication.permissions.user_profile import StaffRequiredMixin, is_self_or_staff


class _StaffOnlyView(StaffRequiredMixin, View):
    def get(self, request, *args, **kwargs) -> HttpResponse:
        return HttpResponse("ok")


class IsSelfOrStaffTests(TestCase):
    def test_true_when_same_user(self) -> None:
        user = UserProfile.objects.create_user(email="ada@example.com", password="password123")
        self.assertTrue(is_self_or_staff(user, user))

    def test_true_when_staff(self) -> None:
        staff = UserProfile.objects.create_user(email="staff@example.com", password="password123", is_staff=True)
        other = UserProfile.objects.create_user(email="other@example.com", password="password123")
        self.assertTrue(is_self_or_staff(staff, other))

    def test_false_for_unrelated_non_staff_user(self) -> None:
        user = UserProfile.objects.create_user(email="ada@example.com", password="password123")
        other = UserProfile.objects.create_user(email="other@example.com", password="password123")
        self.assertFalse(is_self_or_staff(user, other))


class StaffRequiredMixinTests(TestCase):
    def setUp(self) -> None:
        self.factory = RequestFactory()

    def test_raises_permission_denied_for_non_staff(self) -> None:
        request = self.factory.get("/")
        request.user = UserProfile.objects.create_user(email="ada@example.com", password="password123")
        with self.assertRaises(PermissionDenied):
            _StaffOnlyView().dispatch(request)

    def test_allows_staff_user(self) -> None:
        request = self.factory.get("/")
        request.user = UserProfile.objects.create_user(
            email="staff@example.com", password="password123", is_staff=True
        )
        response = _StaffOnlyView().dispatch(request)
        self.assertEqual(response.status_code, 200)


class StaffRequiredMixinAnonymousTests(SimpleTestCase):
    def test_raises_permission_denied_for_anonymous(self) -> None:
        from django.contrib.auth.models import AnonymousUser

        request = RequestFactory().get("/")
        request.user = AnonymousUser()
        with self.assertRaises(PermissionDenied):
            _StaffOnlyView().dispatch(request)
