from unittest.mock import MagicMock

from django.test import SimpleTestCase

from apps.shared.filters import SearchFilterMixin


class _Searcher(SearchFilterMixin):
    search_fields = ["email", "first_name"]


class SearchFilterMixinTests(SimpleTestCase):
    def test_empty_value_returns_queryset_unmodified(self) -> None:
        queryset = MagicMock()
        result = _Searcher().filter_search(queryset, "search", "")
        self.assertIs(result, queryset)
        queryset.filter.assert_not_called()

    def test_value_filters_across_all_search_fields(self) -> None:
        queryset = MagicMock()
        _Searcher().filter_search(queryset, "search", "ada")
        queryset.filter.assert_called_once()
        (query_arg,), _ = queryset.filter.call_args
        query_str = str(query_arg)
        self.assertIn("email__icontains", query_str)
        self.assertIn("first_name__icontains", query_str)
        self.assertIn("ada", query_str)
