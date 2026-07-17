from django.urls import path

from apps.authentication.views.user_profile import SearchableSelectDemoView, UserProfileSearchView

app_name = "demo"

urlpatterns = [
    path("demo/searchable-select/", SearchableSelectDemoView.as_view(), name="searchable-select"),
    path("demo/searchable-select/search/", UserProfileSearchView.as_view(), name="searchable-select-search"),
]
