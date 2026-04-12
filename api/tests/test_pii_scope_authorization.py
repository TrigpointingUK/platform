"""
Tests for user profile email updates (previously gated by api:read-pii scope).

Email updates on /me no longer require a special scope -- any authenticated
user may update their own email address.
"""

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from api.crud.user import create_user
from api.main import app

client = TestClient(app)


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


def test_update_email_without_pii_scope_succeeds(db: Session, test_user):
    """Test that updating email on own profile succeeds without api:read-pii scope."""
    import uuid

    unique_suffix = uuid.uuid4().hex[:8]

    with patch("api.api.deps.auth0_validator.validate_auth0_token") as mock:
        mock.return_value = {
            "token_type": "auth0",
            "auth0_user_id": test_user.auth0_user_id,
            "sub": test_user.auth0_user_id,
            "scope": "openid profile email",
        }

        with patch("api.services.auth0_service.auth0_service") as mock_service:
            mock_service.update_user_email.return_value = True
            new_email = f"newemail_{unique_suffix}@example.com"

            response = client.patch(
                "/v1/users/me",
                json={"email": new_email},
                headers={"Authorization": "Bearer mock_token"},
            )

            assert response.status_code == 200


def test_update_firstname_without_scope_succeeds(db: Session, test_user):
    """Test that updating firstname without api:read-pii scope succeeds (not PII)."""
    with patch("api.api.deps.auth0_validator.validate_auth0_token") as mock:
        mock.return_value = {
            "token_type": "auth0",
            "auth0_user_id": test_user.auth0_user_id,
            "sub": test_user.auth0_user_id,
            "scope": "api:write",
        }

        response = client.patch(
            "/v1/users/me",
            json={"firstname": "John"},
            headers={"Authorization": "Bearer mock_token"},
        )

        assert response.status_code == 200
        assert response.json()["firstname"] == "John"


def test_update_surname_without_scope_succeeds(db: Session, test_user):
    """Test that updating surname without api:read-pii scope succeeds (not PII)."""
    with patch("api.api.deps.auth0_validator.validate_auth0_token") as mock:
        mock.return_value = {
            "token_type": "auth0",
            "auth0_user_id": test_user.auth0_user_id,
            "sub": test_user.auth0_user_id,
            "scope": "api:write",
        }

        response = client.patch(
            "/v1/users/me",
            json={"surname": "Doe"},
            headers={"Authorization": "Bearer mock_token"},
        )

        assert response.status_code == 200
        assert response.json()["surname"] == "Doe"


def test_update_non_pii_fields_without_pii_scope_succeeds(db: Session, test_user):
    """Test that updating non-PII fields works without api:read-pii scope."""
    import uuid

    unique_suffix = uuid.uuid4().hex[:8]

    with patch("api.api.deps.auth0_validator.validate_auth0_token") as mock:
        mock.return_value = {
            "token_type": "auth0",
            "auth0_user_id": test_user.auth0_user_id,
            "sub": test_user.auth0_user_id,
            "scope": "api:write",
        }

        with patch("api.services.auth0_service.auth0_service") as mock_service:
            mock_service.update_user_profile.return_value = True
            new_username = f"newusername_{unique_suffix}"

            response = client.patch(
                "/v1/users/me",
                json={"name": new_username, "homepage": "https://example.com"},
                headers={"Authorization": "Bearer mock_token"},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["name"] == new_username
            assert data["homepage"] == "https://example.com"


def test_update_email_with_scope_succeeds(db: Session, test_user):
    """Test that updating email with api:read-pii scope also succeeds."""
    import uuid

    unique_suffix = uuid.uuid4().hex[:8]

    with patch("api.api.deps.auth0_validator.validate_auth0_token") as mock:
        mock.return_value = {
            "token_type": "auth0",
            "auth0_user_id": test_user.auth0_user_id,
            "sub": test_user.auth0_user_id,
            "scope": "api:write api:read-pii",
        }

        with patch("api.services.auth0_service.auth0_service") as mock_service:
            mock_service.update_user_email.return_value = True
            new_email = f"newemail_{unique_suffix}@example.com"

            response = client.patch(
                "/v1/users/me",
                json={"email": new_email},
                headers={"Authorization": "Bearer mock_token"},
            )

            assert response.status_code == 200
