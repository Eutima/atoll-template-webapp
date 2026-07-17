from django.test import TestCase
from django.urls import reverse

from apps.authentication.models.user_profile import UserProfile


class LoginViewTests(TestCase):
    def setUp(self) -> None:
        self.user = UserProfile.objects.create_user(email="ada@example.com", password="password123")

    def test_login_success_redirects(self) -> None:
        response = self.client.post(
            reverse("authentication:login"), {"username": "ada@example.com", "password": "password123"}
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn("_auth_user_id", self.client.session)

    def test_login_failure_rerenders_with_error(self) -> None:
        response = self.client.post(
            reverse("authentication:login"), {"username": "ada@example.com", "password": "wrong"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("_auth_user_id", self.client.session)


class LogoutViewTests(TestCase):
    def test_logout_clears_session(self) -> None:
        user = UserProfile.objects.create_user(email="ada@example.com", password="password123")
        self.client.force_login(user)
        response = self.client.post(reverse("authentication:logout"))
        self.assertRedirects(response, reverse("authentication:login"))
        self.assertNotIn("_auth_user_id", self.client.session)


class SignUpViewTests(TestCase):
    def test_signup_success_creates_user_and_logs_in(self) -> None:
        response = self.client.post(
            reverse("authentication:signup"),
            {"email": "ada@example.com", "password": "password123", "first_name": "Ada", "last_name": ""},
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(UserProfile.objects.filter(email="ada@example.com").exists())
        self.assertIn("_auth_user_id", self.client.session)

    def test_signup_validation_failure_returns_422(self) -> None:
        response = self.client.post(
            reverse("authentication:signup"), {"email": "not-an-email", "password": "short"}
        )
        self.assertEqual(response.status_code, 422)
        self.assertFalse(UserProfile.objects.filter(email="not-an-email").exists())

    def test_signup_duplicate_email_returns_422(self) -> None:
        UserProfile.objects.create_user(email="ada@example.com", password="password123")
        response = self.client.post(
            reverse("authentication:signup"),
            {"email": "ada@example.com", "password": "password123", "first_name": "", "last_name": ""},
        )
        self.assertEqual(response.status_code, 422)


class UserProfileSearchViewTests(TestCase):
    def setUp(self) -> None:
        self.url = reverse("demo:searchable-select-search")

    def test_empty_results_shows_no_results_state(self) -> None:
        response = self.client.get(self.url, {"search": "nobody"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "No results")

    def test_matching_results_are_rendered(self) -> None:
        UserProfile.objects.create_user(email="ada@example.com", password="password123", first_name="Ada")
        response = self.client.get(self.url, {"search": "Ada"})
        self.assertContains(response, "ada@example.com")

    def test_pagination_shows_load_more(self) -> None:
        for i in range(25):
            UserProfile.objects.create_user(email=f"user{i}@example.com", password="password123")
        response = self.client.get(self.url, {"search": ""})
        self.assertContains(response, "Load more")


class SearchableSelectDemoViewTests(TestCase):
    def test_demo_page_renders(self) -> None:
        response = self.client.get(reverse("demo:searchable-select"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Find a user")
