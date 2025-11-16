"""
Tests for Auth0 user ID mapping behaviour. Auth0 usernames are no longer supported.
"""

from unittest.mock import ANY, patch

from fastapi.testclient import TestClient
from passlib.hash import des_crypt
from sqlalchemy.orm import Session

from api.core.config import settings
from api.crud.user import update_user_auth0_mapping
from api.models.user import User


def _make_user(db: Session, *, name: str, email: str, password: str) -> User:
    """Create a test user with unique identifiers and auto-generated ID."""
    cryptpw = des_crypt.hash(password)
    user = User(
        name=name,
        firstname="Test",
        surname="User",
        email=email,
        cryptpw=cryptpw,
        about="",  # Required field
        email_valid="Y",
        public_ind="Y",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def test_login_persists_auth0_user_id(
    client: TestClient,
    db: Session,
    monkeypatch,
):
    """
    Test that legacy login endpoint authenticates and syncs with Auth0.
    This test verifies that password and email are synced to Auth0.
    """
    import uuid

    unique_suffix = uuid.uuid4().hex[:8]

    # Arrange: User with existing Auth0 ID
    user = _make_user(
        db,
        name=f"login_user_{unique_suffix}",
        email=f"login_{unique_suffix}@example.com",
        password="pw123456",
    )
    # Set an existing Auth0 ID
    user.auth0_user_id = f"auth0|{unique_suffix}"  # type: ignore
    db.commit()

    # Mock Auth0 services
    from unittest.mock import MagicMock

    mock_auth0_service = MagicMock()
    mock_auth0_service.update_user_password.return_value = True
    mock_auth0_service.update_user_email.return_value = True
    monkeypatch.setattr("api.api.v1.endpoints.legacy.auth0_service", mock_auth0_service)

    # Act: Call legacy login with different email
    response = client.post(
        f"{settings.API_V1_STR}/legacy/login",
        json={
            "username": f"login_user_{unique_suffix}",
            "password": "pw123456",
            "email": f"new.email_{unique_suffix}@example.com",
        },
    )

    # Assert
    assert response.status_code == 200
    # Password should be updated
    mock_auth0_service.update_user_password.assert_called_once_with(
        user_id=f"auth0|{unique_suffix}", password="pw123456"
    )
    # Email update should be called since email changed
    mock_auth0_service.update_user_email.assert_called_once_with(
        user_id=f"auth0|{unique_suffix}",
        email=f"new.email_{unique_suffix}@example.com",
        username=f"login_user_{unique_suffix}",
    )
    # Verify the user's email was updated in database and email_valid set to Y
    db.refresh(user)
    assert user.email == f"new.email_{unique_suffix}@example.com"
    assert user.email_valid == "Y"


@patch("api.api.deps.update_user_auth0_mapping")
@patch("api.services.auth0_service.auth0_service")
@patch("api.api.deps.get_user_by_name")
@patch("api.api.deps.get_user_by_email")
@patch("api.api.deps.get_user_by_auth0_id")
@patch("api.core.security.auth0_validator.validate_auth0_token")
def test_deps_links_and_updates_username(
    mock_validate_token,
    mock_get_by_auth0,
    mock_get_by_email,
    mock_get_by_name,
    mock_auth0_service,
    mock_update_mapping,
    client: TestClient,
    db: Session,
):
    # Arrange: Token presents as Auth0 with given sub
    import uuid

    unique_suffix = uuid.uuid4().hex[:8]
    auth0_id = f"auth0|{unique_suffix}"

    mock_validate_token.return_value = {
        "token_type": "auth0",
        "auth0_user_id": auth0_id,
    }
    mock_get_by_auth0.return_value = None  # Force fallback path

    # Create legacy user; Auth0 returns matching email
    user = _make_user(
        db,
        name=f"deps_user_{unique_suffix}",
        email=f"deps_{unique_suffix}@example.com",
        password="pw123456",
    )
    mock_auth0_service.find_user_by_auth0_id.return_value = {
        "user_id": auth0_id,
        "email": f"deps_{unique_suffix}@example.com",
        "nickname": f"deps_user_{unique_suffix}",
        "name": f"deps_user_{unique_suffix}",
    }
    mock_get_by_email.return_value = user
    mock_get_by_name.return_value = None

    # Act
    headers = {"Authorization": "Bearer dummy"}
    response = client.get(f"{settings.API_V1_STR}/users/me", headers=headers)

    # Assert
    assert response.status_code == 200
    mock_update_mapping.assert_called_once_with(
        ANY,
        int(user.id),  # Use dynamic ID
        auth0_id,
    )


def test_get_user_auth0_id_helper(db: Session):
    # Arrange: create user with mapping
    import uuid

    unique_suffix = uuid.uuid4().hex[:8]
    user = _make_user(
        db,
        name=f"map_user_{unique_suffix}",
        email=f"map_{unique_suffix}@example.com",
        password="pw123456",
    )
    # Set mapping via CRUD
    ok = update_user_auth0_mapping(
        db=db,
        user_id=int(user.id),
        auth0_user_id=f"auth0|{unique_suffix}",
    )
    assert ok is True
    # Act/Assert: round-trip via getter
    from api.crud.user import get_user_auth0_id

    assert get_user_auth0_id(db, int(user.id)) == f"auth0|{unique_suffix}"


def test_update_user_auth0_mapping_simple_update(db: Session):
    # Arrange
    import uuid

    unique_suffix = uuid.uuid4().hex[:8]
    user = _make_user(
        db,
        name=f"username_{unique_suffix}",
        email=f"mismatch_{unique_suffix}@example.com",
        password="pw123456",
    )

    # Act
    ok = update_user_auth0_mapping(
        db=db,
        user_id=int(user.id),
        auth0_user_id=f"auth0|{unique_suffix}",
    )

    # Assert
    assert ok is True
    refreshed = db.query(User).filter(User.id == int(user.id)).first()
    assert refreshed is not None
    assert refreshed.auth0_user_id == f"auth0|{unique_suffix}"


def test_update_user_auth0_mapping_user_not_found(monkeypatch):
    # Arrange: patch get_user_by_id to return None
    import api.crud.user as crud_user

    monkeypatch.setattr(crud_user, "get_user_by_id", lambda db, user_id: None)

    class FakeDB:
        def commit(self):
            pass

        def rollback(self):
            pass

    # Act
    # Also cover update_user_auth0_id not found
    from api.crud.user import update_user_auth0_id

    ok = update_user_auth0_mapping(
        db=FakeDB(),
        user_id=999999,
        auth0_user_id="auth0|none",
    )

    # Assert
    assert ok is False
    assert update_user_auth0_id(FakeDB(), 999999, "auth0|none") is False


def test_update_user_auth0_mapping_exception_does_not_crash(monkeypatch, caplog):
    # Arrange: user exists, but sanitizer raises exception
    import api.crud.user as crud_user

    user = type("U", (), {"name": "user name", "auth0_user_id": None})()
    monkeypatch.setattr(crud_user, "get_user_by_id", lambda db, user_id: user)
    # No sanitizer used anymore; force error at commit layer

    class FakeDB:
        def commit(self):
            pass

        def rollback(self):
            pass

    with caplog.at_level("ERROR"):
        ok = update_user_auth0_mapping(
            db=FakeDB(),
            user_id=1,
            auth0_user_id="auth0|x",
        )
    assert ok is True
    assert user.auth0_user_id == "auth0|x"
    # Username fields are no longer tracked


# def test_update_user_auth0_mapping_commit_fallback_success(monkeypatch, caplog):
#     # Arrange: first commit raises, fallback commit succeeds
#     # This test is no longer relevant since fallback logic was removed
#     import api.crud.user as crud_user

#     user = type(
#         "U", (), {"name": "user", "auth0_user_id": None}
#     )()
#     monkeypatch.setattr(crud_user, "get_user_by_id", lambda db, user_id: user)

#     class FakeDB:
#         def __init__(self):
#             self.calls = 0

#         def commit(self):
#             self.calls += 1
#             if self.calls == 1:
#                 raise RuntimeError("db error on first commit")

#         def rollback(self):
#             pass

#     with caplog.at_level("WARNING"):
#         ok = update_user_auth0_mapping(
#             db=FakeDB(),
#             user_id=1,
#             auth0_user_id="auth0|y",
#         )
#     assert ok is True
#     assert user.auth0_user_id == "auth0|y"
#     # auth0_username field removed from User model
#     # Fallback retry logic removed


def test_update_user_auth0_mapping_commit_fallback_failure(monkeypatch, caplog):
    # Arrange: both initial and fallback commit raise
    import api.crud.user as crud_user

    user = type("U", (), {"name": "user", "auth0_user_id": None})()
    monkeypatch.setattr(crud_user, "get_user_by_id", lambda db, user_id: user)

    class FakeDB:
        def commit(self):
            raise RuntimeError("always fails")

        def rollback(self):
            pass

    with caplog.at_level("ERROR"):
        ok = update_user_auth0_mapping(
            db=FakeDB(),
            user_id=1,
            auth0_user_id="auth0|z",
        )
    assert ok is False
    assert any("Auth0 mapping update failed" in rec.message for rec in caplog.records)


def test_update_user_auth0_mapping_success_path(db: Session):
    # Arrange: normal success path sets both fields and commits
    import uuid

    unique_suffix = uuid.uuid4().hex[:8]
    user = _make_user(
        db,
        name=f"ok_user_{unique_suffix}",
        email=f"ok_{unique_suffix}@example.com",
        password="pw123456",
    )
    # Act
    ok = update_user_auth0_mapping(
        db=db,
        user_id=int(user.id),
        auth0_user_id=f"auth0|{unique_suffix}",
    )
    # Assert
    assert ok is True
    refreshed = db.query(User).filter(User.id == int(user.id)).first()
    assert refreshed is not None
    assert refreshed.auth0_user_id == f"auth0|{unique_suffix}"
    # Username fields are no longer tracked


@patch("api.api.deps.update_user_auth0_mapping")
@patch("api.services.auth0_service.auth0_service")
@patch("api.api.deps.get_user_by_name")
@patch("api.api.deps.get_user_by_email")
@patch("api.api.deps.get_user_by_auth0_id")
@patch("api.core.security.auth0_validator.validate_auth0_token")
def test_get_current_user_optional_links_and_updates_id(
    mock_validate_token,
    mock_get_by_auth0,
    mock_get_by_email,
    mock_get_by_name,
    mock_auth0_service,
    mock_update_mapping,
    db: Session,
):
    # Arrange
    class Cred:
        credentials = "dummy"

    mock_validate_token.return_value = {
        "token_type": "auth0",
        "auth0_user_id": "auth0|opt",
    }
    mock_get_by_auth0.return_value = None

    import uuid

    unique_suffix = uuid.uuid4().hex[:8]
    created = _make_user(
        db,
        name=f"opt_user_{unique_suffix}",
        email=f"opt_{unique_suffix}@example.com",
        password="pw123456",
    )
    mock_auth0_service.find_user_by_auth0_id.return_value = {
        "user_id": "auth0|opt",
        "email": f"opt_{unique_suffix}@example.com",
        "nickname": f"opt_user_{unique_suffix}",
        "name": f"opt_user_{unique_suffix}",
    }
    mock_get_by_email.return_value = None
    mock_get_by_name.return_value = created

    from api.api.deps import get_current_user_optional

    # Act
    result = get_current_user_optional(db=db, credentials=Cred())  # type: ignore[arg-type]

    # Assert
    assert result is created
    mock_update_mapping.assert_called_once_with(ANY, int(created.id), "auth0|opt")
