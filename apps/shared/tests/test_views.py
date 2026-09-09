from types import SimpleNamespace

from django.contrib.auth import get_user_model
from django.test import Client, SimpleTestCase, TestCase
from django.urls import reverse

from apps.shared.views import HtmxTemplateMixin, PaginatedListViewMixin


class HomeViewTests(TestCase):
    def test_anonymous_is_redirected_to_login(self) -> None:
        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("authentication:login"), response["Location"])

    def test_authenticated_user_sees_home(self) -> None:
        user = get_user_model().objects.create_user(email="home@example.com", password="password123")
        self.client.force_login(user)
        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "home.html")


class MetricsViewTests(SimpleTestCase):
    def test_returns_up_1(self) -> None:
        response = Client().get("/metrics")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"up 1\n")
        self.assertEqual(response["Content-Type"], "text/plain; version=0.0.4; charset=utf-8")


class HtmxTemplateMixinTests(SimpleTestCase):
    def _mixin(self, is_htmx: bool) -> HtmxTemplateMixin:
        mixin = HtmxTemplateMixin()
        mixin.template_name = "full.html"
        mixin.htmx_template_name = "partial.html"
        mixin.request = SimpleNamespace(htmx=is_htmx)
        return mixin

    def test_full_page_request_uses_template_name(self) -> None:
        self.assertEqual(self._mixin(is_htmx=False).get_template_names(), ["full.html"])

    def test_htmx_request_uses_htmx_template_name(self) -> None:
        self.assertEqual(self._mixin(is_htmx=True).get_template_names(), ["partial.html"])

    def test_htmx_request_falls_back_when_no_htmx_template_set(self) -> None:
        mixin = self._mixin(is_htmx=True)
        mixin.htmx_template_name = None
        self.assertEqual(mixin.get_template_names(), ["full.html"])


class PaginatedListViewMixinTests(SimpleTestCase):
    def test_paginate_returns_expected_page(self) -> None:
        mixin = PaginatedListViewMixin()
        mixin.paginate_by = 2
        page = mixin.paginate(list(range(5)), 2)
        self.assertEqual(list(page.object_list), [2, 3])
        self.assertEqual(page.paginator.num_pages, 3)
