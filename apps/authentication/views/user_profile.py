from typing import Any

from django.contrib.auth import login, logout
from django.contrib.auth.views import LoginView as DjangoLoginView
from django.db.models import QuerySet
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.views import View
from django.views.generic import TemplateView

from apps.authentication.filters.user_profile import UserProfileFilterSet
from apps.authentication.models.user_profile import UserProfile
from apps.authentication.serializers.user_profile import SignUpSerializer
from apps.authentication.services.user_profile import UserProfileService
from apps.shared.exceptions import ValidationError
from apps.shared.views import SearchEndpointView


class LoginView(DjangoLoginView):
    template_name = "authentication/login.html"


class LogoutView(View):
    def post(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        logout(request)
        return redirect("authentication:login")


class SignUpView(View):
    template_name = "authentication/signup.html"
    service = UserProfileService()

    def get(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        return render(request, self.template_name, {"serializer": SignUpSerializer()})

    def post(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        serializer = SignUpSerializer(data=request.POST)
        if not serializer.is_valid():
            return render(request, self.template_name, {"serializer": serializer}, status=422)
        try:
            profile = self.service.create(**serializer.validated_data)
        except ValidationError as exc:
            serializer.errors.update(exc.errors)
            return render(request, self.template_name, {"serializer": serializer}, status=422)
        login(request, profile)
        return redirect("/")


class UserProfileSearchView(SearchEndpointView):
    filterset_class = UserProfileFilterSet
    result_template_name = "authentication/partials/user_profile_options.html"
    service = UserProfileService()

    def get_queryset(self) -> QuerySet[UserProfile]:
        return self.service.filter()


class SearchableSelectDemoView(TemplateView):
    template_name = "authentication/demo/searchable_select_demo.html"
