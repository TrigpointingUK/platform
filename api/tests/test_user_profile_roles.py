"""
Tests for Auth0 roles in user profile endpoint.
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
    """Create a test user."""
    user = create_user(
        db=db,
        username="testuser",
        email="test@example.com",
        auth0_user_id="auth0|test123",
    )
    return user


def test_get_profile_includes_roles(db: Session, test_user):
    """Test that GET /v1/users/me includes roles from Auth0 token."""
    with patch("api.api.deps.auth0_validator.validate_auth0_token") as mock:
        # Mock token with roles in custom claim
        mock.return_value = {
            "token_type": "auth0",
            "auth0_user_id": test_user.auth0_user_id,
            "sub": test_user.auth0_user_id,
            "scope": "api:read",
            "https://trigpointing.uk/roles": ["api-admin", "forum-moderator"],
        }

        response = client.get(
            "/v1/users/me",
            headers={"Authorization": "Bearer mock_token"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "roles" in data
        assert data["roles"] == ["api-admin", "forum-moderator"]


def test_get_profile_no_roles(db: Session, test_user):
    """Test that GET /v1/users/me returns empty roles list when user has no roles."""
    with patch("api.api.deps.auth0_validator.validate_auth0_token") as mock:
        # Mock token without roles
        mock.return_value = {
            "token_type": "auth0",
            "auth0_user_id": test_user.auth0_user_id,
            "sub": test_user.auth0_user_id,
            "scope": "api:read",
            "https://trigpointing.uk/roles": [],
        }

        response = client.get(
            "/v1/users/me",
            headers={"Authorization": "Bearer mock_token"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "roles" in data
        assert data["roles"] == []


def test_get_profile_missing_roles_claim(db: Session, test_user):
    """Test that GET /v1/users/me handles missing roles claim gracefully."""
    with patch("api.api.deps.auth0_validator.validate_auth0_token") as mock:
        # Mock token without roles claim
        mock.return_value = {
            "token_type": "auth0",
            "auth0_user_id": test_user.auth0_user_id,
            "sub": test_user.auth0_user_id,
            "scope": "api:read",
        }

        response = client.get(
            "/v1/users/me",
            headers={"Authorization": "Bearer mock_token"},
        )

        assert response.status_code == 200
        data = response.json()
        # Should return empty list when claim is missing
        assert "roles" in data
        assert data["roles"] == []
