"""
Email service for sending emails via AWS SES.
"""

import json
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

import boto3
from botocore.exceptions import ClientError

from api.core.logging import get_logger

logger = get_logger(__name__)


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

        msg = MIMEMultipart("mixed")
        msg["Subject"] = f"TrigpointingUK Data Archive for {username}"
        msg["From"] = self.from_email
        msg["To"] = actual_recipient

        body_html = (
            f"<html><body>"
            f"<p>Hello {username},</p>"
            f"<p>Please find attached your TrigpointingUK data archive "
            f"containing <strong>{log_count}</strong> published log(s).</p>"
            f"<p>This archive was generated on {filename.split('_')[-1].replace('.zip', '')} UTC.</p>"
            f"<p>If you no longer wish to receive these emails, you can change "
            f"your archive frequency in your TrigpointingUK account settings.</p>"
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
