import os
from unittest.mock import patch, MagicMock
import pytest
from packages.security.email_service import (
    get_email_service,
    set_email_service,
    SMTPEmailService,
    MemoryLogEmailService,
)
from apps.api.routers.auth import is_email_verification_required


def test_smtp_email_service_dispatches_proper_mime_payload():
    """
    Test C4:
    SMTPEmailService must construct proper headers and dispatch through smtplib.SMTP.
    """
    service = SMTPEmailService(
        host="smtp.example.com",
        port=587,
        username="user@example.com",
        password="secretpassword",
        from_email="noreply@contentops.io",
        use_tls=True,
    )

    with patch("smtplib.SMTP") as mock_smtp_cls:
        mock_server = MagicMock()
        mock_smtp_cls.return_value.__enter__.return_value = mock_server

        res = service.send_verification_email(
            to_email="recipient@company.com",
            token="secure_token_12345",
            user_name="John Doe",
        )

        assert res.success is True
        assert res.recipient == "recipient@company.com"
        mock_server.starttls.assert_called_once()
        mock_server.login.assert_called_once_with("user@example.com", "secretpassword")
        mock_server.sendmail.assert_called_once()
        args, kwargs = mock_server.sendmail.call_args
        assert args[0] == "noreply@contentops.io"
        assert args[1] == ["recipient@company.com"]
        import email
        parsed_msg = email.message_from_string(args[2])
        decoded_payload = "".join([part.get_payload(decode=True).decode("utf-8") for part in parsed_msg.get_payload()])
        assert "secure_token_12345" in decoded_payload


def test_production_enforces_email_verification_by_default(monkeypatch):
    """
    Test C4:
    In production (APP_ENV=production), email verification must be required by default (fail-closed)
    unless explicitly set to false.
    """
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.delenv("REQUIRE_EMAIL_VERIFICATION", raising=False)

    assert is_email_verification_required() is True, "Vulnerability C4: Email verification was bypassed by default in production!"


def test_get_email_service_selects_smtp_when_configured(monkeypatch):
    """
    Test C4:
    get_email_service() must instantiate SMTPEmailService when EMAIL_BACKEND=smtp.
    """
    set_email_service(None)
    monkeypatch.setenv("EMAIL_BACKEND", "smtp")
    monkeypatch.setenv("SMTP_HOST", "smtp.sendgrid.net")

    svc = get_email_service()
    assert isinstance(svc, SMTPEmailService)
    set_email_service(None)
