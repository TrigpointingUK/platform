"""
Email service for sending emails via AWS SES.
"""

import hashlib
import hmac
import json
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional
from urllib.parse import urlencode

import boto3
from botocore.exceptions import ClientError

from api.core.logging import get_logger

logger = get_logger(__name__)

_SITE_URLS = {
    "production": "https://trigpointing.uk",
    "staging": "https://trigpointing.me",
}

# Public API host for links in outbound email (matches ALB / Cloudflare hostnames).
_API_PUBLIC_BASE_BY_ENV = {
    "production": "https://api.trigpointing.uk",
    "staging": "https://api.trigpointing.me",
}


def _site_url(environment: str) -> str:
    return _SITE_URLS.get(environment, "http://localhost:5173")


def _is_loopback_api_url(url: str) -> bool:
    u = url.strip().lower()
    return (
        "localhost" in u
        or u.startswith("http://127.")
        or u.startswith("https://127.")
        or "::1" in u
    )


def _public_api_base_url(settings: object) -> str:
    """
    Base URL for user-facing API links in email (unsubscribe, etc.).

    ECS tasks often omit FASTAPI_URL, so Pydantic leaves the localhost default; we
    still infer the correct public hostname from ENVIRONMENT.
    """
    env = (
        str(getattr(settings, "ENVIRONMENT", "development") or "development")
        .strip()
        .lower()
    )
    raw = str(getattr(settings, "FASTAPI_URL", "") or "").strip().rstrip("/")
    if not raw:
        raw = "http://localhost:8000"
    if not _is_loopback_api_url(raw):
        return raw
    return _API_PUBLIC_BASE_BY_ENV.get(env, raw)


def _build_display_name(
    firstname: Optional[str], surname: Optional[str], username: str
) -> str:
    parts = [p.strip() for p in (firstname, surname) if p and p.strip()]
    if parts:
        return f"{' '.join(parts)} ({username})"
    return username


def _unsubscribe_token(secret: str, user_id: int) -> str:
    """HMAC-SHA256 token for one-click archive unsubscribe."""
    return hmac.new(
        secret.encode(),
        f"archive-unsubscribe-{user_id}".encode(),
        hashlib.sha256,
    ).hexdigest()


def verify_unsubscribe_token(secret: str, user_id: int, token: str) -> bool:
    expected = _unsubscribe_token(secret, user_id)
    return hmac.compare_digest(expected, token)


def _unsubscribe_url(settings: object, user_id: Optional[int]) -> str:
    """Build a signed one-click unsubscribe URL."""
    secret = getattr(settings, "WEBHOOK_SHARED_SECRET", None) or "dev-fallback"
    api_base = _public_api_base_url(settings)
    token = _unsubscribe_token(secret, user_id or 0)
    qs = urlencode({"uid": user_id or 0, "token": token})
    return f"{api_base}/v1/users/archive-unsubscribe?{qs}"


class EmailService:
    """Service for sending emails via AWS SES."""

    def __init__(self, region_name: str = "eu-west-1"):
        """Initialise the SES client."""
        try:
            self.ses_client = boto3.client("ses", region_name=region_name)
            self.from_email = "contact@trigpointing.uk"
        except Exception as e:
            logger.error(f"Failed to initialise SES client: {e}")
            self.ses_client = None

    def send_contact_email(
        self,
        to_email: str,
        reply_to: str,
        subject: str,
        message: str,
        name: str,
        user_id: Optional[int] = None,
        auth0_user_id: Optional[str] = None,
        username: Optional[str] = None,
    ) -> bool:
        """
        Send a contact form email via SES.

        Args:
            to_email: Recipient email address
            reply_to: Reply-To email address
            subject: Email subject
            message: Email message body
            name: Sender's name
            user_id: Optional database user ID (for logged-in users)
            auth0_user_id: Optional Auth0 user ID (for logged-in users)

        Returns:
            True if successful, False otherwise
        """
        if not self.ses_client:
            logger.error("SES client not available")
            return False

        # Build email body with message and metadata
        body_text = f"{message}\n\n"
        body_text += "---\n"
        body_text += f"From: {name} ({reply_to})\n"
        if username:
            body_text += f"Username: {username}\n"
        if user_id:
            body_text += f"User ID: {user_id}\n"
        if auth0_user_id:
            body_text += f"Auth0 User ID: {auth0_user_id}\n"

        try:
            response = self.ses_client.send_email(
                Source=self.from_email,
                Destination={"ToAddresses": [to_email]},
                Message={
                    "Subject": {"Data": subject, "Charset": "UTF-8"},
                    "Body": {"Text": {"Data": body_text, "Charset": "UTF-8"}},
                },
                ReplyToAddresses=[reply_to],
            )

            log_data = {
                "event": "contact_email_sent",
                "to": to_email,
                "reply_to": reply_to,
                "subject": subject,
                "message_id": response.get("MessageId", ""),
                "username": username,
                "user_id": user_id,
                "auth0_user_id": auth0_user_id,
            }
            logger.info(json.dumps(log_data))

            return True

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            error_message = e.response.get("Error", {}).get("Message", str(e))

            log_data = {
                "event": "contact_email_failed",
                "to": to_email,
                "reply_to": reply_to,
                "error_code": error_code,
                "error_message": error_message,
                "username": username,
                "user_id": user_id,
                "auth0_user_id": auth0_user_id,
            }
            logger.error(json.dumps(log_data))

            return False

        except Exception as e:
            log_data = {
                "event": "contact_email_error",
                "to": to_email,
                "reply_to": reply_to,
                "error": str(e),
                "username": username,
                "user_id": user_id,
                "auth0_user_id": auth0_user_id,
            }
            logger.error(json.dumps(log_data))

            return False

    def send_archive_email(
        self,
        to_email: str,
        username: str,
        zip_bytes: bytes,
        filename: str,
        log_count: int,
        user_id: Optional[int] = None,
        firstname: Optional[str] = None,
        surname: Optional[str] = None,
    ) -> bool:
        """
        Send an archive email with a zip file attachment via SES SendRawEmail.

        In non-production environments, the recipient is always overridden to
        test@teasel.org to prevent accidental emails to real users.

        Returns:
            True if successful, False otherwise
        """
        from api.core.config import settings

        if not self.ses_client:
            logger.error("SES client not available")
            return False

        actual_recipient = to_email
        if settings.ENVIRONMENT != "production":
            actual_recipient = "test@teasel.org"
            logger.info(
                json.dumps(
                    {
                        "event": "archive_email_recipient_override",
                        "original_recipient": to_email,
                        "actual_recipient": actual_recipient,
                        "environment": settings.ENVIRONMENT,
                        "user_id": user_id,
                    }
                )
            )

        display_name = _build_display_name(firstname, surname, username)
        site_url = _site_url(settings.ENVIRONMENT)
        prefs_url = f"{site_url}/preferences#data-archive"
        unsubscribe_url = _unsubscribe_url(settings, user_id)

        msg = MIMEMultipart("mixed")
        msg["Subject"] = f"TrigpointingUK Data Archive for {username}"
        msg["From"] = self.from_email
        msg["To"] = actual_recipient
        msg["List-Unsubscribe"] = f"<{unsubscribe_url}>"
        # RFC 8058: MUAs POST List-Unsubscribe=One-Click to the same URI (see POST handler).
        msg["List-Unsubscribe-Post"] = "List-Unsubscribe=One-Click"

        body_html = (
            f"<html><body>"
            f"<p>Hello {display_name},</p>"
            f"<p>You are receiving this email because you are, or have been, "
            f"an active user of the TrigpointingUK website.</p>"
            f"<p>All users are sent a backup archive of all their logs, once every "
            f"year on an opt-out basis, or more frequently on an opt-in basis.</p>"
            f"<p>If you no longer wish to receive these emails, "
            f'<a href="{unsubscribe_url}">click here to unsubscribe</a>.</p>'
            f"<p>To change how often you receive these archives, choose what they contain, "
            f"or request an adhoc email be sent with your latest logs, visit your "
            f'<a href="{prefs_url}">preferences</a> page.</p>'
            f"<p>Please find attached your TrigpointingUK backup archive "
            f"containing <strong>{log_count}</strong> published log(s).</p>"
            f"<p>— TrigpointingUK</p>"
            f"</body></html>"
        )
        body_part = MIMEText(body_html, "html", "utf-8")
        msg.attach(body_part)

        attachment = MIMEApplication(zip_bytes, "zip")
        attachment.add_header("Content-Disposition", "attachment", filename=filename)
        msg.attach(attachment)

        try:
            response = self.ses_client.send_raw_email(
                Source=self.from_email,
                Destinations=[actual_recipient],
                RawMessage={"Data": msg.as_string()},
            )

            logger.info(
                json.dumps(
                    {
                        "event": "archive_email_sent",
                        "to": actual_recipient,
                        "original_to": to_email,
                        "message_id": response.get("MessageId", ""),
                        "username": username,
                        "user_id": user_id,
                        "zip_size_bytes": len(zip_bytes),
                        "log_count": log_count,
                    }
                )
            )
            return True

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            error_message = e.response.get("Error", {}).get("Message", str(e))
            logger.error(
                json.dumps(
                    {
                        "event": "archive_email_failed",
                        "to": actual_recipient,
                        "error_code": error_code,
                        "error_message": error_message,
                        "user_id": user_id,
                    }
                )
            )
            return False

        except Exception as e:
            logger.error(
                json.dumps(
                    {
                        "event": "archive_email_error",
                        "to": actual_recipient,
                        "error": str(e),
                        "user_id": user_id,
                    }
                )
            )
            return False


# Singleton instance
email_service = EmailService()
