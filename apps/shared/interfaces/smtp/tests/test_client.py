from unittest.mock import patch

from django.core import mail
from django.test import TestCase

from apps.shared.interfaces.smtp.client import SmtpInterface
from apps.shared.interfaces.smtp.exceptions import EmailSendError


class SmtpInterfaceTests(TestCase):
    def test_send_success_populates_outbox(self) -> None:
        sent_count = SmtpInterface().send(to=["user@example.com"], subject="Hi", body="Hello")
        self.assertEqual(sent_count, 1)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["user@example.com"])
        self.assertEqual(mail.outbox[0].subject, "Hi")

    def test_send_uses_default_from_email_when_not_provided(self) -> None:
        SmtpInterface().send(to=["user@example.com"], subject="Hi", body="Hello")
        from django.conf import settings

        self.assertEqual(mail.outbox[0].from_email, settings.DEFAULT_FROM_EMAIL)

    def test_send_failure_raises_email_send_error(self) -> None:
        with patch(
            "apps.shared.interfaces.smtp.client.EmailMessage.send",
            side_effect=RuntimeError("smtp down"),
        ):
            with self.assertRaises(EmailSendError):
                SmtpInterface().send(to=["user@example.com"], subject="Hi", body="Hello")
        self.assertEqual(len(mail.outbox), 0)
