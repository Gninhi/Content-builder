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


_default_service: Optional[BaseEmailService] = None


def get_email_service() -> BaseEmailService:
    global _default_service
    if _default_service is None:
        # Defaults to MemoryLogEmailService for local dev & testing
        _default_service = MemoryLogEmailService()
    return _default_service


def set_email_service(service: BaseEmailService) -> None:
    global _default_service
    _default_service = service
