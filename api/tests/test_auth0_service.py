"""
Unit tests for Auth0 service integration.
"""

from unittest.mock import Mock, call, patch

import pytest

from api.services.auth0_service import Auth0Service


class TestAuth0Service:
    """Test cases for Auth0Service."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_credentials = {
            "client_id": "test-client-id",
            "client_secret": "test-client-secret",
            "audience": "https://test-domain.auth0.com/api/v2/",
            "domain": "test-domain.auth0.com",
        }

        self.mock_user_data = {
            "user_id": "auth0|123456789",
            "username": "testuser",
            "email": "test@example.com",
            "name": "Test User",
            "identities": [
                {
                    "connection": "Username-Password-Authentication",
                    "provider": "auth0",
                }
            ],
        }

    @patch("api.services.auth0_service.settings")
    def test_init_disabled(self, mock_settings):
        """Test service initialization when Auth0 is disabled."""
        # Auth0 is now always enabled and will raise exception if not configured
        mock_settings.AUTH0_TENANT_DOMAIN = None

        with pytest.raises(
            ValueError, match="AUTH0_TENANT_DOMAIN is required but not configured"
        ):
            Auth0Service()

    @patch("api.services.auth0_service.settings")
    def test_init_enabled(self, mock_settings):
        """Test service initialization when Auth0 is enabled."""
        # Auth0 is now always enabled
        mock_settings.AUTH0_TENANT_DOMAIN = "test-domain.auth0.com"
        mock_settings.AUTH0_CONNECTION = "tme-users"

        service = Auth0Service()
        # Auth0 is now always enabled - no enabled attribute
        assert service.tenant_domain == "test-domain.auth0.com"
        assert service.connection == "tme-users"

    @patch("api.services.auth0_service.settings")
    def test_init_missing_config(self, mock_settings):
        """Test service initialization with missing configuration."""
        # Auth0 is now always enabled and will raise exception if not configured
        mock_settings.AUTH0_TENANT_DOMAIN = None
        mock_settings.AUTH0_SECRET_NAME = "test-secret"

        with pytest.raises(
            ValueError, match="AUTH0_TENANT_DOMAIN is required but not configured"
        ):
            Auth0Service()

    @patch("api.services.auth0_service.settings")
    def test_get_auth0_credentials_success(self, mock_settings):
        """Test successful retrieval of Auth0 credentials."""
        # Auth0 is now always enabled
        mock_settings.AUTH0_TENANT_DOMAIN = "test-domain.auth0.com"
        mock_settings.AUTH0_M2M_CLIENT_ID = "test-client-id"
        mock_settings.AUTH0_M2M_CLIENT_SECRET = "test-client-secret"

        service = Auth0Service()
        result = service._get_auth0_credentials()

        expected_credentials = {
            "client_id": "test-client-id",
            "client_secret": "test-client-secret",
            "domain": "test-domain.auth0.com",
        }
        assert result == expected_credentials

    @patch("api.services.auth0_service.settings")
    def test_get_auth0_credentials_missing_credentials(self, mock_settings):
        """Test handling of missing credentials."""
        # Auth0 is now always enabled
        mock_settings.AUTH0_TENANT_DOMAIN = "test-domain.auth0.com"
        mock_settings.AUTH0_M2M_CLIENT_ID = None  # Missing client ID
        mock_settings.AUTH0_M2M_CLIENT_SECRET = "test-client-secret"
        # Ensure deprecated fallbacks are not used
        mock_settings.AUTH0_M2M_CLIENT_ID = None
        mock_settings.AUTH0_M2M_CLIENT_SECRET = None

        service = Auth0Service()
        result = service._get_auth0_credentials()

        assert result is None

    # @patch("api.services.auth0_service.settings")
    # def test_get_auth0_credentials_disabled(self, mock_settings):
    #     """Test credentials retrieval when service is disabled."""
    #     # Auth0 is now always enabled - this test is no longer relevant

    #     service = Auth0Service()
    #     result = service._get_auth0_credentials()

    #     assert result is None

    @patch("requests.post")
    @patch("api.services.auth0_service.Auth0Service._get_auth0_credentials")
    @patch("api.services.auth0_service.settings")
    def test_get_access_token_success(self, mock_settings, mock_get_creds, mock_post):
        """Test successful access token retrieval."""
        # Auth0 is now always enabled
        mock_settings.AUTH0_TENANT_DOMAIN = "test-domain.auth0.com"
        mock_settings.AUTH0_SECRET_NAME = "test-secret"

        mock_get_creds.return_value = self.mock_credentials
        mock_response = Mock()
        mock_response.json.return_value = {
            "access_token": "test-access-token",
            "expires_in": 3600,
        }
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        service = Auth0Service()
        result = service._get_access_token()

        assert result == "test-access-token"
        assert service._access_token == "test-access-token"
        assert service._token_expires_at is not None

    @patch("requests.post")
    @patch("api.services.auth0_service.Auth0Service._get_auth0_credentials")
    @patch("api.services.auth0_service.settings")
    def test_get_access_token_request_error(
        self, mock_settings, mock_get_creds, mock_post
    ):
        """Test handling of request errors during token retrieval."""
        # Auth0 is now always enabled
        mock_settings.AUTH0_TENANT_DOMAIN = "test-domain.auth0.com"
        mock_settings.AUTH0_SECRET_NAME = "test-secret"

        mock_get_creds.return_value = self.mock_credentials
        mock_post.side_effect = Exception("Request failed")

        service = Auth0Service()
        result = service._get_access_token()

        assert result is None

    @patch("requests.request")
    @patch("api.services.auth0_service.Auth0Service._get_access_token")
    @patch("api.services.auth0_service.settings")
    def test_make_auth0_request_success(
        self, mock_settings, mock_get_token, mock_request
    ):
        """Test successful Auth0 API request."""
        # Auth0 is now always enabled
        mock_settings.AUTH0_TENANT_DOMAIN = "test-domain.auth0.com"
        mock_settings.AUTH0_SECRET_NAME = "test-secret"

        mock_get_token.return_value = "test-token"
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"test": "data"}
        mock_request.return_value = mock_response

        service = Auth0Service()
        result = service._make_auth0_request("GET", "users")

        assert result == {"test": "data"}
        mock_request.assert_called_once()

    @patch("requests.request")
    @patch("api.services.auth0_service.Auth0Service._get_access_token")
    @patch("api.services.auth0_service.settings")
    def test_make_auth0_request_failure(
        self, mock_settings, mock_get_token, mock_request
    ):
        """Test handling of failed Auth0 API request."""
        # Auth0 is now always enabled
        mock_settings.AUTH0_TENANT_DOMAIN = "test-domain.auth0.com"
        mock_settings.AUTH0_SECRET_NAME = "test-secret"

        mock_get_token.return_value = "test-token"
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.text = "Bad Request"
        mock_request.return_value = mock_response

        service = Auth0Service()
        result = service._make_auth0_request("GET", "users")

        assert result is None

    @patch("api.services.auth0_service.Auth0Service._make_auth0_request")
    @patch("api.services.auth0_service.settings")
    def test_find_user_by_username_success(self, mock_settings, mock_request):
        """Test successful user search by username."""
        # Auth0 is now always enabled
        mock_settings.AUTH0_TENANT_DOMAIN = "test-domain.auth0.com"
        mock_settings.AUTH0_SECRET_NAME = "test-secret"
        mock_settings.AUTH0_CONNECTION = "Username-Password-Authentication"

        mock_request.return_value = [self.mock_user_data]

        service = Auth0Service()
        result = service.find_user_by_nickname_or_name("testuser")

        assert result == self.mock_user_data
        # It should call a search by nickname or name
        called = mock_request.call_args[0][1]
        assert "nickname" in called or "name" in called

    @patch("api.services.auth0_service.Auth0Service._make_auth0_request")
    @patch("api.services.auth0_service.settings")
    def test_find_user_by_username_not_found(self, mock_settings, mock_request):
        """Test user search when user not found."""
        # Auth0 is now always enabled
        mock_settings.AUTH0_TENANT_DOMAIN = "test-domain.auth0.com"
        mock_settings.AUTH0_SECRET_NAME = "test-secret"

        mock_request.return_value = {"users": []}

        service = Auth0Service()
        result = service.find_user_by_nickname_or_name("nonexistent")

        assert result is None

    @patch("api.services.auth0_service.Auth0Service._make_auth0_request")
    @patch("api.services.auth0_service.settings")
    def test_find_user_by_email_success(self, mock_settings, mock_request):
        """Test successful user search by email."""
        # Auth0 is now always enabled
        mock_settings.AUTH0_TENANT_DOMAIN = "test-domain.auth0.com"
        mock_settings.AUTH0_SECRET_NAME = "test-secret"
        mock_settings.AUTH0_CONNECTION = "Username-Password-Authentication"

        mock_request.return_value = [self.mock_user_data]

        service = Auth0Service()
        result = service.find_user_by_email("test@example.com")

        assert result == self.mock_user_data
        mock_request.assert_called_once_with(
            "GET", 'users?q=email:"test@example.com"&search_engine=v3'
        )

    @patch("api.services.auth0_service.Auth0Service._make_auth0_request")
    @patch("api.services.auth0_service.settings")
    def test_create_user_success(self, mock_settings, mock_request):
        """Test successful user creation."""
        # Auth0 is now always enabled
        mock_settings.AUTH0_TENANT_DOMAIN = "test-domain.auth0.com"
        mock_settings.AUTH0_SECRET_NAME = "test-secret"
        mock_settings.AUTH0_CONNECTION = "Username-Password-Authentication"

        mock_request.return_value = self.mock_user_data

        service = Auth0Service()
        result = service.create_user(
            "testuser", "test@example.com", "Test User", "password123", 123
        )

        assert result == self.mock_user_data
        mock_request.assert_called_once()
        call_args = mock_request.call_args
        assert call_args[0][0] == "POST"
        assert call_args[0][1] == "users"
        sent = call_args[0][2]
        assert sent["connection"] == "Username-Password-Authentication"
        assert sent["nickname"] == "testuser"
        assert sent["name"] == "testuser"
        assert sent["password"] == "password123"
        assert sent["email_verified"] is True
        assert sent["verify_email"] is False
        assert sent["email"] == "test@example.com"
        assert sent["app_metadata"]["database_user_id"] == 123
        assert sent["app_metadata"]["original_username"] == "testuser"
        assert "legacy_sync" in sent["app_metadata"]

    @patch("api.services.auth0_service.Auth0Service._make_auth0_request")
    @patch("api.services.auth0_service.settings")
    def test_create_user_without_email(self, mock_settings, mock_request):
        """Test user creation without email."""
        # Auth0 is now always enabled
        mock_settings.AUTH0_TENANT_DOMAIN = "test-domain.auth0.com"
        mock_settings.AUTH0_SECRET_NAME = "test-secret"
        mock_settings.AUTH0_CONNECTION = "Username-Password-Authentication"

        mock_request.return_value = self.mock_user_data

        service = Auth0Service()
        result = service.create_user("testuser", None, "Test User", "password123", 123)

        assert result == self.mock_user_data
        call_args = mock_request.call_args
        assert "email" not in call_args[0][2]
        # Check that password and app_metadata are included
        user_data = call_args[0][2]
        assert user_data["password"] == "password123"
        assert user_data["app_metadata"]["database_user_id"] == 123

    @patch("api.services.auth0_service.Auth0Service._make_auth0_request")
    @patch("api.services.auth0_service.settings")
    def test_create_user_with_custom_connection(self, mock_settings, mock_request):
        """Test user creation with custom connection."""
        # Auth0 is now always enabled
        mock_settings.AUTH0_TENANT_DOMAIN = "test-domain.auth0.com"
        mock_settings.AUTH0_SECRET_NAME = "test-secret"
        mock_settings.AUTH0_CONNECTION = "tme-users"

        mock_request.return_value = self.mock_user_data

        service = Auth0Service()
        result = service.create_user(
            "testuser", "test@example.com", "Test User", "password123", 123
        )

        assert result == self.mock_user_data
        call_args = mock_request.call_args
        assert call_args[0][0] == "POST"
        assert call_args[0][1] == "users"
        sent = call_args[0][2]
        assert sent["connection"] == "tme-users"
        assert sent["nickname"] == "testuser"
        assert sent["name"] == "testuser"
        assert sent["password"] == "password123"
        assert sent["email_verified"] is True
        assert sent["verify_email"] is False
        assert sent["email"] == "test@example.com"
        assert sent["app_metadata"]["database_user_id"] == 123
        assert sent["app_metadata"]["original_username"] == "testuser"
        assert "legacy_sync" in sent["app_metadata"]

    @patch("api.services.auth0_service.Auth0Service._make_auth0_request")
    @patch("api.services.auth0_service.settings")
    def test_update_user_email_success(self, mock_settings, mock_request):
        """Test successful email update and verification email trigger."""
        # Auth0 is now always enabled
        mock_settings.AUTH0_TENANT_DOMAIN = "test-domain.auth0.com"
        mock_settings.AUTH0_SECRET_NAME = "test-secret"

        mock_request.side_effect = [
            {"nickname": "legacy_user"},
            {"success": True},
            {"job_id": "job-123"},
        ]

        service = Auth0Service()
        result = service.update_user_email("auth0|123456789", "new@example.com")

        assert result is True
        # Should make three calls: get user + update email + send verification
        assert mock_request.call_count == 3
        mock_request.assert_has_calls(
            [
                call("GET", "users/auth0|123456789"),
                call(
                    "PATCH",
                    "users/auth0|123456789",
                    {
                        "email": "new@example.com",
                        "email_verified": False,
                        "name": "legacy_user",
                    },
                ),
                call(
                    "POST",
                    "jobs/verification-email",
                    {"user_id": "auth0|123456789"},
                ),
            ],
            any_order=False,
        )

    @patch("api.services.auth0_service.Auth0Service._make_auth0_request")
    @patch("api.services.auth0_service.settings")
    def test_update_user_email_failure(self, mock_settings, mock_request):
        """Test email update failure."""
        # Auth0 is now always enabled
        mock_settings.AUTH0_TENANT_DOMAIN = "test-domain.auth0.com"
        mock_settings.AUTH0_SECRET_NAME = "test-secret"

        mock_request.side_effect = [
            {"nickname": "legacy_user"},
            None,
        ]

        service = Auth0Service()
        result = service.update_user_email("auth0|123456789", "new@example.com")

        assert result is False
        assert mock_request.call_count == 2
        mock_request.assert_has_calls(
            [
                call("GET", "users/auth0|123456789"),
                call(
                    "PATCH",
                    "users/auth0|123456789",
                    {
                        "email": "new@example.com",
                        "email_verified": False,
                        "name": "legacy_user",
                    },
                ),
            ],
            any_order=False,
        )

    @patch("api.services.auth0_service.Auth0Service.find_user_by_nickname_or_name")
    @patch("api.services.auth0_service.Auth0Service.update_user_email")
    @patch("api.services.auth0_service.settings")
    def test_sync_user_to_auth0_existing_user_email_update(
        self, mock_settings, mock_update_email, mock_find_user
    ):
        """Test sync when user exists and email needs updating."""
        # Auth0 is now always enabled
        mock_settings.AUTH0_TENANT_DOMAIN = "test-domain.auth0.com"
        mock_settings.AUTH0_SECRET_NAME = "test-secret"

        existing_user = {
            "user_id": "auth0|123456789",
            "username": "testuser",
            "email": "old@example.com",
            "name": "Test User",
        }
        mock_find_user.return_value = existing_user
        mock_update_email.return_value = True

        service = Auth0Service()
        result = service.sync_user_to_auth0(
            "testuser", "new@example.com", "Test User", "password123", 123
        )

        assert result["email"] == "new@example.com"
        mock_find_user.assert_called_once_with("testuser")
        mock_update_email.assert_called_once_with(
            "auth0|123456789", "new@example.com", "testuser"
        )

    @patch("api.services.auth0_service.Auth0Service.find_user_by_nickname_or_name")
    @patch("api.services.auth0_service.Auth0Service.create_user")
    @patch("api.services.auth0_service.settings")
    def test_sync_user_to_auth0_new_user(
        self, mock_settings, mock_create_user, mock_find_user
    ):
        """Test sync when user doesn't exist and needs to be created."""
        # Auth0 is now always enabled
        mock_settings.AUTH0_TENANT_DOMAIN = "test-domain.auth0.com"
        mock_settings.AUTH0_SECRET_NAME = "test-secret"

        mock_find_user.return_value = None
        mock_create_user.return_value = self.mock_user_data

        service = Auth0Service()
        result = service.sync_user_to_auth0(
            "testuser", "test@example.com", "Test User", "password123", 123
        )

        assert result == self.mock_user_data
        mock_find_user.assert_called_once_with("testuser")
        mock_create_user.assert_called_once_with(
            "testuser", "test@example.com", "Test User", "password123", 123, None, None
        )

    @patch("api.services.auth0_service.Auth0Service.find_user_by_nickname_or_name")
    @patch("api.services.auth0_service.settings")
    def test_sync_user_to_auth0_existing_user_no_email_change(
        self, mock_settings, mock_find_user
    ):
        """Test sync when user exists and email doesn't need updating."""
        # Auth0 is now always enabled
        mock_settings.AUTH0_TENANT_DOMAIN = "test-domain.auth0.com"
        mock_settings.AUTH0_SECRET_NAME = "test-secret"

        existing_user = {
            "user_id": "auth0|123456789",
            "username": "testuser",
            "email": "test@example.com",
            "name": "Test User",
        }
        mock_find_user.return_value = existing_user

        service = Auth0Service()
        result = service.sync_user_to_auth0(
            "testuser", "test@example.com", "Test User", "password123", 123
        )

        assert result == existing_user
        mock_find_user.assert_called_once_with("testuser")

    @patch("api.services.auth0_service.settings")
    def test_sync_user_to_auth0_disabled(self, mock_settings):
        """Test sync when Auth0 is disabled."""
        # Auth0 is now always enabled

        service = Auth0Service()
        result = service.sync_user_to_auth0(
            "testuser", "test@example.com", "Test User", "password123", 123
        )

        assert result is None

    @patch("api.services.auth0_service.Auth0Service.find_user_by_nickname_or_name")
    @patch("api.services.auth0_service.settings")
    def test_sync_user_to_auth0_exception_handling(self, mock_settings, mock_find_user):
        """Test sync exception handling."""
        # Auth0 is now always enabled
        mock_settings.AUTH0_TENANT_DOMAIN = "test-domain.auth0.com"
        mock_settings.AUTH0_SECRET_NAME = "test-secret"

        mock_find_user.side_effect = Exception("Auth0 API Error")

        service = Auth0Service()
        result = service.sync_user_to_auth0(
            "testuser", "test@example.com", "Test User", "password123", 123
        )

        assert result is None
