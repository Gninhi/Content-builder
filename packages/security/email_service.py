import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, List, Dict, Any

logger = logging.getLogger("packages.security.email_service")


@dataclass
class EmailDeliveryResult:
    success: bool
    recipient: str
    subject: str
    message_id: str
    error: Optional[str] = None


class BaseEmailService(ABC):
    @abstractmethod
    def send_verification_email(self, to_email: str, token: str, user_name: str) -> EmailDeliveryResult:
        pass

    @abstractmethod
    def send_password_reset_email(self, to_email: str, token: str, user_name: str) -> EmailDeliveryResult:
        pass


class MemoryLogEmailService(BaseEmailService):
    """
    In-memory and secure log email service for local development, demo, and automated tests.
    Does not expose sensitive raw passwords, logs security-safe notification events,
    and maintains an in-memory audit store accessible to test harnesses.
    """

    def __init__(self):
        self.sent_emails: List[Dict[str, Any]] = []

    def clear(self):
        self.sent_emails.clear()

    def get_latest_token_for(self, email: str, email_type: str = "verification") -> Optional[str]:
        target = email.strip().lower()
        for item in reversed(self.sent_emails):
            if item.get("recipient", "").strip().lower() == target and item.get("type") == email_type:
                return item.get("token")
        return None

    def send_verification_email(self, to_email: str, token: str, user_name: str) -> EmailDeliveryResult:
        email_clean = to_email.strip().lower()
        subject = "Vérification de votre compte ContentOps Harness"
        logger.info(f"AUDIT: Email verification dispatched for user '{user_name}' <{email_clean}>")
        self.sent_emails.append({
            "type": "verification",
            "recipient": email_clean,
            "subject": subject,
            "user_name": user_name,
            "token": token,
        })
        return EmailDeliveryResult(
            success=True,
            recipient=email_clean,
            subject=subject,
            message_id=f"msg_verif_{len(self.sent_emails)}",
        )

    def send_password_reset_email(self, to_email: str, token: str, user_name: str) -> EmailDeliveryResult:
        email_clean = to_email.strip().lower()
        subject = "Réinitialisation de votre mot de passe ContentOps Harness"
        logger.info(f"AUDIT: Password reset email dispatched for user '{user_name}' <{email_clean}>")
        self.sent_emails.append({
            "type": "reset",
            "recipient": email_clean,
            "subject": subject,
            "user_name": user_name,
            "token": token,
        })
        return EmailDeliveryResult(
            success=True,
            recipient=email_clean,
            subject=subject,
            message_id=f"msg_reset_{len(self.sent_emails)}",
        )


import os
import uuid
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


class SMTPEmailService(BaseEmailService):
    """
    Production-ready SMTP email delivery service supporting TLS / STARTTLS.
    """
    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        from_email: Optional[str] = None,
        use_tls: bool = True,
    ):
        self.host = host or os.getenv("SMTP_HOST", "localhost")
        self.port = int(port or os.getenv("SMTP_PORT", "587"))
        self.username = username or os.getenv("SMTP_USERNAME")
        self.password = password or os.getenv("SMTP_PASSWORD")
        self.from_email = from_email or os.getenv("SMTP_FROM_EMAIL", "noreply@contentops.io")
        self.use_tls = use_tls

    def _send_smtp_message(self, to_email: str, subject: str, text_content: str, html_content: Optional[str] = None) -> EmailDeliveryResult:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = self.from_email
        msg["To"] = to_email
        msg_id = f"<{uuid.uuid4().hex}@{self.host}>"
        msg["Message-ID"] = msg_id

        msg.attach(MIMEText(text_content, "plain", "utf-8"))
        if html_content:
            msg.attach(MIMEText(html_content, "html", "utf-8"))

        try:
            with smtplib.SMTP(self.host, self.port, timeout=10) as server:
                if self.use_tls:
                    server.starttls()
                if self.username and self.password:
                    server.login(self.username, self.password)
                server.sendmail(self.from_email, [to_email], msg.as_string())
            return EmailDeliveryResult(
                success=True,
                recipient=to_email,
                subject=subject,
                message_id=msg_id,
            )
        except Exception as e:
            logger.error(f"Failed to dispatch email via SMTP to {to_email}: {e}")
            return EmailDeliveryResult(
                success=False,
                recipient=to_email,
                subject=subject,
                message_id=msg_id,
                error=str(e),
            )

    def send_verification_email(self, to_email: str, token: str, user_name: str) -> EmailDeliveryResult:
        subject = "Vérification de votre compte ContentOps Harness"
        base_url = os.getenv("APP_BASE_URL", "http://localhost:5173")
        verify_url = f"{base_url}/verify-email?token={token}"
        text_content = (
            f"Bonjour {user_name},\n\n"
            f"Bienvenue sur ContentOps Harness. Veuillez vérifier votre adresse email en cliquant sur le lien suivant :\n"
            f"{verify_url}\n\n"
            f"Ce lien expirera dans 24 heures.\n"
        )
        html_content = (
            f"<p>Bonjour <strong>{user_name}</strong>,</p>"
            f"<p>Bienvenue sur ContentOps Harness. Veuillez vérifier votre adresse email :</p>"
            f"<p><a href=\"{verify_url}\" style=\"display:inline-block;padding:10px 20px;background:#2563eb;color:#fff;text-decoration:none;border-radius:4px;\">Confirmer mon compte</a></p>"
            f"<p>Ou copiez ce lien : {verify_url}</p>"
        )
        return self._send_smtp_message(to_email, subject, text_content, html_content)

    def send_password_reset_email(self, to_email: str, token: str, user_name: str) -> EmailDeliveryResult:
        subject = "Réinitialisation de votre mot de passe ContentOps Harness"
        base_url = os.getenv("APP_BASE_URL", "http://localhost:5173")
        reset_url = f"{base_url}/reset-password?token={token}"
        text_content = (
            f"Bonjour {user_name},\n\n"
            f"Une demande de réinitialisation de mot de passe a été initiée pour votre compte ContentOps Harness :\n"
            f"{reset_url}\n\n"
            f"Ce lien est à usage unique et expirera dans 1 heure.\n"
        )
        html_content = (
            f"<p>Bonjour <strong>{user_name}</strong>,</p>"
            f"<p>Pour réinitialiser votre mot de passe ContentOps Harness :</p>"
            f"<p><a href=\"{reset_url}\" style=\"display:inline-block;padding:10px 20px;background:#2563eb;color:#fff;text-decoration:none;border-radius:4px;\">Réinitialiser mon mot de passe</a></p>"
            f"<p>Ou copiez ce lien : {reset_url}</p>"
        )
        return self._send_smtp_message(to_email, subject, text_content, html_content)


_default_service: Optional[BaseEmailService] = None


def get_email_service() -> BaseEmailService:
    global _default_service
    if _default_service is None:
        backend = os.getenv("EMAIL_BACKEND", "").lower()
        smtp_host = os.getenv("SMTP_HOST")
        from packages.security.env import is_production
        if backend == "smtp" or (is_production() and smtp_host) or (not backend and smtp_host):
            _default_service = SMTPEmailService()
        else:
            _default_service = MemoryLogEmailService()
    return _default_service


def set_email_service(service: Optional[BaseEmailService]) -> None:
    global _default_service
    _default_service = service
