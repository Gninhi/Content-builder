import json
import logging
import os
import smtplib
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Optional, List, Dict, Any

from packages.security.env import get_app_env

logger = logging.getLogger("packages.security.email_service")

DEV_MAILBOX_PATH = Path(__file__).resolve().parents[2] / "storage" / "dev_mailbox.json"


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


def is_dev_mailbox_allowed() -> bool:
    """
    Returns True ONLY when running in development, local, or test environments
    and DEV_MAILBOX_ENABLED is not explicitly disabled.
    Strictly returns False in staging and production.
    """
    app_env = get_app_env()
    if app_env in ("production", "prod", "staging"):
        return False
    explicit = os.getenv("DEV_MAILBOX_ENABLED")
    if explicit is not None and explicit.strip():
        return explicit.strip().lower() in ("true", "1", "yes")
    return app_env in ("development", "dev", "local", "test", "testing")


def validate_email_configuration() -> None:
    """
    Enforces fail-closed validation of email configuration at startup:
    1. Forbids DEV_MAILBOX_ENABLED or dev/memory email adapters in staging/production.
    2. Requires SMTP_HOST when email verification is active in production (outside automated test harness).
    """
    app_env = get_app_env()
    is_test_harness = (
        os.environ.get("CONTENTOPS_TEST_MODE") == "1"
        or "PYTEST_CURRENT_TEST" in os.environ
        or app_env in ("test", "testing")
    )

    if app_env in ("production", "prod", "staging"):
        dev_mailbox_flag = os.getenv("DEV_MAILBOX_ENABLED", "").strip().lower()
        if dev_mailbox_flag in ("true", "1", "yes"):
            raise RuntimeError(
                f"Startup Denied: DEV_MAILBOX_ENABLED cannot be enabled in '{app_env}' environment."
            )
        backend = os.getenv("EMAIL_BACKEND", "").strip().lower()
        if backend in ("memory", "dev", "local", "dev_mailbox"):
            raise RuntimeError(
                f"Startup Denied: EMAIL_BACKEND='{backend}' is strictly forbidden in '{app_env}' environment."
            )
        req_verif_raw = os.getenv("REQUIRE_EMAIL_VERIFICATION")
        req_verif = True if req_verif_raw is None else req_verif_raw.strip().lower() in ("true", "1", "yes")
        smtp_host = os.getenv("SMTP_HOST", "").strip()
        if req_verif and not smtp_host and not is_test_harness:
            raise RuntimeError(
                f"Startup Denied: REQUIRE_EMAIL_VERIFICATION is enabled in '{app_env}', "
                "but SMTP_HOST is not configured."
            )


class MemoryLogEmailService(BaseEmailService):
    """
    Controlled local development & test email mailbox service.
    Never logs raw verification/reset tokens to general application logs.
    Refuses to operate in staging or production outside the automated test harness.
    """

    def __init__(self, persist_to_disk: Optional[bool] = None):
        app_env = get_app_env()
        is_test_harness = (
            os.environ.get("CONTENTOPS_TEST_MODE") == "1"
            or "PYTEST_CURRENT_TEST" in os.environ
            or app_env in ("test", "testing")
        )
        if app_env in ("production", "prod", "staging") and not is_test_harness:
            raise RuntimeError(
                f"MemoryLogEmailService (dev mailbox) is strictly forbidden in '{app_env}' environment."
            )
        self.sent_emails: List[Dict[str, Any]] = []
        if persist_to_disk is None:
            self._persist_to_disk = app_env in ("development", "dev", "local") and not is_test_harness
        else:
            self._persist_to_disk = persist_to_disk

    def _save_to_disk(self) -> None:
        if not self._persist_to_disk:
            return
        try:
            DEV_MAILBOX_PATH.parent.mkdir(parents=True, exist_ok=True)
            payload = self.sent_emails[-50:]
            DEV_MAILBOX_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
            try:
                os.chmod(DEV_MAILBOX_PATH, 0o600)
            except OSError:
                pass
        except Exception as exc:
            logger.warning("Could not persist dev mailbox entry: %s", exc)

    def clear(self) -> None:
        self.sent_emails.clear()
        if self._persist_to_disk and DEV_MAILBOX_PATH.exists():
            try:
                DEV_MAILBOX_PATH.unlink()
            except OSError:
                pass

    def get_latest_token_for(self, email: str, email_type: str = "verification") -> Optional[str]:
        msg = self.get_latest_message_for(email, email_type=email_type)
        return msg.get("token") if msg else None

    def get_latest_message_for(self, email: str, email_type: str = "verification") -> Optional[Dict[str, Any]]:
        target = email.strip().lower()
        for item in reversed(self.sent_emails):
            if item.get("recipient", "").strip().lower() == target and item.get("type") == email_type:
                return dict(item)
        if self._persist_to_disk and DEV_MAILBOX_PATH.exists():
            try:
                disk_items = json.loads(DEV_MAILBOX_PATH.read_text(encoding="utf-8"))
                for item in reversed(disk_items):
                    if item.get("recipient", "").strip().lower() == target and item.get("type") == email_type:
                        return dict(item)
            except Exception:
                pass
        return None

    def list_messages_for(self, email: Optional[str] = None) -> List[Dict[str, Any]]:
        items = list(self.sent_emails)
        if not items and self._persist_to_disk and DEV_MAILBOX_PATH.exists():
            try:
                items = json.loads(DEV_MAILBOX_PATH.read_text(encoding="utf-8"))
            except Exception:
                items = []
        if email:
            target = email.strip().lower()
            items = [i for i in items if i.get("recipient", "").strip().lower() == target]
        return [dict(i) for i in reversed(items)]

    def send_verification_email(self, to_email: str, token: str, user_name: str) -> EmailDeliveryResult:
        email_clean = to_email.strip().lower()
        subject = "Vérification de votre compte ContentOps Harness"
        base_url = os.getenv("APP_BASE_URL", "http://localhost:3000").rstrip("/")
        verify_url = f"{base_url}/ui/?verify_token={token}"
        msg_id = f"msg_verif_{len(self.sent_emails) + 1}_{uuid.uuid4().hex[:8]}"

        # Never log the raw token or verification URL in general logs
        logger.info("AUDIT: Email verification queued in dev mailbox for '%s' <%s> (msg_id=%s)", user_name, email_clean, msg_id)
        entry = {
            "message_id": msg_id,
            "type": "verification",
            "recipient": email_clean,
            "subject": subject,
            "user_name": user_name,
            "token": token,
            "action_url": verify_url,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        self.sent_emails.append(entry)
        self._save_to_disk()
        return EmailDeliveryResult(
            success=True,
            recipient=email_clean,
            subject=subject,
            message_id=msg_id,
        )

    def send_password_reset_email(self, to_email: str, token: str, user_name: str) -> EmailDeliveryResult:
        email_clean = to_email.strip().lower()
        subject = "Réinitialisation de votre mot de passe ContentOps Harness"
        base_url = os.getenv("APP_BASE_URL", "http://localhost:3000").rstrip("/")
        reset_url = f"{base_url}/ui/?reset_token={token}"
        msg_id = f"msg_reset_{len(self.sent_emails) + 1}_{uuid.uuid4().hex[:8]}"

        # Never log the raw token or reset URL in general logs
        logger.info("AUDIT: Password reset queued in dev mailbox for '%s' <%s> (msg_id=%s)", user_name, email_clean, msg_id)
        entry = {
            "message_id": msg_id,
            "type": "reset",
            "recipient": email_clean,
            "subject": subject,
            "user_name": user_name,
            "token": token,
            "action_url": reset_url,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        self.sent_emails.append(entry)
        self._save_to_disk()
        return EmailDeliveryResult(
            success=True,
            recipient=email_clean,
            subject=subject,
            message_id=msg_id,
        )


DevMailboxEmailService = MemoryLogEmailService



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
        validate_email_configuration()
        backend = os.getenv("EMAIL_BACKEND", "").strip().lower()
        smtp_host = os.getenv("SMTP_HOST", "").strip()
        app_env = get_app_env()
        if backend == "smtp" or (app_env in ("production", "prod", "staging") and smtp_host) or (not backend and smtp_host):
            _default_service = SMTPEmailService()
        else:
            _default_service = MemoryLogEmailService()
    return _default_service


def set_email_service(service: Optional[BaseEmailService]) -> None:
    global _default_service
    _default_service = service

