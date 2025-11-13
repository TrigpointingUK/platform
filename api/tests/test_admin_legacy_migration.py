"""
Tests for admin-driven legacy user migration endpoints.
"""

from typing import Dict
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from passlib.hash import des_crypt
from sqlalchemy.orm import Session

import api.api.v1.endpoints.admin as admin_endpoints
from api.models.user import User
from api.services.auth0_service import Auth0EmailAlreadyExistsError


def _create_user(
    db: Session,
    *,
    username: str,
    email: str,
    email_valid: str = "N",
    auth0_user_id: str | None = None,
) -> User:
    """Create and persist a legacy user for testing."""
    user = User(
        name=username,
        firstname="Test",
        surname="User",
        email=email,
        email_valid=email_valid,
        cryptpw=des_crypt.hash("password123"),
        public_ind="N",
        homepage="",
        about="",
    )
    if auth0_user_id:
        user.auth0_user_id = auth0_user_id  # type: ignore
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _admin_headers(admin_user: User) -> Dict[str, str]:
    """Return headers for an admin-scoped request."""
    return {"Authorization": f"Bearer admin-token-{admin_user.id}"}


@pytest.fixture
def admin_user(db: Session) -> User:
    """Create an admin legacy user record."""
    admin = _create_user(
        db,
        username="adminuser",
        email="admin@example.com",
        email_valid="Y",
    )
    admin.auth0_user_id = f"auth0|{admin.id}"  # type: ignore
    db.commit()
    db.refresh(admin)
    return admin


@pytest.fixture
def admin_auth_patch(admin_user: User):
    """Patch Auth0 token validation to impersonate an admin-scoped user."""
    payload = {
        "token_type": "auth0",
        "auth0_user_id": f"auth0|{admin_user.id}",
        "sub": f"auth0|{admin_user.id}",
        "scope": "openid profile api:write api:admin",
    }
    with patch("api.api.deps.auth0_validator.validate_auth0_token") as mock:
        mock.return_value = payload
        yield mock


def test_search_returns_matching_users(
    db: Session, client: TestClient, admin_user: User, admin_auth_patch
):
    """Ensure legacy search endpoint returns matching usernames or emails."""
    _create_user(db, username="alice", email="alice@example.com")
    _create_user(db, username="bob", email="bob@example.net")

    response = client.get(
        "/v1/admin/legacy-migration/users?q=ali",
        headers=_admin_headers(admin_user),
    )

    assert response.status_code == 200
    body = response.json()
    assert len(body["items"]) == 1
    assert body["items"][0]["name"] == "alice"
    assert body["items"][0]["has_auth0_account"] is False


def test_search_requires_two_characters(
    client: TestClient, admin_user: User, admin_auth_patch
):
    """Search endpoint should reject short queries."""
    response = client.get(
        "/v1/admin/legacy-migration/users?q=a ",
        headers=_admin_headers(admin_user),
    )
    assert response.status_code == 400
    assert "at least two" in response.json()["detail"]


def test_migrate_user_success(
    db: Session, client: TestClient, admin_user: User, admin_auth_patch
):
    """Successful migration should update Auth0 mapping and email."""
    target_user = _create_user(db, username="charlie", email="old@example.com")

    with patch.object(
        admin_endpoints.auth0_service,
        "create_user_for_admin_migration",
        return_value={"user_id": "auth0|charlie123"},
    ) as mock_create:
        response = client.post(
            "/v1/admin/legacy-migration/migrate",
            json={"user_id": target_user.id, "email": "new@example.com"},
            headers=_admin_headers(admin_user),
        )

    assert response.status_code == 200
    body = response.json()
    assert body["auth0_user_id"] == "auth0|charlie123"
    assert "Hi charlie!" in body["message"]
    assert '"new@example.com"' in body["message"]

    db.refresh(target_user)
    assert target_user.auth0_user_id == "auth0|charlie123"
    assert target_user.email == "new@example.com"
    assert target_user.email_valid == "Y"
    mock_create.assert_called_once()


def test_migrate_user_prevent_when_already_migrated(
    db: Session, client: TestClient, admin_user: User, admin_auth_patch
):
    """Migration should fail if the user already has an Auth0 identifier."""
    migrated_user = _create_user(
        db,
        username="dan",
        email="dan@example.com",
        auth0_user_id="auth0|existing",
        email_valid="Y",
    )

    response = client.post(
        "/v1/admin/legacy-migration/migrate",
        json={"user_id": migrated_user.id, "email": "dan@example.com"},
        headers=_admin_headers(admin_user),
    )

    assert response.status_code == 400
    assert "already has an Auth0 account" in response.json()["detail"]


def test_migrate_user_email_conflict_in_database(
    db: Session, client: TestClient, admin_user: User, admin_auth_patch
):
    """Migration should fail if another user already owns the email."""
    other_user = _create_user(db, username="eva", email="shared@example.com")
    target_user = _create_user(db, username="frank", email="frank@example.com")

    response = client.post(
        "/v1/admin/legacy-migration/migrate",
        json={"user_id": target_user.id, "email": other_user.email},
        headers=_admin_headers(admin_user),
    )

    assert response.status_code == 400
    assert "already in use by another user" in response.json()["detail"]


def test_migrate_user_email_conflict_in_auth0(
    db: Session, client: TestClient, admin_user: User, admin_auth_patch
):
    """Migration should fail when Auth0 reports an existing user with the email."""
    target_user = _create_user(db, username="gail", email="gail@example.com")

    with patch.object(
        admin_endpoints.auth0_service,
        "create_user_for_admin_migration",
        side_effect=Auth0EmailAlreadyExistsError("gail@example.com"),
    ):
        response = client.post(
            "/v1/admin/legacy-migration/migrate",
            json={"user_id": target_user.id, "email": "gail@example.com"},
            headers=_admin_headers(admin_user),
        )

    assert response.status_code == 400
    assert "already registered in Auth0" in response.json()["detail"]


def test_migrate_user_missing_auth0_id(
    db: Session, client: TestClient, admin_user: User, admin_auth_patch
):
    """Migration should fail if Auth0 response lacks a user identifier."""
    target_user = _create_user(db, username="hugh", email="hugh@example.com")

    with patch.object(
        admin_endpoints.auth0_service,
        "create_user_for_admin_migration",
        return_value={},
    ):
        response = client.post(
            "/v1/admin/legacy-migration/migrate",
            json={"user_id": target_user.id, "email": "hugh@example.com"},
            headers=_admin_headers(admin_user),
        )

    assert response.status_code == 502
    assert "did not return a user identifier" in response.json()["detail"]


def test_migrate_user_database_failure_returns_500(
    db: Session,
    client: TestClient,
    admin_user: User,
    admin_auth_patch,
    monkeypatch,
):
    """Migration should return 500 if the database commit fails."""
    target_user = _create_user(db, username="ivan", email="ivan@example.com")

    def failing_commit(self):
        raise RuntimeError("db commit failed")

    monkeypatch.setattr(Session, "commit", failing_commit, raising=False)

    with patch.object(
        admin_endpoints.auth0_service,
        "create_user_for_admin_migration",
        return_value={"user_id": "auth0|ivan123"},
    ), patch.object(
        admin_endpoints.auth0_service,
        "delete_user",
        return_value=True,
    ) as mock_delete:
        response = client.post(
            "/v1/admin/legacy-migration/migrate",
            json={"user_id": target_user.id, "email": "ivan-new@example.com"},
            headers=_admin_headers(admin_user),
        )

    assert response.status_code == 500
    assert "Failed to persist Auth0 migration details" in response.json()["detail"]
    mock_delete.assert_called_once_with("auth0|ivan123")

    db.refresh(target_user)
    assert target_user.auth0_user_id is None
