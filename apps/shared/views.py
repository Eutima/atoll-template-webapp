from typing import Any

from django.core.paginator import Page, Paginator
from django.db.models import QuerySet
from django.http import HttpRequest, HttpResponse
from django.template.response import TemplateResponse
from django.views import View


class HtmxTemplateMixin:
    """Renders `htmx_template_name` for htmx requests (partial swap) and
    `template_name` for full-page loads."""

    template_name: str
    htmx_template_name: str | None = None

    def get_template_names(self) -> list[str]:
        request: HttpRequest = self.request  # type: ignore[attr-defined]
        if getattr(request, "htmx", False) and self.htmx_template_name:
            return [self.htmx_template_name]
        return [self.template_name]


class PaginatedListViewMixin:
    """Wraps Django's Paginator for list views; subclasses provide
    `paginate_by` and a `get_queryset()`."""

    paginate_by: int = 25

    def paginate(self, queryset: QuerySet, page_number: str | int | None) -> Page:
        paginator = Paginator(queryset, self.paginate_by)
        return paginator.get_page(page_number)


def metrics(request: HttpRequest) -> HttpResponse:
    """Minimal Prometheus exposition endpoint: reports process liveness only."""
    return HttpResponse("up 1\n", content_type="text/plain; version=0.0.4; charset=utf-8")


class SearchEndpointView(View):
    """Generic reusable htmx search endpoint powering `<c-searchable-select>`.

    Subclasses set `filterset_class` (a `SearchFilterMixin`-based FilterSet),
    `result_template_name`, and override `get_queryset()` to source records
    through a domain Service rather than a bare model manager.
    """

    filterset_class: type
    result_template_name: str
    paginate_by: int = 20

    def get_queryset(self) -> QuerySet:
        raise NotImplementedError

    def get(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        filterset = self.filterset_class(request.GET, queryset=self.get_queryset())
        page_obj = Paginator(filterset.qs, self.paginate_by).get_page(request.GET.get("page"))
        return TemplateResponse(
            request,
            self.result_template_name,
            {"page_obj": page_obj, "query": request.GET.get("search", "")},
        )
