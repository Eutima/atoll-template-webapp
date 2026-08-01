from unittest.mock import Mock, patch

import requests
from django.test import TestCase, override_settings

from apps.shared.interfaces.helix.client import HelixInterface
from apps.shared.interfaces.helix.exceptions import HelixAuthError

HELIX_SETTINGS = {
    "HELIX_BASE_URL": "https://helix.example.com",
    "HELIX_OAUTH_CLIENT_ID": "client-id",
    "HELIX_OAUTH_CLIENT_SECRET": "client-secret",
    "HELIX_OAUTH_TENANT": "acme-corp",
    "HELIX_OAUTH_REDIRECT_URI": "https://app.example.com/auth/helix/callback/",
}


@override_settings(**HELIX_SETTINGS)
class HelixInterfaceTests(TestCase):
    def test_authorize_url_includes_pkce_and_tenant(self) -> None:
        url = HelixInterface().authorize_url(state="state-123", code_challenge="challenge-abc")
        self.assertTrue(url.startswith("https://helix.example.com/auth/oauth/authorize/?"))
        self.assertIn("client_id=client-id", url)
        self.assertIn("tenant=acme-corp", url)
        self.assertIn("code_challenge=challenge-abc", url)
        self.assertIn("code_challenge_method=S256", url)
        self.assertIn("state=state-123", url)
        self.assertIn("scope=read+openid", url)
        self.assertNotIn("nonce=", url)

    def test_authorize_url_includes_nonce_when_given(self) -> None:
        url = HelixInterface().authorize_url(
            state="state-123", code_challenge="challenge-abc", nonce="nonce-xyz"
        )
        self.assertIn("nonce=nonce-xyz", url)

    def test_exchange_code_returns_token_response(self) -> None:
        mock_response = Mock(status_code=200)
        mock_response.json.return_value = {"access_token": "abc", "refresh_token": "def"}
        with patch("apps.shared.interfaces.helix.client.requests.post", return_value=mock_response) as mock_post:
            tokens = HelixInterface().exchange_code(code="auth-code", code_verifier="verifier")
        self.assertEqual(tokens["access_token"], "abc")
        sent_data = mock_post.call_args.kwargs["data"]
        self.assertEqual(sent_data["client_secret"], "client-secret")
        self.assertEqual(sent_data["code"], "auth-code")

    def test_exchange_code_raises_helix_auth_error_on_failure(self) -> None:
        with patch(
            "apps.shared.interfaces.helix.client.requests.post",
            side_effect=requests.exceptions.ConnectionError("down"),
        ):
            with self.assertRaises(HelixAuthError):
                HelixInterface().exchange_code(code="auth-code", code_verifier="verifier")

    def test_userinfo_sends_bearer_token(self) -> None:
        mock_response = Mock(status_code=200)
        mock_response.json.return_value = {"sub": "user-1", "email": "user@example.com"}
        with patch("apps.shared.interfaces.helix.client.requests.get", return_value=mock_response) as mock_get:
            claims = HelixInterface().userinfo(access_token="access-token")
        self.assertEqual(claims["email"], "user@example.com")
        self.assertEqual(mock_get.call_args.kwargs["headers"]["Authorization"], "Bearer access-token")

    def test_tenant_slugs_extracts_slug_list(self) -> None:
        mock_response = Mock(status_code=200)
        mock_response.json.return_value = [
            {"id": "1", "name": "Acme Corp", "slug": "acme-corp"},
            {"id": "2", "name": "Other Co", "slug": "other-co"},
        ]
        with patch("apps.shared.interfaces.helix.client.requests.get", return_value=mock_response):
            slugs = HelixInterface().tenant_slugs(access_token="access-token")
        self.assertEqual(slugs, ["acme-corp", "other-co"])
