from types import SimpleNamespace

from django.test import SimpleTestCase

from apps.shared.views import HtmxTemplateMixin, PaginatedListViewMixin


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
