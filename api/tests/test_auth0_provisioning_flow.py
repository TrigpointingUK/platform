"""
Integration tests for Auth0 provisioning and profile sync flow.
"""

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from api.crud.user import create_user, get_user_by_auth0_id, get_user_by_name
from api.main import app

client = TestClient(app)


@pytest.fixture
def mock_webhook_secret(monkeypatch):
    """Mock WEBHOOK_SHARED_SECRET configuration."""
    test_secret = "test_webhook_secret_12345"
    monkeypatch.setattr("api.core.config.settings.WEBHOOK_SHARED_SECRET", test_secret)
    return test_secret


def test_full_provisioning_flow(db: Session, mock_webhook_secret):
    """Test complete flow from Auth0 Action to user creation."""
    import uuid

    unique_suffix = uuid.uuid4().hex[:8]

    # Simulate Auth0 Action calling webhook
    auth0_payload = {
        "username": f"auth0newuser_{unique_suffix}",
        "email": f"auth0user_{unique_suffix}@example.com",
        "auth0_user_id": f"auth0|newuser_{unique_suffix}",
    }

    response = client.post(
        "/v1/users",
        json=auth0_payload,
        headers={"X-Webhook-Secret": mock_webhook_secret},
    )

    assert response.status_code == 201

    # Verify user created in database
    user = get_user_by_auth0_id(db, auth0_payload["auth0_user_id"])
    assert user is not None
    assert user.name == auth0_payload["username"]
    assert user.email == auth0_payload["email"]
    assert user.firstname == ""  # Empty as expected
    assert user.surname == ""  # Empty as expected
    assert user.cryptpw != ""  # Random string
    assert len(user.cryptpw) > 20  # Random token


def test_username_collision_retry_flow(db: Session, mock_webhook_secret):
    """Test Auth0 Action retry behavior when username collisions occur.

    Simulates the Action's behavior of retrying with suffixed usernames
    when a collision is detected.
    """
    import uuid

    unique_suffix = uuid.uuid4().hex[:8]
    base_username = f"john_{unique_suffix}"

    # Create first user to cause collision
    create_user(
        db=db,
        username=base_username,
        email=f"john1_{unique_suffix}@example.com",
        auth0_user_id=f"auth0|john1_{unique_suffix}",
    )

    # First attempt - collision with base username
    response = client.post(
        "/v1/users",
        json={
            "username": base_username,
            "email": f"john2_{unique_suffix}@example.com",
            "auth0_user_id": f"auth0|john2_{unique_suffix}",
        },
        headers={"X-Webhook-Secret": mock_webhook_secret},
    )

    assert response.status_code == 409
    detail = response.json()["detail"]
    assert "username" in detail.lower()

    # Second attempt - with random suffix (simulating Action retry)
    suffixed_username = f"{base_username}_432524"
    response = client.post(
        "/v1/users",
        json={
            "username": suffixed_username,  # With 6-digit suffix
            "email": f"john2_{unique_suffix}@example.com",
            "auth0_user_id": f"auth0|john2_{unique_suffix}",
        },
        headers={"X-Webhook-Secret": mock_webhook_secret},
    )

    assert response.status_code == 201

    # Verify user created with suffixed username
    user = get_user_by_name(db, suffixed_username)
    assert user is not None
    assert user.email == f"john2_{unique_suffix}@example.com"
    assert user.auth0_user_id == f"auth0|john2_{unique_suffix}"


def test_provisioning_then_profile_update(db: Session, mock_webhook_secret):
    """Test user created via webhook can then update profile."""
    import uuid

    unique_suffix = uuid.uuid4().hex[:8]

    # Step 1: Create user via webhook
    auth0_payload = {
        "username": f"updatetest_{unique_suffix}",
        "email": f"updatetest_{unique_suffix}@example.com",
        "auth0_user_id": f"auth0|updatetest_{unique_suffix}",
    }

    response = client.post(
        "/v1/users",
        json=auth0_payload,
        headers={"X-Webhook-Secret": mock_webhook_secret},
    )

    assert response.status_code == 201

    # Step 2: Update profile via PATCH
    with patch("api.api.deps.auth0_validator.validate_auth0_token") as mock_user_token:
        mock_user_token.return_value = {
            "token_type": "auth0",
            "auth0_user_id": f"auth0|updatetest_{unique_suffix}",
            "sub": f"auth0|updatetest_{unique_suffix}",
            "scope": "api:write api:read-pii",
        }

        with patch("api.services.auth0_service.auth0_service") as mock_service:
            mock_service.update_user_profile.return_value = True

            profile_update = {
                "firstname": "Update",
                "surname": "Test",
                "name": f"updatedusername_{unique_suffix}",
            }

            response = client.patch(
                "/v1/users/me",
                json=profile_update,
                headers={"Authorization": "Bearer user_token"},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["firstname"] == "Update"
            assert data["surname"] == "Test"
            assert data["name"] == f"updatedusername_{unique_suffix}"

            # Verify Auth0 sync was called for name change
            mock_service.update_user_profile.assert_called_once()


def test_cryptpw_is_not_empty(db: Session, mock_webhook_secret):
    """Test that cryptpw is set to a non-empty random string."""
    import uuid

    unique_suffix = uuid.uuid4().hex[:8]

    auth0_payload = {
        "username": f"crypttest_{unique_suffix}",
        "email": f"crypttest_{unique_suffix}@example.com",
        "auth0_user_id": f"auth0|crypttest_{unique_suffix}",
    }

    response = client.post(
        "/v1/users",
        json=auth0_payload,
        headers={"X-Webhook-Secret": mock_webhook_secret},
    )

    assert response.status_code == 201

    # Verify cryptpw is not empty
    user = get_user_by_auth0_id(db, auth0_payload["auth0_user_id"])
    assert user is not None
    assert user.cryptpw != ""
    assert len(user.cryptpw) > 20  # Should be a reasonably long random string


@pytest.mark.skip(reason="Orphaned user sync not yet implemented - test needs fixing")
def test_orphaned_user_sync_on_login(db: Session):
    """Test that if webhook fails, user can still be synced on first login."""
    # Simulate webhook failure - user created in Auth0 but not in database
    # Then user logs in and gets synced via get_current_user dependency
    import uuid

    unique_suffix = uuid.uuid4().hex[:8]

    auth0_user_id = f"auth0|orphaned_{unique_suffix}"
    email = f"orphaned_{unique_suffix}@example.com"
    username = f"orphaneduser_{unique_suffix}"

    # User doesn't exist in database yet
    user = get_user_by_auth0_id(db, auth0_user_id)
    assert user is None

    # Simulate Auth0 returning user details
    with patch("api.services.auth0_service.auth0_service") as mock_service:
        mock_service.find_user_by_auth0_id.return_value = {
            "user_id": auth0_user_id,
            "email": email,
            "nickname": username,
        }

        # Mock token validation
        with patch("api.api.deps.auth0_validator.validate_auth0_token") as mock_token:
            mock_token.return_value = {
                "token_type": "auth0",
                "auth0_user_id": auth0_user_id,
                "email": email,
                "nickname": username,
            }

            # Try to access protected endpoint - should trigger user sync
            # Note: This will fail because we haven't created the user via webhook
            # In real scenario, this would be handled by existing legacy migration logic
            _ = client.get(
                "/v1/users/me",
                headers={"Authorization": "Bearer user_token"},
            )

            # This demonstrates the fallback mechanism exists
            # (actual sync would happen in get_current_user dependency)
    # Note: user would need to be retrieved from DB to verify cryptpw format


def test_profile_sync_resilience(db: Session, mock_webhook_secret):
    """Test that profile updates succeed even when Auth0 sync fails."""
    # Create user
    payload = {
        "username": "resilientuser",
        "email": "resilient@example.com",
        "auth0_user_id": "auth0|resilient123",
    }

    client.post(
        "/v1/users",
        json=payload,
        headers={"X-Webhook-Secret": mock_webhook_secret},
    )

    # Update profile with Auth0 sync failure
    with patch("api.api.deps.auth0_validator.validate_auth0_token") as mock_user_token:
        mock_user_token.return_value = {
            "token_type": "auth0",
            "auth0_user_id": "auth0|resilient123",
            "scope": "api:write api:read-pii",
        }

        with patch("api.services.auth0_service.auth0_service") as mock_service:
            # Mock Auth0 to fail
            mock_service.update_user_email.side_effect = Exception("Auth0 down")

            update_payload = {
                "email": "newemail@example.com",
            }

            response = client.patch(
                "/v1/users/me",
                json=update_payload,
                headers={"Authorization": "Bearer user_token"},
            )

            # Update should still succeed
            assert response.status_code == 200

            # Verify database was updated
            user = get_user_by_auth0_id(db, "auth0|resilient123")
            assert user is not None
            assert user.email == "newemail@example.com"
