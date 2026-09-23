from django.test import SimpleTestCase

from apps.authentication.lib.helix_claims import build_session_claims


class BuildSessionClaimsTests(SimpleTestCase):
    def test_full_claim_set_is_mapped(self) -> None:
        userinfo = {
            "sub": "helix-sub-1",
            "email": "ada@example.com",
            "given_name": "Ada",
            "family_name": "Lovelace",
        }
        self.assertEqual(
            build_session_claims(userinfo),
            {"sub": "helix-sub-1", "email": "ada@example.com", "first_name": "Ada", "last_name": "Lovelace"},
        )

    def test_missing_optional_claims_default_to_empty_strings(self) -> None:
        claims = build_session_claims({"sub": "helix-sub-1", "email": "ada@example.com"})
        self.assertEqual(claims["first_name"], "")
        self.assertEqual(claims["last_name"], "")

    def test_empty_userinfo_returns_all_empty_strings(self) -> None:
        claims = build_session_claims({})
        self.assertEqual(claims, {"sub": "", "email": "", "first_name": "", "last_name": ""})
