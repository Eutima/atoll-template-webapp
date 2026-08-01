from django.conf import settings
from django.contrib import admin
from django.urls import include, path

from apps.shared.views import metrics

urlpatterns = [
    path("admin/", admin.site.urls),
    path("metrics", metrics, name="metrics"),
    path("auth/", include("apps.authentication.urls")),
    path("", include("apps.authentication.urls_demo")),
]

if settings.DEBUG:
    import debug_toolbar

    urlpatterns = [path("__debug__/", include(debug_toolbar.urls)), *urlpatterns]
