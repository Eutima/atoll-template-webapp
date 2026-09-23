from urllib.parse import parse_qs, unquote, urlparse

import pyotp
from django.test import SimpleTestCase

from apps.authentication.lib import totp


class GenerateSecretTests(SimpleTestCase):
    def test_returns_valid_base32_secret(self) -> None:
        secret = totp.generate_secret()
        self.assertTrue(secret.isalnum())
        pyotp.totp.TOTP(secret).now()  # raises if not a valid base32 secret


class ProvisioningUriTests(SimpleTestCase):
    def test_includes_account_name_and_issuer(self) -> None:
        uri = totp.provisioning_uri("JBSWY3DPEHPK3PXP", "ada@example.com")
        parsed = urlparse(uri)
        self.assertEqual(parsed.scheme, "otpauth")
        self.assertEqual(parsed.netloc, "totp")
        self.assertIn("ada@example.com", unquote(parsed.path))
        self.assertEqual(parse_qs(parsed.query)["issuer"], [totp.ISSUER_NAME])
        self.assertEqual(parse_qs(parsed.query)["secret"], ["JBSWY3DPEHPK3PXP"])


class VerifyCodeTests(SimpleTestCase):
    def test_returns_true_for_current_code(self) -> None:
        secret = totp.generate_secret()
        code = pyotp.totp.TOTP(secret).now()
        self.assertTrue(totp.verify_code(secret, code))

    def test_returns_false_for_wrong_code(self) -> None:
        secret = totp.generate_secret()
        self.assertFalse(totp.verify_code(secret, "000000"))


class QrCodeSvgTests(SimpleTestCase):
    def test_returns_svg_markup(self) -> None:
        svg = totp.qr_code_svg("otpauth://totp/test?secret=JBSWY3DPEHPK3PXP")
        self.assertIn("<svg", svg)


class GenerateBackupCodesTests(SimpleTestCase):
    def test_returns_requested_count_of_unique_codes(self) -> None:
        codes = totp.generate_backup_codes(count=10)
        self.assertEqual(len(codes), 10)
        self.assertEqual(len(set(codes)), 10)


class HashBackupCodeTests(SimpleTestCase):
    def test_hash_is_deterministic(self) -> None:
        self.assertEqual(totp.hash_backup_code("abcd-1234"), totp.hash_backup_code("abcd-1234"))

    def test_different_codes_hash_differently(self) -> None:
        self.assertNotEqual(totp.hash_backup_code("abcd-1234"), totp.hash_backup_code("efgh-5678"))
