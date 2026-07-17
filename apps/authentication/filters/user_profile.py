import django_filters

from apps.authentication.models.user_profile import UserProfile
from apps.shared.filters import BaseFilterSet, SearchFilterMixin


class UserProfileFilterSet(SearchFilterMixin, BaseFilterSet):
    search = django_filters.CharFilter(method="filter_search")
    is_active = django_filters.BooleanFilter()
    ordering = django_filters.OrderingFilter(
        fields=(("email", "email"), ("created_at", "created_at")),
    )

    search_fields = ["email", "first_name", "last_name"]

    class Meta:
        model = UserProfile
        fields = ["is_active"]
