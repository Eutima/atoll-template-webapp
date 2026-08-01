from urllib.parse import urlencode

import requests
from django.conf import settings
from l4py import get_logger

from apps.shared.interfaces.base import BaseInterface
from apps.shared.interfaces.helix.exceptions import HelixAuthError

logger = get_logger()

_REQUEST_TIMEOUT_SECONDS = 10


class HelixInterface(BaseInterface):
    """OAuth2/OIDC client for "Login with Helix" -- the only place in the
    codebase allowed to call Helix's HTTP API directly. Never logs
    client_secret, code_verifier, or any issued token."""

    def authorize_url(self, *, state: str, code_challenge: str, nonce: str | None = None) -> str:
        params = {
            "client_id": settings.HELIX_OAUTH_CLIENT_ID,
            "response_type": "code",
            "redirect_uri": settings.HELIX_OAUTH_REDIRECT_URI,
            "tenant": settings.HELIX_OAUTH_TENANT,
            "scope": "read openid",
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
            "state": state,
        }
        if nonce:
            params["nonce"] = nonce
        return f"{settings.HELIX_BASE_URL}/auth/oauth/authorize/?{urlencode(params)}"

    def exchange_code(self, *, code: str, code_verifier: str) -> dict:
        data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": settings.HELIX_OAUTH_REDIRECT_URI,
            "client_id": settings.HELIX_OAUTH_CLIENT_ID,
            "client_secret": settings.HELIX_OAUTH_CLIENT_SECRET,
            "code_verifier": code_verifier,
        }
        try:
            response = requests.post(
                f"{settings.HELIX_BASE_URL}/auth/oauth/token/", data=data, timeout=_REQUEST_TIMEOUT_SECONDS
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            logger.error("Helix token exchange failed: %s", exc)
            raise HelixAuthError("Failed to exchange authorization code") from exc
        return response.json()

    def userinfo(self, *, access_token: str) -> dict:
        try:
            response = requests.get(
                f"{settings.HELIX_BASE_URL}/auth/oauth/userinfo/",
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=_REQUEST_TIMEOUT_SECONDS,
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            logger.error("Helix userinfo request failed: %s", exc)
            raise HelixAuthError("Failed to fetch Helix user info") from exc
        return response.json()

    def tenant_slugs(self, *, access_token: str) -> list[str]:
        try:
            response = requests.get(
                f"{settings.HELIX_BASE_URL}/api/v1/tenants/",
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=_REQUEST_TIMEOUT_SECONDS,
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            logger.error("Helix tenants request failed: %s", exc)
            raise HelixAuthError("Failed to fetch Helix workspace memberships") from exc
        return [tenant["slug"] for tenant in response.json()]
