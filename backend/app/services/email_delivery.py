import asyncio
import html
import logging

from fastapi_mail.errors import ConnectionErrors
from fastapi_mail import ConnectionConfig, FastMail, MessageSchema, MessageType

from app.core.config import get_settings

logger = logging.getLogger("quiz_pass.email")


class EmailDeliveryService:
    def __init__(self):
        self.settings = get_settings()

    def send(self, to_email: str, subject: str, body: str, html_body: str | None = None) -> bool:
        if not self._smtp_configured():
            logger.warning("Email delivery is not configured. To=%s Subject=%s\n%s", to_email, subject, body)
            return False

        message = MessageSchema(
            subject=subject,
            recipients=[to_email],
            body=html_body or self.text_to_html(body),
            alternative_body=body,
            subtype=MessageType.html,
        )
        try:
            asyncio.run(FastMail(self._connection_config()).send_message(message))
        except ConnectionErrors:
            logger.exception(
                "Email delivery failed. host=%s port=%s from=%s to=%s subject=%s",
                self.settings.smtp_host,
                self.settings.smtp_port,
                self.settings.smtp_from_email,
                to_email,
                subject,
            )
            return False
        return True

    def _connection_config(self) -> ConnectionConfig:
        use_ssl_tls = self.settings.smtp_use_tls and self.settings.smtp_port == 465
        return ConnectionConfig(
            MAIL_USERNAME=self.settings.smtp_username,
            MAIL_PASSWORD=self.settings.smtp_password,
            MAIL_FROM=self.settings.smtp_from_email,
            MAIL_PORT=self.settings.smtp_port,
            MAIL_SERVER=self.settings.smtp_host,
            MAIL_STARTTLS=self.settings.smtp_use_tls and not use_ssl_tls,
            MAIL_SSL_TLS=use_ssl_tls,
            USE_CREDENTIALS=bool(self.settings.smtp_username),
            VALIDATE_CERTS=True,
            SUPPRESS_SEND=self.settings.app_env == "test",
        )

    def _smtp_configured(self) -> bool:
        return bool(self.settings.smtp_host and self.settings.smtp_from_email)

    @staticmethod
    def text_to_html(body: str) -> str:
        return f"<pre>{html.escape(body)}</pre>"
