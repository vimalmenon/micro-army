"""Email sender — sends emails via SMTP with retry logic."""

from __future__ import annotations

import logging
import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

from config import settings

logger = logging.getLogger(__name__)


class EmailSender:
    """Sends emails via SMTP. Supports SSL (465) and STARTTLS (587)."""

    def __init__(self):
        self.host = settings.smtp_host
        self.port = settings.smtp_port
        self.user = settings.smtp_user
        self.password = settings.smtp_password
        self.from_addr = settings.smtp_from
        self.from_name = settings.smtp_from_name
        self.use_ssl = settings.smtp_use_ssl

    def _build_message(
        self,
        to: str,
        subject: str,
        body: str,
        body_type: str = "html",
        cc: Optional[list[str]] = None,
    ) -> MIMEMultipart:
        msg = MIMEMultipart("alternative")
        msg["From"] = f"{self.from_name} <{self.from_addr}>"
        msg["To"] = to
        msg["Subject"] = subject
        if cc:
            msg["Cc"] = ", ".join(cc)

        subtype = "html" if body_type == "html" else "plain"
        msg.attach(MIMEText(body, subtype))

        return msg

    def send(
        self,
        to: str,
        subject: str,
        body: str,
        body_type: str = "html",
        cc: Optional[list[str]] = None,
    ) -> tuple[bool, str]:
        """Send an email. Returns (success, error_message)."""
        try:
            msg = self._build_message(to, subject, body, body_type, cc)
            recipients = [to]
            if cc:
                recipients.extend(cc)

            if self.use_ssl:
                # Port 465 — SSL
                ctx = ssl.create_default_context()
                with smtplib.SMTP_SSL(self.host, self.port, context=ctx, timeout=30) as server:
                    server.login(self.user, self.password)
                    server.sendmail(self.from_addr, recipients, msg.as_string())
            else:
                # Port 587 — STARTTLS
                with smtplib.SMTP(self.host, self.port, timeout=30) as server:
                    server.starttls()
                    server.login(self.user, self.password)
                    server.sendmail(self.from_addr, recipients, msg.as_string())

            logger.info("Email sent to %s: %s", to, subject)
            return True, ""

        except smtplib.SMTPAuthenticationError:
            err = "SMTP authentication failed — check credentials"
            logger.error(err)
            return False, err
        except smtplib.SMTPRecipientsRefused:
            err = f"All recipients refused for {to}"
            logger.error(err)
            return False, err
        except (smtplib.SMTPException, OSError, TimeoutError) as e:
            err = f"SMTP error: {e}"
            logger.error(err)
            return False, err
        except Exception as e:
            err = f"Unexpected error sending email: {e}"
            logger.exception(err)
            return False, err


# Singleton
email_sender = EmailSender()
