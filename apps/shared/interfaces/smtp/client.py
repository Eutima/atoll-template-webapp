from django.conf import settings
from django.core.mail import EmailMessage
from l4py import get_logger

from apps.shared.interfaces.base import BaseInterface
from apps.shared.interfaces.smtp.exceptions import EmailSendError

logger = get_logger()


class SmtpInterface(BaseInterface):
    """Thin wrapper around Django's email backend -- the only place in the
    codebase allowed to call django.core.mail directly."""

    def send(
        self,
        *,
        to: list[str],
        subject: str,
        body: str,
        from_email: str | None = None,
    ) -> int:
        from_email = from_email or settings.DEFAULT_FROM_EMAIL
        message = EmailMessage(subject=subject, body=body, from_email=from_email, to=to)
        try:
            sent_count = message.send(fail_silently=False)
        except Exception as exc:
            logger.error("Failed to send email to %s: %s", to, exc)
            raise EmailSendError(str(exc)) from exc
        logger.info("Sent email to %s subject=%s", to, subject)
        return sent_count
