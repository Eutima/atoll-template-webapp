from typing import Any

from django.http import HttpRequest

from apps.authentication.permissions.helix import get_helix_user
from apps.authentication.services.helix_login import HelixLoginService


def helix(request: HttpRequest) -> dict[str, Any]:
    return {
        "helix_user": get_helix_user(request),
        "helix_configured": HelixLoginService.is_configured(),
    }
