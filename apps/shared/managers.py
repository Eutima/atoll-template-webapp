from django.db import models


class BaseQuerySet(models.QuerySet):
    """Optional convenience base for trivial models. Domains that need
    richer reusable filtering should define their own QuerySet instead of
    inheriting this one, to keep each domain's query vocabulary explicit."""

    def active(self) -> "BaseQuerySet":
        return self.filter(is_active=True)


BaseManager = models.Manager.from_queryset(BaseQuerySet)
