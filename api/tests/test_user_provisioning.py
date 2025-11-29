"""
Tests for POST /v1/users user provisioning endpoint.
"""

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from api.crud.user import create_user
from api.main import app

client = TestClient(app)


@pytest.fixture
def mock_webhook_secret(monkeypatch):
    """Mock WEBHOOK_SHARED_SECRET configuration."""
    test_secret = "test_webhook_secret_12345"
    monkeypatch.setattr("api.core.config.settings.WEBHOOK_SHARED_SECRET", test_secret)
    return test_secret


def test_create_user_success(db: Session, mock_webhook_secret):
    """Test successful user creation via POST endpoint."""
    import uuid

    unique_suffix = uuid.uuid4().hex[:8]
    payload = {
        "username": f"newuser_{unique_suffix}",
        "email": f"newuser_{unique_suffix}@example.com",
        "auth0_user_id": f"auth0|newuser_{unique_suffix}",
    }

    response = client.post(
        "/v1/users",
        json=payload,
        headers={"X-Webhook-Secret": mock_webhook_secret},
    )

    assert response.status_code == 201
    data = response.json()
    assert data["name"] == f"newuser_{unique_suffix}"
    assert data["email"] == f"newuser_{unique_suffix}@example.com"
    assert data["auth0_user_id"] == f"auth0|newuser_{unique_suffix}"
    assert "id" in data


def test_create_user_invalid_token(db: Session, mock_webhook_secret):
    """Test that invalid webhook secret returns 401."""
    payload = {
        "username": "testuser",
        "email": "test@example.com",
        "auth0_user_id": "auth0|test123",
    }

    response = client.post(
        "/v1/users",
        json=payload,
        headers={"X-Webhook-Secret": "wrong_secret"},
    )

    assert response.status_code == 401


def test_create_user_missing_token(db: Session, mock_webhook_secret):
    """Test that missing webhook secret returns 401."""
    payload = {
        "username": "testuser",
        "email": "test@example.com",
        "auth0_user_id": "auth0|test123",
    }

    response = client.post("/v1/users", json=payload)

    assert response.status_code == 401


def test_create_user_duplicate_username(db: Session, mock_webhook_secret):
    """Test that duplicate username returns 409 with proper error message.

    This test verifies the error format that the Auth0 Action relies on
    to detect username collisions and retry with a different name.
    """
    import uuid

    unique_suffix = uuid.uuid4().hex[:8]
    duplicate_name = f"duplicate_{unique_suffix}"

    # Create first user directly in DB
    create_user(
        db=db,
        username=duplicate_name,
        email=f"first_{unique_suffix}@example.com",
        auth0_user_id=f"auth0|first_{unique_suffix}",
    )

    # Try to create second user with same username via API
    payload = {
        "username": duplicate_name,
        "email": f"second_{unique_suffix}@example.com",
        "auth0_user_id": f"auth0|second_{unique_suffix}",
    }

    response = client.post(
        "/v1/users",
        json=payload,
        headers={"X-Webhook-Secret": mock_webhook_secret},
    )

    assert response.status_code == 409
    detail = response.json()["detail"]
    # Auth0 Action checks for "username" in the error message
    assert "username" in detail.lower()
    # Verify it includes the attempted username for debugging
    assert duplicate_name.lower() in detail.lower()


def test_create_user_duplicate_email(db: Session, mock_webhook_secret):
    """Test that duplicate email returns 409."""
    import uuid

    unique_suffix = uuid.uuid4().hex[:8]
    duplicate_email = f"duplicate_{unique_suffix}@example.com"

    # Create first user directly in DB
    create_user(
        db=db,
        username=f"user1_{unique_suffix}",
        email=duplicate_email,
        auth0_user_id=f"auth0|user1_{unique_suffix}",
    )

    # Try to create second user with same email via API
    payload = {
        "username": f"user2_{unique_suffix}",
        "email": duplicate_email,
        "auth0_user_id": f"auth0|user2_{unique_suffix}",
    }

    response = client.post(
        "/v1/users",
        json=payload,
        headers={"X-Webhook-Secret": mock_webhook_secret},
    )

    assert response.status_code == 409
    assert "email" in response.json()["detail"].lower()


def test_create_user_duplicate_auth0_user_id(db: Session, mock_webhook_secret):
    """Test that duplicate auth0_user_id returns 409."""
    import uuid

    unique_suffix = uuid.uuid4().hex[:8]
    duplicate_auth0 = f"auth0|duplicate_{unique_suffix}"

    # Create first user directly in DB
    create_user(
        db=db,
        username=f"user1_{unique_suffix}",
        email=f"user1_{unique_suffix}@example.com",
        auth0_user_id=duplicate_auth0,
    )

    # Try to create second user with same auth0_user_id via API
    payload = {
        "username": f"user2_{unique_suffix}",
        "email": f"user2_{unique_suffix}@example.com",
        "auth0_user_id": duplicate_auth0,
    }

    response = client.post(
        "/v1/users",
        json=payload,
        headers={"X-Webhook-Secret": mock_webhook_secret},
    )

    assert response.status_code == 409
    assert "auth0" in response.json()["detail"].lower()


def test_create_user_invalid_payload_missing_username(db: Session, mock_webhook_secret):
    """Test that missing username returns 422."""
    payload = {
        "email": "test@example.com",
        "auth0_user_id": "auth0|test123",
    }

    response = client.post(
        "/v1/users",
        json=payload,
        headers={"X-Webhook-Secret": mock_webhook_secret},
    )

    assert response.status_code == 422


def test_create_user_invalid_payload_missing_email(db: Session, mock_webhook_secret):
    """Test that missing email returns 422."""
    payload = {
        "username": "testuser",
        "auth0_user_id": "auth0|test123",
    }

    response = client.post(
        "/v1/users",
        json=payload,
        headers={"X-Webhook-Secret": mock_webhook_secret},
    )

    assert response.status_code == 422


def test_create_user_invalid_payload_missing_auth0_user_id(
    db: Session, mock_webhook_secret
):
    """Test that missing auth0_user_id returns 422."""
    payload = {
        "username": "testuser",
        "email": "test@example.com",
    }

    response = client.post(
        "/v1/users",
        json=payload,
        headers={"X-Webhook-Secret": mock_webhook_secret},
    )

    assert response.status_code == 422


def test_create_user_empty_username(db: Session, mock_webhook_secret):
    """Test that empty username returns 422."""
    payload = {
        "username": "",
        "email": "test@example.com",
        "auth0_user_id": "auth0|test123",
    }

    response = client.post(
        "/v1/users",
        json=payload,
        headers={"X-Webhook-Secret": mock_webhook_secret},
    )

    assert response.status_code == 422


def test_create_user_database_error(db: Session, mock_webhook_secret):
    """Test that database errors are handled gracefully."""
    with patch("api.crud.user.create_user") as mock_create:
        mock_create.side_effect = Exception("Database connection error")

        payload = {
            "username": "testuser",
            "email": "test@example.com",
            "auth0_user_id": "auth0|test123",
        }

        response = client.post(
            "/v1/users",
            json=payload,
            headers={"X-Webhook-Secret": mock_webhook_secret},
        )

        assert response.status_code == 500
        assert "error" in response.json()["detail"].lower()
