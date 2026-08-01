from django.urls import path

from apps.authentication.views.user_profile import (
    HelixCallbackView,
    HelixLoginView,
    LoginPageView,
    LogoutView,
)

app_name = "authentication"

urlpatterns = [
    path("login/", LoginPageView.as_view(), name="login"),
    path("helix/login/", HelixLoginView.as_view(), name="helix-login"),
    path("helix/callback/", HelixCallbackView.as_view(), name="helix-callback"),
    path("logout/", LogoutView.as_view(), name="logout"),
]
