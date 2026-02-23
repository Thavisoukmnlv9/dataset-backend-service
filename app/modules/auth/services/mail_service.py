"""
Email service for sending verification and password-reset OTPs.

Supports Brevo HTTP API with SMTP fallback. Configuration is read from
the centralised Settings object — never from os.getenv at module level.
"""
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

import requests
from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.core.config import settings

logger = logging.getLogger(__name__)

# ── Template setup ───────────────────────────────────────────────────────────

_TEMPLATES_DIR = Path(__file__).resolve().parents[2] / "shared" / "email_templates"

_jinja_env = Environment(
    loader=FileSystemLoader(str(_TEMPLATES_DIR)),
    autoescape=select_autoescape(["html", "xml"]),
)

_VERIFICATION_PLAIN = """Hello!

Your dataset verification code is: {otp}

This code expires in 10 minutes.

If you didn't request this code, please ignore this email.

Best regards,
The dataset Team
"""

_PASSWORD_RESET_PLAIN = """Hello!

Your dataset password reset code is: {otp}

This code expires in 10 minutes.

If you didn't request a password reset, you can safely ignore this email.

Best regards,
The dataset Team
"""


# ── Internal helpers ─────────────────────────────────────────────────────────

def _smtp_config() -> dict:
    return {
        "host": settings.smtp_host,
        "port": settings.smtp_port,
        "user": settings.smtp_username,
        "password": settings.smtp_password,
        "from_email": settings.smtp_from_email,
        "from_name": settings.smtp_from_name,
    }


def _send_via_brevo_api(
    to_email: str, subject: str, html: str, text: str
) -> bool:
    import os
    api_key = os.getenv("BREVO_API_KEY")
    if not api_key:
        logger.warning("BREVO_API_KEY not set — skipping API send")
        return False

    cfg = _smtp_config()
    payload = {
        "sender": {"name": cfg["from_name"], "email": cfg["from_email"]},
        "to": [{"email": to_email}],
        "subject": subject,
        "htmlContent": html,
        "textContent": text,
    }
    headers = {
        "accept": "application/json",
        "api-key": api_key,
        "content-type": "application/json",
    }
    try:
        resp = requests.post(
            "https://api.brevo.com/v3/smtp/email",
            json=payload,
            headers=headers,
            timeout=15,
        )
        if resp.status_code == 201:
            logger.info("Email sent via Brevo API to %s", to_email)
            return True
        logger.error("Brevo API %s: %s", resp.status_code, resp.text)
        return False
    except Exception as exc:
        logger.error("Brevo API error for %s: %s", to_email, exc)
        return False


def _send_via_smtp(to_email: str, subject: str, html: str, text: str) -> bool:
    cfg = _smtp_config()
    try:
        msg = MIMEMultipart("alternative")
        msg["From"] = f"{cfg['from_name']} <{cfg['from_email']}>"
        msg["To"] = to_email
        msg["Subject"] = subject
        msg.attach(MIMEText(text, "plain", "utf-8"))
        msg.attach(MIMEText(html, "html", "utf-8"))

        with smtplib.SMTP(cfg["host"], cfg["port"]) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(cfg["user"], cfg["password"])
            server.send_message(msg)

        logger.info("Email sent via SMTP to %s", to_email)
        return True
    except Exception as exc:
        logger.exception("SMTP send failed for %s: %s", to_email, exc)
        return False


def _send_email(to_email: str, subject: str, html: str, text: str) -> bool:
    """Try Brevo API first, fall back to SMTP."""
    if _send_via_brevo_api(to_email, subject, html, text):
        return True
    logger.warning("API failed — falling back to SMTP for %s", to_email)
    return _send_via_smtp(to_email, subject, html, text)


# ── Public API ───────────────────────────────────────────────────────────────

def send_verification_email(to_email: str, otp: str) -> bool:
    """Send an email-verification OTP."""
    html = _jinja_env.get_template("verify_email.html").render(otp=otp)
    text = _VERIFICATION_PLAIN.format(otp=otp)
    return _send_email(to_email, "Your dataset Verification Code", html, text)


def send_password_reset_otp_email(to_email: str, otp: str) -> bool:
    """Send a password-reset OTP."""
    html = _jinja_env.get_template("password_reset_otp.html").render(otp=otp)
    text = _PASSWORD_RESET_PLAIN.format(otp=otp)
    return _send_email(to_email, "Reset Your dataset Password", html, text)
