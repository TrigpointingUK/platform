"""
Tests for admin scope authorization (api:admin).
"""

from datetime import date, datetime
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from api.crud.user import create_user
from api.main import app
from api.models.tphoto import TPhoto
from api.models.user import TLog

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


@pytest.fixture
def other_user(db: Session):
    """Create another user with unique username."""
    import uuid

    unique_name = f"otheruser_{uuid.uuid4().hex[:8]}"
    user = create_user(
        db=db,
        username=unique_name,
        email=f"{unique_name}@example.com",
        auth0_user_id=f"auth0|{unique_name}",
    )
    return user


@pytest.fixture
def other_users_log(db: Session, other_user):
    """Create a log owned by other_user."""
    log = TLog(
        trig_id=1,
        user_id=other_user.id,
        comment="Test log",
        condition="G",
        date=date.today(),
        time=datetime.now().time(),
        osgb_eastings=1,
        osgb_northings=1,
        osgb_gridref="AA 00000 00000",
        fb_number="",
        score=0,
        ip_addr="127.0.0.1",
        source="W",
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return log


@pytest.fixture
def other_users_photo(db: Session, other_user, other_users_log):
    """Create a photo owned by other_user."""
    photo = TPhoto(
        tlog_id=other_users_log.id,
        server_id=0,
        type="T",
        filename="000/P00001.jpg",
        filesize=100,
        height=100,
        width=100,
        icon_filename="000/I00001.jpg",
        icon_filesize=10,
        icon_height=10,
        icon_width=10,
        name="Test Photo",
        text_desc="Test comment",
        ip_addr="127.0.0.1",
        public_ind="Y",
        deleted_ind="N",
        source="W",
        crt_timestamp=datetime.now(),
    )
    db.add(photo)
    db.commit()
    db.refresh(photo)
    return photo


def test_delete_others_log_without_admin_scope_returns_403(
    db: Session, test_user, other_users_log
):
    """Test that deleting another user's log without api:admin scope returns 403."""
    with patch("api.api.deps.auth0_validator.validate_auth0_token") as mock:
        mock.return_value = {
            "token_type": "auth0",
            "auth0_user_id": test_user.auth0_user_id,
            "sub": test_user.auth0_user_id,
            "scope": "api:write",  # Missing api:admin
        }

        response = client.delete(
            f"/v1/logs/{other_users_log.id}",
            headers={"Authorization": "Bearer mock_token"},
        )

        assert response.status_code == 403
        assert "api:admin" in response.json()["detail"]


def test_update_others_log_without_admin_scope_returns_403(
    db: Session, test_user, other_users_log
):
    """Test that updating another user's log without api:admin scope returns 403."""
    with patch("api.api.deps.auth0_validator.validate_auth0_token") as mock:
        mock.return_value = {
            "token_type": "auth0",
            "auth0_user_id": test_user.auth0_user_id,
            "sub": test_user.auth0_user_id,
            "scope": "api:write",
        }

        response = client.patch(
            f"/v1/logs/{other_users_log.id}",
            json={"comment": "Updated comment"},
            headers={"Authorization": "Bearer mock_token"},
        )

        assert response.status_code == 403
        assert "api:admin" in response.json()["detail"]


def test_delete_others_photo_without_admin_scope_returns_403(
    db: Session, test_user, other_users_photo
):
    """Test that deleting another user's photo without api:admin scope returns 403."""
    with patch("api.api.deps.auth0_validator.validate_auth0_token") as mock:
        mock.return_value = {
            "token_type": "auth0",
            "auth0_user_id": test_user.auth0_user_id,
            "sub": test_user.auth0_user_id,
            "scope": "api:write",
        }

        response = client.delete(
            f"/v1/photos/{other_users_photo.id}",
            headers={"Authorization": "Bearer mock_token"},
        )

        assert response.status_code == 403
        assert "api:admin" in response.json()["detail"]


def test_delete_others_log_with_admin_scope_succeeds(
    db: Session, test_user, other_users_log
):
    """Test that admin users can delete other users' logs."""
    with patch("api.api.deps.auth0_validator.validate_auth0_token") as mock:
        mock.return_value = {
            "token_type": "auth0",
            "auth0_user_id": test_user.auth0_user_id,
            "sub": test_user.auth0_user_id,
            "scope": "api:write api:admin",  # Has admin scope
        }

        response = client.delete(
            f"/v1/logs/{other_users_log.id}",
            headers={"Authorization": "Bearer mock_token"},
        )

        assert response.status_code == 204


def test_update_others_log_with_admin_scope_succeeds(
    db: Session, test_user, other_users_log
):
    """Test that admin users can update other users' logs."""
    with patch("api.api.deps.auth0_validator.validate_auth0_token") as mock:
        mock.return_value = {
            "token_type": "auth0",
            "auth0_user_id": test_user.auth0_user_id,
            "sub": test_user.auth0_user_id,
            "scope": "api:write api:admin",
        }

        response = client.patch(
            f"/v1/logs/{other_users_log.id}",
            json={"comment": "Updated by admin"},
            headers={"Authorization": "Bearer mock_token"},
        )

        assert response.status_code == 200
        assert response.json()["comment"] == "Updated by admin"


# Skipping photo delete with admin test due to S3 mocking complexity
# The admin scope check is already tested for logs, and the pattern is the same
