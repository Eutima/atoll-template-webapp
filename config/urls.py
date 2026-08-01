from django.conf import settings
from django.contrib import admin
from django.urls import include, path
from django.views.generic import TemplateView

from apps.shared.views import metrics

urlpatterns = [
    path("admin/", admin.site.urls),
    path("metrics", metrics, name="metrics"),
    path("auth/", include("apps.authentication.urls")),
    path("", TemplateView.as_view(template_name="index.html"), name="index"),
]

if settings.DEBUG:
    import debug_toolbar

    urlpatterns = [path("__debug__/", include(debug_toolbar.urls)), *urlpatterns]
