"""
Tests for the email service (SES).
"""

from unittest.mock import MagicMock, patch

from botocore.exceptions import ClientError

from api.services.email_service import EmailService


class TestEmailServiceInit:
    @patch("api.services.email_service.boto3.client")
    def test_successful_init(self, mock_boto_client):
        svc = EmailService(region_name="eu-west-1")
        assert svc.ses_client is not None
        assert svc.from_email == "contact@trigpointing.uk"

    @patch("api.services.email_service.boto3.client", side_effect=Exception("fail"))
    def test_init_failure_sets_client_none(self, mock_boto_client):
        svc = EmailService()
        assert svc.ses_client is None


class TestSendContactEmail:
    def setup_method(self):
        self.svc = EmailService.__new__(EmailService)
        self.svc.ses_client = MagicMock()
        self.svc.from_email = "contact@trigpointing.uk"

    def test_successful_send(self):
        self.svc.ses_client.send_email.return_value = {"MessageId": "abc123"}
        result = self.svc.send_contact_email(
            to_email="admin@example.com",
            reply_to="user@example.com",
            subject="Test Subject",
            message="Hello",
            name="Test User",
        )
        assert result is True
        self.svc.ses_client.send_email.assert_called_once()

    def test_includes_optional_fields_in_body(self):
        self.svc.ses_client.send_email.return_value = {"MessageId": "xyz"}
        result = self.svc.send_contact_email(
            to_email="admin@example.com",
            reply_to="user@example.com",
            subject="Test",
            message="Hi",
            name="Bob",
            user_id=42,
            auth0_user_id="auth0|42",
            username="bob42",
        )
        assert result is True
        call_args = self.svc.ses_client.send_email.call_args
        body = call_args[1]["Message"]["Body"]["Text"]["Data"]
        assert "bob42" in body
        assert "User ID: 42" in body
        assert "auth0|42" in body

    def test_returns_false_when_client_is_none(self):
        self.svc.ses_client = None
        result = self.svc.send_contact_email(
            to_email="admin@example.com",
            reply_to="user@example.com",
            subject="Test",
            message="Hello",
            name="Test",
        )
        assert result is False

    def test_returns_false_on_client_error(self):
        error_response = {"Error": {"Code": "MessageRejected", "Message": "bounce"}}
        self.svc.ses_client.send_email.side_effect = ClientError(
            error_response, "SendEmail"
        )
        result = self.svc.send_contact_email(
            to_email="admin@example.com",
            reply_to="user@example.com",
            subject="Test",
            message="Hello",
            name="Test",
        )
        assert result is False

    def test_returns_false_on_unexpected_error(self):
        self.svc.ses_client.send_email.side_effect = RuntimeError("unexpected")
        result = self.svc.send_contact_email(
            to_email="admin@example.com",
            reply_to="user@example.com",
            subject="Test",
            message="Hello",
            name="Test",
        )
        assert result is False
