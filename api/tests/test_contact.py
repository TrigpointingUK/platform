"""
Tests for contact form endpoint.
"""

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from api.core.config import settings
from api.crud.user import create_user
from api.models.user import User


@pytest.fixture
def test_user(db: Session):
    """Create a test user with unique username."""
    import uuid

    unique_name = f"testuser_{uuid.uuid4().hex[:8]}"
    user = create_user(
        db=db,
        username=unique_name,
        email=f"{unique_name}@example.com",
        auth0_user_id=f"auth0|{unique_name}",
    )
    return user


class TestContactEndpoint:
    """Test contact form submission endpoint."""

    @patch("api.api.v1.endpoints.admin.email_service")
    def test_submit_contact_unauthenticated_success(
        self, mock_email_service: MagicMock, client: TestClient
    ):
        """Test successful contact form submission without authentication."""
        mock_email_service.send_contact_email.return_value = True

        response = client.post(
            f"{settings.API_V1_STR}/admin/contact",
            json={
                "name": "John Doe",
                "email": "john@example.com",
                "subject": "Test Subject",
                "message": "This is a test message",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "successfully" in data["message"].lower()

        # Verify email service was called correctly
        mock_email_service.send_contact_email.assert_called_once()
        call_args = mock_email_service.send_contact_email.call_args
        assert call_args.kwargs["to_email"] == "contact@teasel.org"
        assert call_args.kwargs["reply_to"] == "john@example.com"
        assert call_args.kwargs["subject"] == "Test Subject"
        assert call_args.kwargs["message"] == "This is a test message"
        assert call_args.kwargs["name"] == "John Doe"
        assert call_args.kwargs["user_id"] is None
        assert call_args.kwargs["auth0_user_id"] is None
        assert call_args.kwargs["username"] is None

    @patch("api.api.v1.endpoints.admin.email_service")
    def test_submit_contact_authenticated_success(
        self,
        mock_email_service: MagicMock,
        client: TestClient,
        db: Session,
        test_user: User,
    ):
        """Test successful contact form submission with authentication."""
        mock_email_service.send_contact_email.return_value = True

        with patch("api.api.deps.auth0_validator.validate_auth0_token") as mock_token:
            mock_token.return_value = {
                "token_type": "auth0",
                "auth0_user_id": test_user.auth0_user_id,
                "sub": test_user.auth0_user_id,
                "nickname": "testuser",
                "name": "Test User",
                "scope": "api:write",
            }

            response = client.post(
                f"{settings.API_V1_STR}/admin/contact",
                json={
                    "name": "John Doe",
                    "email": "john@example.com",
                    "subject": "Test Subject",
                    "message": "This is a test message",
                    # These should be ignored/overridden by backend
                    "user_id": 99999,
                    "auth0_user_id": "fake_id",
                    "username": "fake_username",
                },
                headers={"Authorization": "Bearer mock_token"},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True

            # Verify email service was called with correct user info from token/db
            mock_email_service.send_contact_email.assert_called_once()
            call_args = mock_email_service.send_contact_email.call_args
            assert call_args.kwargs["user_id"] == test_user.id
            assert call_args.kwargs["auth0_user_id"] == test_user.auth0_user_id
            assert call_args.kwargs["username"] == "testuser"  # nickname from token
            # User-provided values should be overridden
            assert call_args.kwargs["user_id"] != 99999
            assert call_args.kwargs["auth0_user_id"] != "fake_id"
            assert call_args.kwargs["username"] != "fake_username"

    @patch("api.api.v1.endpoints.admin.email_service")
    def test_submit_contact_authenticated_no_nickname(
        self,
        mock_email_service: MagicMock,
        client: TestClient,
        db: Session,
        test_user: User,
    ):
        """Test authenticated submission when token has no nickname (uses name or db username)."""
        mock_email_service.send_contact_email.return_value = True

        with patch("api.api.deps.auth0_validator.validate_auth0_token") as mock_token:
            mock_token.return_value = {
                "token_type": "auth0",
                "auth0_user_id": test_user.auth0_user_id,
                "sub": test_user.auth0_user_id,
                "name": "Token Name",
                # No nickname
                "scope": "api:write",
            }

            response = client.post(
                f"{settings.API_V1_STR}/admin/contact",
                json={
                    "name": "John Doe",
                    "email": "john@example.com",
                    "subject": "Test Subject",
                    "message": "This is a test message",
                },
                headers={"Authorization": "Bearer mock_token"},
            )

            assert response.status_code == 200

            # Should use name from token as fallback
            call_args = mock_email_service.send_contact_email.call_args
            assert call_args.kwargs["username"] == "Token Name"

    @patch("api.api.v1.endpoints.admin.email_service")
    def test_submit_contact_authenticated_fallback_to_db_username(
        self,
        mock_email_service: MagicMock,
        client: TestClient,
        db: Session,
        test_user: User,
    ):
        """Test authenticated submission when token has neither nickname nor name (uses db username)."""
        mock_email_service.send_contact_email.return_value = True

        with patch("api.api.deps.auth0_validator.validate_auth0_token") as mock_token:
            mock_token.return_value = {
                "token_type": "auth0",
                "auth0_user_id": test_user.auth0_user_id,
                "sub": test_user.auth0_user_id,
                # No nickname or name
                "scope": "api:write",
            }

            response = client.post(
                f"{settings.API_V1_STR}/admin/contact",
                json={
                    "name": "John Doe",
                    "email": "john@example.com",
                    "subject": "Test Subject",
                    "message": "This is a test message",
                },
                headers={"Authorization": "Bearer mock_token"},
            )

            assert response.status_code == 200

            # Should fallback to database username
            call_args = mock_email_service.send_contact_email.call_args
            assert call_args.kwargs["username"] == test_user.name

    @patch("api.api.v1.endpoints.admin.email_service")
    def test_submit_contact_email_service_failure(
        self, mock_email_service: MagicMock, client: TestClient
    ):
        """Test contact form submission when email service fails."""
        mock_email_service.send_contact_email.return_value = False

        response = client.post(
            f"{settings.API_V1_STR}/admin/contact",
            json={
                "name": "John Doe",
                "email": "john@example.com",
                "subject": "Test Subject",
                "message": "This is a test message",
            },
        )

        assert response.status_code == 500
        assert "Failed to send email" in response.json()["detail"]

    def test_submit_contact_missing_fields(self, client: TestClient):
        """Test contact form submission with missing required fields."""
        response = client.post(
            f"{settings.API_V1_STR}/admin/contact",
            json={
                "name": "John Doe",
                # Missing email, subject, message
            },
        )

        assert response.status_code == 422  # Validation error

    def test_submit_contact_invalid_email(self, client: TestClient):
        """Test contact form submission with invalid email format."""
        response = client.post(
            f"{settings.API_V1_STR}/admin/contact",
            json={
                "name": "John Doe",
                "email": "not-an-email",
                "subject": "Test Subject",
                "message": "This is a test message",
            },
        )

        assert response.status_code == 422  # Validation error

    def test_submit_contact_empty_fields(self, client: TestClient):
        """Test contact form submission with empty required fields."""
        response = client.post(
            f"{settings.API_V1_STR}/admin/contact",
            json={
                "name": "",
                "email": "john@example.com",
                "subject": "Test Subject",
                "message": "This is a test message",
            },
        )

        assert response.status_code == 422  # Validation error

    def test_submit_contact_too_long_fields(self, client: TestClient):
        """Test contact form submission with fields exceeding max length."""
        response = client.post(
            f"{settings.API_V1_STR}/admin/contact",
            json={
                "name": "A" * 101,  # Exceeds max_length=100
                "email": "john@example.com",
                "subject": "Test Subject",
                "message": "This is a test message",
            },
        )

        assert response.status_code == 422  # Validation error

        response = client.post(
            f"{settings.API_V1_STR}/admin/contact",
            json={
                "name": "John Doe",
                "email": "john@example.com",
                "subject": "A" * 201,  # Exceeds max_length=200
                "message": "This is a test message",
            },
        )

        assert response.status_code == 422  # Validation error

        response = client.post(
            f"{settings.API_V1_STR}/admin/contact",
            json={
                "name": "John Doe",
                "email": "john@example.com",
                "subject": "Test Subject",
                "message": "A" * 5001,  # Exceeds max_length=5000
            },
        )

        assert response.status_code == 422  # Validation error
