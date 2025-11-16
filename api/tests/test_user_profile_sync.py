"""
Tests for PATCH /v1/users/me with Auth0 sync logic.
"""

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from api.crud.user import create_user
from api.main import app

client = TestClient(app)


@pytest.fixture
def test_user_with_auth0(db: Session):
    """Create a test user with Auth0 ID and unique username."""
    import uuid

    unique_name = f"testuser_{uuid.uuid4().hex[:8]}"
    user = create_user(
        db=db,
        username=unique_name,
        email=f"{unique_name}@example.com",
        auth0_user_id=f"auth0|{unique_name}",
    )
    return user


@pytest.fixture
def mock_auth0_token(test_user_with_auth0):
    """Mock Auth0 token validation to return test user."""
    with patch("api.api.deps.auth0_validator.validate_auth0_token") as mock:
        mock.return_value = {
            "token_type": "auth0",
            "auth0_user_id": test_user_with_auth0.auth0_user_id,
            "sub": test_user_with_auth0.auth0_user_id,
            "scope": "api:write api:read-pii",
        }
        yield mock


def test_update_firstname_surname_no_sync(
    db: Session, test_user_with_auth0, mock_auth0_token
):
    """Test updating firstname/surname (database only, no Auth0 sync)."""
    with patch("api.services.auth0_service.auth0_service") as mock_service:
        payload = {
            "firstname": "John",
            "surname": "Doe",
        }

        response = client.patch(
            "/v1/users/me",
            json=payload,
            headers={"Authorization": "Bearer mock_token"},
        )

        assert response.status_code == 200
        # Auth0 service should not be called for firstname/surname
        mock_service.update_user_profile.assert_not_called()
        mock_service.update_user_email.assert_not_called()


def test_update_name_syncs_to_auth0(
    db: Session, test_user_with_auth0, mock_auth0_token
):
    """Test updating name/nickname syncs to Auth0."""
    import uuid

    new_username = f"newusername_{uuid.uuid4().hex[:8]}"

    with patch("api.services.auth0_service.auth0_service") as mock_service:
        mock_service.update_user_profile.return_value = True

        payload = {
            "name": new_username,
        }

        response = client.patch(
            "/v1/users/me",
            json=payload,
            headers={"Authorization": "Bearer mock_token"},
        )

        assert response.status_code == 200
        # Auth0 service should be called to sync nickname
        mock_service.update_user_profile.assert_called_once_with(
            user_id=test_user_with_auth0.auth0_user_id,
            nickname=new_username,
        )


def test_update_email_syncs_to_auth0(
    db: Session, test_user_with_auth0, mock_auth0_token
):
    """Test updating email syncs to Auth0."""
    import uuid

    new_email = f"newemail_{uuid.uuid4().hex[:8]}@example.com"

    with patch("api.services.auth0_service.auth0_service") as mock_service:
        mock_service.update_user_email.return_value = True

        payload = {
            "email": new_email,
        }

        response = client.patch(
            "/v1/users/me",
            json=payload,
            headers={"Authorization": "Bearer mock_token"},
        )

        assert response.status_code == 200
        # Auth0 service should be called to sync email
        mock_service.update_user_email.assert_called_once_with(
            user_id=test_user_with_auth0.auth0_user_id,
            email=new_email,
        )


def test_update_name_duplicate_validation(
    db: Session, test_user_with_auth0, mock_auth0_token
):
    """Test that duplicate name is rejected."""
    import uuid

    unique_suffix = uuid.uuid4().hex[:8]
    existing_username = f"existinguser_{unique_suffix}"

    # Create another user with different name
    create_user(
        db=db,
        username=existing_username,
        email=f"existing_{unique_suffix}@example.com",
        auth0_user_id=f"auth0|existing_{unique_suffix}",
    )

    payload = {
        "name": existing_username,  # Try to change to existing username
    }

    response = client.patch(
        "/v1/users/me",
        json=payload,
        headers={"Authorization": "Bearer mock_token"},
    )

    assert response.status_code == 409
    assert (
        "username" in response.json()["detail"].lower()
        or "taken" in response.json()["detail"].lower()
    )


def test_update_email_duplicate_validation(
    db: Session, test_user_with_auth0, mock_auth0_token
):
    """Test that duplicate email is rejected."""
    import uuid

    unique_suffix = uuid.uuid4().hex[:8]
    existing_email = f"existing_{unique_suffix}@example.com"

    # Create another user with different email
    create_user(
        db=db,
        username=f"anotheruser_{unique_suffix}",
        email=existing_email,
        auth0_user_id=f"auth0|another_{unique_suffix}",
    )

    payload = {
        "email": existing_email,  # Try to change to existing email
    }

    response = client.patch(
        "/v1/users/me",
        json=payload,
        headers={"Authorization": "Bearer mock_token"},
    )

    assert response.status_code == 409
    assert "email" in response.json()["detail"].lower()


def test_auth0_sync_failure_doesnt_fail_update(
    db: Session, test_user_with_auth0, mock_auth0_token
):
    """Test that Auth0 sync failure doesn't fail the database update."""
    import uuid

    new_nickname = f"newnickname_{uuid.uuid4().hex[:8]}"

    with patch("api.services.auth0_service.auth0_service") as mock_service:
        # Mock Auth0 sync to fail
        mock_service.update_user_profile.return_value = False

        payload = {
            "name": new_nickname,
        }

        response = client.patch(
            "/v1/users/me",
            json=payload,
            headers={"Authorization": "Bearer mock_token"},
        )

        # Request should still succeed
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == new_nickname


def test_combined_updates_work(db: Session, test_user_with_auth0, mock_auth0_token):
    """Test that multiple fields can be updated at once."""
    import uuid

    unique_suffix = uuid.uuid4().hex[:8]

    with patch("api.services.auth0_service.auth0_service") as mock_service:
        mock_service.update_user_profile.return_value = True
        mock_service.update_user_email.return_value = True

        payload = {
            "name": f"updatedname_{unique_suffix}",
            "email": f"updated_{unique_suffix}@example.com",
            "firstname": "Updated",
            "surname": "User",
            "homepage": "https://example.com",
        }

        response = client.patch(
            "/v1/users/me",
            json=payload,
            headers={"Authorization": "Bearer mock_token"},
        )

        assert response.status_code == 200
        # Both Auth0 syncs should be called
        mock_service.update_user_profile.assert_called_once()
        mock_service.update_user_email.assert_called_once()


def test_update_no_auth0_id_skips_sync(db: Session, mock_auth0_token):
    """Test that users without auth0_user_id skip Auth0 sync."""
    # Create user without auth0_user_id
    import secrets
    import uuid
    from datetime import date, datetime, time

    from api.models.user import User

    unique_suffix = uuid.uuid4().hex[:8]
    user = User(
        name=f"legacyuser_{unique_suffix}",
        email=f"legacy_{unique_suffix}@example.com",
        auth0_user_id=None,
        cryptpw=secrets.token_urlsafe(32),
        firstname="",
        surname="",
        email_valid="Y",
        email_ind="N",
        public_ind="N",
        homepage="",
        distance_ind="K",
        about="",
        status_max=0,
        crt_date=date.today(),
        crt_time=time(),
        upd_timestamp=datetime.now(),
        online_map_type="",
        online_map_type2="lla",
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    # Mock token to return this user
    with patch("api.api.deps.auth0_validator.validate_auth0_token") as mock_token_val:
        mock_token_val.return_value = {
            "token_type": "auth0",
            "auth0_user_id": None,
            "sub": "legacy_sub",
        }

        with patch("api.api.deps.get_user_by_auth0_id") as mock_get_user:
            mock_get_user.return_value = user

            with patch("api.services.auth0_service.auth0_service") as mock_service:
                import uuid

                new_name = f"newname_{uuid.uuid4().hex[:8]}"

                payload = {
                    "name": new_name,
                }

                _ = client.patch(
                    "/v1/users/me",
                    json=payload,
                    headers={"Authorization": "Bearer mock_token"},
                )

                # Auth0 sync should not be called
                mock_service.update_user_profile.assert_not_called()


def test_auth0_sync_exception_doesnt_fail_update(
    db: Session, test_user_with_auth0, mock_auth0_token
):
    """Test that Auth0 sync exception doesn't fail the database update."""
    import uuid

    new_email = f"newemail_{uuid.uuid4().hex[:8]}@example.com"

    with patch("api.services.auth0_service.auth0_service") as mock_service:
        # Mock Auth0 sync to raise exception
        mock_service.update_user_email.side_effect = Exception("Auth0 API error")

        payload = {
            "email": new_email,
        }

        response = client.patch(
            "/v1/users/me",
            json=payload,
            headers={"Authorization": "Bearer mock_token"},
        )

        # Request should still succeed even when Auth0 sync fails
        assert response.status_code == 200

        # Verify database was updated despite Auth0 sync failure
        # Refresh the session to see committed changes from the endpoint
        db.expire_all()
        from api.crud.user import get_user_by_auth0_id

        user = get_user_by_auth0_id(db, test_user_with_auth0.auth0_user_id)
        assert user is not None
        assert user.email == new_email
