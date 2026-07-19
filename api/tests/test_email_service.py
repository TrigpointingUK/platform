"""
Tests for the email service (SES).
"""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from botocore.exceptions import ClientError

from api.services import email_service as email_service_module
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


class TestPublicApiBaseUrl:
    def test_production_replaces_localhost_default(self):
        s = SimpleNamespace(
            ENVIRONMENT="production", FASTAPI_URL="http://localhost:8000"
        )
        assert (
            email_service_module._public_api_base_url(s)
            == "https://api.trigpointing.uk"
        )

    def test_staging_replaces_localhost_default(self):
        s = SimpleNamespace(ENVIRONMENT="staging", FASTAPI_URL="http://localhost:8000")
        assert (
            email_service_module._public_api_base_url(s)
            == "https://api.trigpointing.me"
        )

    def test_development_keeps_localhost(self):
        s = SimpleNamespace(
            ENVIRONMENT="development", FASTAPI_URL="http://localhost:8000"
        )
        assert email_service_module._public_api_base_url(s) == "http://localhost:8000"

    def test_explicit_public_url_preserved_in_production(self):
        s = SimpleNamespace(
            ENVIRONMENT="production",
            FASTAPI_URL="https://api.trigpointing.uk",
        )
        assert (
            email_service_module._public_api_base_url(s)
            == "https://api.trigpointing.uk"
        )

    def test_unsubscribe_url_uses_public_base(self):
        s = SimpleNamespace(
            ENVIRONMENT="production",
            FASTAPI_URL="http://localhost:8000",
            WEBHOOK_SHARED_SECRET="s3cr3t",
        )
        url = email_service_module._unsubscribe_url(s, 99)
        assert url.startswith(
            "https://api.trigpointing.uk/v1/users/archive-unsubscribe?"
        )
        assert "uid=99" in url
        assert "token=" in url

    def test_public_api_base_url_normalises_mixed_case_environment(self):
        s = SimpleNamespace(
            ENVIRONMENT="Production",
            FASTAPI_URL="http://localhost:8000",
        )
        assert (
            email_service_module._public_api_base_url(s)
            == "https://api.trigpointing.uk"
        )

    def test_site_url_normalises_mixed_case_environment(self):
        assert email_service_module._site_url("Production") == "https://trigpointing.uk"

    def test_email_transactional_bases_ignore_localhost_in_production(self):
        s = SimpleNamespace(
            ENVIRONMENT="production",
            FASTAPI_URL="http://localhost:8000",
            PUBLIC_WEB_BASE_URL=None,
            PUBLIC_API_BASE_URL=None,
        )
        site, api = email_service_module._email_transactional_bases(s)
        assert site == "https://trigpointing.uk"
        assert api == "https://api.trigpointing.uk"

    def test_email_transactional_bases_respect_public_overrides(self):
        s = SimpleNamespace(
            ENVIRONMENT="production",
            FASTAPI_URL="http://localhost:8000",
            PUBLIC_WEB_BASE_URL="https://example.org",
            PUBLIC_API_BASE_URL="https://api.example.org",
        )
        site, api = email_service_module._email_transactional_bases(s)
        assert site == "https://example.org"
        assert api == "https://api.example.org"


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


class TestUnsubscribeToken:
    def test_verify_accepts_matching_token(self):
        token = email_service_module._unsubscribe_token("s3cr3t", 42)
        assert email_service_module.verify_unsubscribe_token("s3cr3t", 42, token)

    def test_verify_rejects_wrong_token(self):
        assert not email_service_module.verify_unsubscribe_token(
            "s3cr3t", 42, "deadbeef"
        )


class TestHelperBranches:
    def test_build_display_name_with_names(self):
        assert (
            email_service_module._build_display_name("Ada", "Lovelace", "ada")
            == "Ada Lovelace (ada)"
        )

    def test_build_display_name_falls_back_to_username(self):
        assert email_service_module._build_display_name(None, "  ", "ada") == "ada"

    def test_transactional_bases_staging(self):
        s = SimpleNamespace(
            ENVIRONMENT="staging",
            FASTAPI_URL="http://localhost:8000",
            PUBLIC_WEB_BASE_URL=None,
            PUBLIC_API_BASE_URL=None,
        )
        site, api = email_service_module._email_transactional_bases(s)
        assert site == "https://trigpointing.me"
        assert api == "https://api.trigpointing.me"

    def test_transactional_bases_development_falls_back(self):
        s = SimpleNamespace(
            ENVIRONMENT="development",
            FASTAPI_URL="http://localhost:8000",
            PUBLIC_WEB_BASE_URL=None,
            PUBLIC_API_BASE_URL=None,
        )
        site, api = email_service_module._email_transactional_bases(s)
        assert site == "http://localhost:5173"
        assert api == "http://localhost:8000"

    def test_public_api_base_url_defaults_when_fastapi_url_blank(self):
        s = SimpleNamespace(ENVIRONMENT="staging", FASTAPI_URL="")
        # Blank FASTAPI_URL falls back to localhost default, then env mapping.
        assert (
            email_service_module._public_api_base_url(s)
            == "https://api.trigpointing.me"
        )


class TestSendArchiveEmail:
    def setup_method(self):
        self.svc = EmailService.__new__(EmailService)
        self.svc.ses_client = MagicMock()
        self.svc.from_email = "contact@trigpointing.uk"

    def test_returns_false_when_client_is_none(self):
        self.svc.ses_client = None
        result = self.svc.send_archive_email(
            to_email="user@example.com",
            username="bob",
            zip_bytes=b"zip",
            filename="archive.zip",
            log_count=3,
        )
        assert result is False

    @patch("api.core.config.settings")
    def test_production_keeps_recipient_and_sends(self, mock_settings):
        mock_settings.ENVIRONMENT = "production"
        mock_settings.PUBLIC_WEB_BASE_URL = None
        mock_settings.PUBLIC_API_BASE_URL = None
        mock_settings.FASTAPI_URL = "http://localhost:8000"
        mock_settings.WEBHOOK_SHARED_SECRET = "s3cr3t"
        self.svc.ses_client.send_raw_email.return_value = {"MessageId": "m1"}

        result = self.svc.send_archive_email(
            to_email="user@example.com",
            username="bob",
            zip_bytes=b"zipdata",
            filename="archive.zip",
            log_count=5,
            user_id=7,
            firstname="Bob",
            surname="Smith",
        )
        assert result is True
        kwargs = self.svc.ses_client.send_raw_email.call_args[1]
        assert kwargs["Destinations"] == ["user@example.com"]

    @patch("api.core.config.settings")
    def test_non_production_overrides_recipient(self, mock_settings):
        mock_settings.ENVIRONMENT = "staging"
        mock_settings.PUBLIC_WEB_BASE_URL = None
        mock_settings.PUBLIC_API_BASE_URL = None
        mock_settings.FASTAPI_URL = "http://localhost:8000"
        mock_settings.WEBHOOK_SHARED_SECRET = "s3cr3t"
        self.svc.ses_client.send_raw_email.return_value = {"MessageId": "m2"}

        result = self.svc.send_archive_email(
            to_email="user@example.com",
            username="bob",
            zip_bytes=b"zip",
            filename="archive.zip",
            log_count=1,
        )
        assert result is True
        kwargs = self.svc.ses_client.send_raw_email.call_args[1]
        assert kwargs["Destinations"] == ["test@teasel.org"]

    @patch("api.core.config.settings")
    def test_returns_false_on_client_error(self, mock_settings):
        mock_settings.ENVIRONMENT = "production"
        mock_settings.PUBLIC_WEB_BASE_URL = None
        mock_settings.PUBLIC_API_BASE_URL = None
        mock_settings.FASTAPI_URL = "http://localhost:8000"
        mock_settings.WEBHOOK_SHARED_SECRET = "s3cr3t"
        self.svc.ses_client.send_raw_email.side_effect = ClientError(
            {"Error": {"Code": "Throttling", "Message": "slow down"}}, "SendRawEmail"
        )
        result = self.svc.send_archive_email(
            to_email="user@example.com",
            username="bob",
            zip_bytes=b"zip",
            filename="archive.zip",
            log_count=1,
        )
        assert result is False

    @patch("api.core.config.settings")
    def test_returns_false_on_unexpected_error(self, mock_settings):
        mock_settings.ENVIRONMENT = "production"
        mock_settings.PUBLIC_WEB_BASE_URL = None
        mock_settings.PUBLIC_API_BASE_URL = None
        mock_settings.FASTAPI_URL = "http://localhost:8000"
        mock_settings.WEBHOOK_SHARED_SECRET = "s3cr3t"
        self.svc.ses_client.send_raw_email.side_effect = RuntimeError("boom")
        result = self.svc.send_archive_email(
            to_email="user@example.com",
            username="bob",
            zip_bytes=b"zip",
            filename="archive.zip",
            log_count=1,
        )
        assert result is False


class TestSendDeletionBackupEmail:
    def setup_method(self):
        self.svc = EmailService.__new__(EmailService)
        self.svc.ses_client = MagicMock()
        self.svc.from_email = "contact@trigpointing.uk"

    def test_returns_false_when_client_is_none(self):
        self.svc.ses_client = None
        result = self.svc.send_deletion_backup_email(
            to_email="user@example.com",
            username="bob",
            zip_bytes=b"zip",
            filename="backup.zip",
            log_count=2,
        )
        assert result is False

    @patch("api.core.config.settings")
    def test_production_sends_to_real_recipient(self, mock_settings):
        mock_settings.ENVIRONMENT = "production"
        self.svc.ses_client.send_raw_email.return_value = {"MessageId": "d1"}
        result = self.svc.send_deletion_backup_email(
            to_email="user@example.com",
            username="bob",
            zip_bytes=b"zip",
            filename="backup.zip",
            log_count=2,
            user_id=9,
            firstname="Bob",
        )
        assert result is True
        kwargs = self.svc.ses_client.send_raw_email.call_args[1]
        assert kwargs["Destinations"] == ["user@example.com"]

    @patch("api.core.config.settings")
    def test_non_production_overrides_recipient(self, mock_settings):
        mock_settings.ENVIRONMENT = "staging"
        self.svc.ses_client.send_raw_email.return_value = {"MessageId": "d2"}
        result = self.svc.send_deletion_backup_email(
            to_email="user@example.com",
            username="bob",
            zip_bytes=b"zip",
            filename="backup.zip",
            log_count=2,
        )
        assert result is True
        kwargs = self.svc.ses_client.send_raw_email.call_args[1]
        assert kwargs["Destinations"] == ["test@teasel.org"]

    @patch("api.core.config.settings")
    def test_returns_false_on_client_error(self, mock_settings):
        mock_settings.ENVIRONMENT = "production"
        self.svc.ses_client.send_raw_email.side_effect = ClientError(
            {"Error": {"Code": "Throttling", "Message": "slow"}}, "SendRawEmail"
        )
        result = self.svc.send_deletion_backup_email(
            to_email="user@example.com",
            username="bob",
            zip_bytes=b"zip",
            filename="backup.zip",
            log_count=2,
        )
        assert result is False

    @patch("api.core.config.settings")
    def test_returns_false_on_unexpected_error(self, mock_settings):
        mock_settings.ENVIRONMENT = "production"
        self.svc.ses_client.send_raw_email.side_effect = RuntimeError("boom")
        result = self.svc.send_deletion_backup_email(
            to_email="user@example.com",
            username="bob",
            zip_bytes=b"zip",
            filename="backup.zip",
            log_count=2,
        )
        assert result is False
