import django_filters
from django.db.models import Q, QuerySet


class BaseFilterSet(django_filters.FilterSet):
    """Marker base for all domain FilterSets; subclasses define their own
    `ordering = django_filters.OrderingFilter(fields=(...))`."""


class SearchFilterMixin:
    """Mixin for FilterSets exposing a single free-text `search` filter that
    ORs `icontains` across `search_fields` (subclasses set this attribute)."""

    search_fields: list[str] = []

    def filter_search(self, queryset: QuerySet, name: str, value: str) -> QuerySet:
        if not value:
            return queryset
        query = Q()
        for field in self.search_fields:
            query |= Q(**{f"{field}__icontains": value})
        return queryset.filter(query)
