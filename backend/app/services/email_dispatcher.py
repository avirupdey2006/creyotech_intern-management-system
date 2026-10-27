from datetime import date
from email.message import EmailMessage
from typing import Dict, Set
import aiosmtplib

from app.core.config import settings
from app.core.logging import pino_logger, trigger_sentry_alert


class EmailDispatcherService:
    """
    Manages outgoing email notifications with PDF attachments, idempotency protection,
    and daily quota enforcement (100/day free or 2,000/day Workspace per Section 1).
    """

    def __init__(self) -> None:
        self._dispatched_idempotency_keys: Set[str] = set()
        self._daily_counts: Dict[str, int] = {}

    def get_today_count(self) -> int:
        today_key = date.today().isoformat()
        return self._daily_counts.get(today_key, 0)

    def has_been_dispatched(self, idempotency_key: str) -> bool:
        return idempotency_key in self._dispatched_idempotency_keys

    async def dispatch_document_email(
        self,
        *,
        recipient_email: str,
        candidate_name: str,
        document_type: str,
        pdf_bytes: bytes,
        idempotency_key: str,
    ) -> dict:
        """
        Sends an email with the generated PDF attachment once per unique idempotency_key.
        """
        # 1. Idempotency Guard (Section 5.3)
        if idempotency_key in self._dispatched_idempotency_keys:
            pino_logger.info(
                "Idempotent skip: email already dispatched for transaction key",
                idempotency_key=idempotency_key,
                recipient_email=recipient_email,
                document_type=document_type,
            )
            return {
                "status": "SKIPPED_DUPLICATE",
                "idempotency_key": idempotency_key,
                "daily_sent_count": self.get_today_count(),
            }

        # 2. Daily Quota Constraint Check (Section 1: 100/day free or 2,000/day Workspace)
        today_key = date.today().isoformat()
        current_count = self._daily_counts.get(today_key, 0)
        if current_count >= settings.EMAIL_DAILY_LIMIT:
            trigger_sentry_alert(
                "Daily email dispatch quota exceeded",
                level="error",
                context={
                    "daily_limit": settings.EMAIL_DAILY_LIMIT,
                    "current_count": current_count,
                    "recipient_email": recipient_email,
                    "document_type": document_type,
                },
            )
            raise RuntimeError(
                f"Daily email quota limit of {settings.EMAIL_DAILY_LIMIT}/day reached."
            )

        # 3. Build MIME Email with PDF Attachment
        friendly_title = document_type.replace("_", " ").title()
        msg = EmailMessage()
        msg["From"] = settings.SMTP_FROM_EMAIL
        msg["To"] = recipient_email
        msg["Subject"] = f"[IMS] Your {friendly_title} is Ready"
        msg["X-Idempotency-Key"] = idempotency_key
        msg.set_content(
            f"Dear {candidate_name},\n\n"
            f"Please find attached your official {friendly_title} issued by the Intern Management System.\n"
            f"You may also download this document securely from your Candidate Portal.\n\n"
            f"Best regards,\nHR & Administration Team"
        )

        attachment_filename = f"{document_type.lower()}.pdf"
        msg.add_attachment(
            pdf_bytes,
            maintype="application",
            subtype="pdf",
            filename=attachment_filename,
        )

        # 4. Deliver via SMTP TLS if real credentials are configured, else simulated delivery
        smtp_user_clean = (settings.SMTP_USER or "").strip().lower()
        smtp_pwd_clean = (settings.SMTP_PASSWORD or "").strip().lower()

        placeholder_users = {
            "",
            "your_smtp_email",
            "hr-notifications@yourdomain.com",
            "hr-notifications@example.com",
            "noreply@ims.local",
            "mock_smtp_user",
        }
        placeholder_passwords = {
            "",
            "mock_smtp_password",
            "your_app_specific_password",
            "your_smtp_app_password",
        }

        is_mock_smtp = (
            not settings.SMTP_USER
            or smtp_user_clean in placeholder_users
            or smtp_user_clean.endswith(("@yourdomain.com", "@example.com", ".local", ".test"))
            or smtp_user_clean.startswith("your_smtp_")
            or smtp_pwd_clean in placeholder_passwords
            or smtp_pwd_clean.startswith("your_")
            or recipient_email.endswith((".test", ".local"))
        )

        if not is_mock_smtp:
            try:
                await aiosmtplib.send(
                    msg,
                    hostname=settings.SMTP_HOST,
                    port=settings.SMTP_PORT,
                    start_tls=True,
                    username=settings.SMTP_USER,
                    password=settings.SMTP_PASSWORD,
                    timeout=15.0,
                )
                delivery_mode = "SMTP_TLS"
            except Exception as exc:
                trigger_sentry_alert(
                    "SMTP email delivery failure",
                    level="error",
                    context={
                        "recipient_email": recipient_email,
                        "document_type": document_type,
                        "idempotency_key": idempotency_key,
                        "error": str(exc),
                    },
                )
                if settings.ENVIRONMENT == "development":
                    pino_logger.warning(
                        "SMTP delivery failed in development; falling back to simulated dispatch",
                        recipient_email=recipient_email,
                        document_type=document_type,
                        idempotency_key=idempotency_key,
                        error=str(exc),
                    )
                    delivery_mode = "SIMULATED_FALLBACK"
                else:
                    raise
        else:
            delivery_mode = "SIMULATED_LOCAL"

        # 5. Record Idempotency Key & Increment Daily Counter
        self._dispatched_idempotency_keys.add(idempotency_key)
        self._daily_counts[today_key] = current_count + 1

        pino_logger.info(
            "Dispatched email notification with PDF attachment",
            recipient_email=recipient_email,
            document_type=document_type,
            idempotency_key=idempotency_key,
            delivery_mode=delivery_mode,
            daily_sent_count=self._daily_counts[today_key],
            daily_limit=settings.EMAIL_DAILY_LIMIT,
        )
        return {
            "status": "SENT",
            "delivery_mode": delivery_mode,
            "idempotency_key": idempotency_key,
            "daily_sent_count": self._daily_counts[today_key],
        }


email_dispatcher_service = EmailDispatcherService()