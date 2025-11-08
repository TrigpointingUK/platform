"""
Tests for the legacy user migration endpoint.

This endpoint migrates legacy users to Auth0 by:
1. Selecting unique email addresses without Auth0 IDs
2. For each email, choosing the user with most recent tlog
3. Creating Auth0 users with metadata
4. Updating database with Auth0 user IDs
5. Sending verification emails
"""

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from api.core.config import settings
from api.models.user import TLog, User


@pytest.fixture
def test_users_for_migration(db: Session) -> list[User]:
    """Create test users for migration."""
    users = []

    # User 1: email1@example.com, has logs
    user1 = User(
        id=6001,
        name="user1",
        firstname="User",
        surname="One",
        email="email1@example.com",
        cryptpw="test",
        about="",
        email_valid="N",
        public_ind="Y",
        auth0_user_id=None,
    )
    db.add(user1)
    users.append(user1)

    # User 2: email2@example.com, has logs
    user2 = User(
        id=6002,
        name="user2",
        firstname="User",
        surname="Two",
        email="email2@example.com",
        cryptpw="test",
        about="",
        email_valid="N",
        public_ind="Y",
        auth0_user_id=None,
    )
    db.add(user2)
    users.append(user2)

    # User 3: Same email as user1, has more recent logs (should be chosen)
    user3 = User(
        id=6003,
        name="user3",
        firstname="User",
        surname="Three",
        email="email1@example.com",
        cryptpw="test",
        about="",
        email_valid="N",
        public_ind="Y",
        auth0_user_id=None,
    )
    db.add(user3)
    users.append(user3)

    # User 4: Already has Auth0 ID (should be skipped)
    user4 = User(
        id=6004,
        name="user4",
        firstname="User",
        surname="Four",
        email="email3@example.com",
        cryptpw="test",
        about="",
        email_valid="N",
        public_ind="Y",
        auth0_user_id="auth0|existing123",
    )
    db.add(user4)
    users.append(user4)

    # User 5: No email (should be skipped)
    user5 = User(
        id=6005,
        name="user5",
        firstname="User",
        surname="Five",
        email="",
        cryptpw="test",
        about="",
        email_valid="N",
        public_ind="Y",
        auth0_user_id=None,
    )
    db.add(user5)
    users.append(user5)

    db.commit()

    # Add logs for user selection
    # User 1: older log
    log1 = TLog(
        id=7001,
        trig_id=1,
        user_id=6001,
        date=datetime(2023, 1, 1).date(),
        time=datetime(2023, 1, 1).time(),
        fb_number="",
        condition="G",
        comment="Test log 1",
        score=0,
        ip_addr="127.0.0.1",
        source="W",
        upd_timestamp=datetime(2023, 1, 1),
    )
    db.add(log1)

    # User 3: newer log (same email as user1, should be chosen)
    log3 = TLog(
        id=7003,
        trig_id=1,
        user_id=6003,
        date=datetime(2024, 1, 1).date(),
        time=datetime(2024, 1, 1).time(),
        fb_number="",
        condition="G",
        comment="Test log 3",
        score=0,
        ip_addr="127.0.0.1",
        source="W",
        upd_timestamp=datetime(2024, 1, 1),
    )
    db.add(log3)

    # User 2: log
    log2 = TLog(
        id=7002,
        trig_id=1,
        user_id=6002,
        date=datetime(2023, 6, 1).date(),
        time=datetime(2023, 6, 1).time(),
        fb_number="",
        condition="G",
        comment="Test log 2",
        score=0,
        ip_addr="127.0.0.1",
        source="W",
        upd_timestamp=datetime(2023, 6, 1),
    )
    db.add(log2)

    db.commit()
    return users


@pytest.fixture
def admin_user(db: Session) -> User:
    """Create an admin user for testing."""
    admin = User(
        id=9999,
        name="admin",
        email="admin@example.com",
        cryptpw="test",
        auth0_user_id="auth0|9999",
        firstname="Admin",
        surname="User",
        about="",
        email_valid="Y",
        public_ind="Y",
    )
    db.add(admin)
    db.commit()
    db.refresh(admin)
    return admin


@pytest.fixture
def admin_token(monkeypatch):
    """Patch token validator to provide admin scope for user 9999."""

    def _validate_admin(token: str):
        if token == "auth0_user_9999":
            return {
                "token_type": "auth0",
                "auth0_user_id": "auth0|9999",
                "scope": "openid profile api:admin",
            }
        elif token.startswith("auth0_user_"):
            try:
                user_id = int(token.split("_", 2)[2])
                return {"token_type": "auth0", "auth0_user_id": f"auth0|{user_id}"}
            except Exception:
                return None
        return None

    monkeypatch.setattr(
        "api.core.security.auth0_validator.validate_auth0_token", _validate_admin
    )
    return "auth0_user_9999"


class TestMigrateUsersDryRun:
    """Test dry run mode."""

    def test_dry_run_mode(
        self,
        client: TestClient,
        db: Session,
        test_users_for_migration: list[User],
        admin_user: User,
        admin_token: str,
    ):
        """Test dry run mode - should not create Auth0 users or update database."""
        response = client.post(
            f"{settings.API_V1_STR}/legacy/migrate_users",
            json={"limit": 10, "dry_run": True},
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        assert response.status_code == 200
        data = response.json()

        assert data["dry_run"] is True
        assert data["total_unique_emails_found"] == 2  # email1 and email2
        assert data["total_processed"] == 2

        # All actions should be skipped_dry_run
        for action in data["actions"]:
            assert action["action"] == "skipped_dry_run"
            assert action["auth0_user_id"] is None
            assert action["verification_email_sent"] is None

        # Verify no database updates
        user1 = db.query(User).filter(User.id == 6001).first()
        user2 = db.query(User).filter(User.id == 6002).first()
        user3 = db.query(User).filter(User.id == 6003).first()

        assert user1 is not None
        assert user2 is not None
        assert user3 is not None
        assert user1.auth0_user_id is None
        assert user2.auth0_user_id is None
        assert user3.auth0_user_id is None


class TestMigrateUsersRealMigration:
    """Test actual migration."""

    @patch("api.api.v1.endpoints.legacy.auth0_service")
    def test_successful_migration(
        self,
        mock_auth0_service: MagicMock,
        client: TestClient,
        db: Session,
        test_users_for_migration: list[User],
        admin_user: User,
        admin_token: str,
    ):
        """Test successful migration of users to Auth0."""
        # Mock Auth0 service responses
        mock_auth0_service.create_user_for_migration.side_effect = [
            {"user_id": "auth0|migrated1"},  # For user3 (email1@example.com)
            {"user_id": "auth0|migrated2"},  # For user2 (email2@example.com)
        ]
        mock_auth0_service.send_verification_email.return_value = True

        response = client.post(
            f"{settings.API_V1_STR}/legacy/migrate_users",
            json={"limit": 10, "dry_run": False, "send_confirmation_email": True},
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        assert response.status_code == 200
        data = response.json()

        assert data["dry_run"] is False
        assert data["total_unique_emails_found"] == 2
        assert data["total_processed"] == 2

        # Check that both users were created successfully
        created_actions = [a for a in data["actions"] if a["action"] == "created"]
        assert len(created_actions) == 2

        # Verify the right users were chosen
        emails_migrated = {a["email"] for a in created_actions}
        assert emails_migrated == {"email1@example.com", "email2@example.com"}

        # For email1@example.com, user3 should be chosen (more recent log)
        email1_action = [
            a for a in created_actions if a["email"] == "email1@example.com"
        ][0]
        assert email1_action["database_user_id"] == 6003
        assert email1_action["database_username"] == "user3"
        assert email1_action["auth0_user_id"] == "auth0|migrated1"
        assert email1_action["verification_email_sent"] is True

        # For email2@example.com, user2 should be chosen
        email2_action = [
            a for a in created_actions if a["email"] == "email2@example.com"
        ][0]
        assert email2_action["database_user_id"] == 6002
        assert email2_action["database_username"] == "user2"
        assert email2_action["auth0_user_id"] == "auth0|migrated2"
        assert email2_action["verification_email_sent"] is True

        # Verify database updates
        user2 = db.query(User).filter(User.id == 6002).first()
        user3 = db.query(User).filter(User.id == 6003).first()

        assert user2 is not None
        assert user3 is not None
        assert user2.auth0_user_id == "auth0|migrated2"
        assert user3.auth0_user_id == "auth0|migrated1"

        # Verify user1 was not updated (user3 was chosen for same email)
        user1 = db.query(User).filter(User.id == 6001).first()
        assert user1 is not None
        assert user1.auth0_user_id is None

        # Verify Auth0 service calls
        assert mock_auth0_service.create_user_for_migration.call_count == 2
        assert mock_auth0_service.send_verification_email.call_count == 2

        # Check call arguments for user3 (email1@example.com)
        call_args_user3 = mock_auth0_service.create_user_for_migration.call_args_list[0]
        assert call_args_user3.kwargs["email"] == "email1@example.com"
        assert call_args_user3.kwargs["name"] == "user3"
        assert call_args_user3.kwargs["legacy_user_id"] == 6003
        assert call_args_user3.kwargs["original_username"] == "user3"
        assert call_args_user3.kwargs["firstname"] == "User"
        assert call_args_user3.kwargs["surname"] == "Three"


class TestMigrateUsersErrors:
    """Test error handling."""

    @patch("api.api.v1.endpoints.legacy.auth0_service")
    def test_auth0_creation_fails(
        self,
        mock_auth0_service: MagicMock,
        client: TestClient,
        db: Session,
        test_users_for_migration: list[User],
        admin_user: User,
        admin_token: str,
    ):
        """Test handling of Auth0 user creation failure."""
        # Mock Auth0 service to fail
        mock_auth0_service.create_user_for_migration.return_value = None

        response = client.post(
            f"{settings.API_V1_STR}/legacy/migrate_users",
            json={"limit": 10, "dry_run": False},
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        assert response.status_code == 200
        data = response.json()

        # All migrations should fail
        failed_actions = [a for a in data["actions"] if a["action"] == "failed"]
        assert len(failed_actions) == 2

        for action in failed_actions:
            assert action["error"] == "Auth0 user creation failed"
            assert action["auth0_user_id"] == "ERROR"

        # Verify users were marked with ERROR in database
        user2 = db.query(User).filter(User.id == 6002).first()
        user3 = db.query(User).filter(User.id == 6003).first()
        assert user2 is not None
        assert user3 is not None
        assert user2.auth0_user_id == "ERROR"
        assert user3.auth0_user_id == "ERROR"

    @patch("api.api.v1.endpoints.legacy.auth0_service")
    def test_database_update_fails(
        self,
        mock_auth0_service: MagicMock,
        client: TestClient,
        db: Session,
        test_users_for_migration: list[User],
        admin_user: User,
        admin_token: str,
    ):
        """Test handling of database update failure."""
        # Mock Auth0 service to succeed
        mock_auth0_service.create_user_for_migration.return_value = {
            "user_id": "auth0|migrated1"
        }

        # Mock database update to fail
        with patch(
            "api.api.v1.endpoints.legacy.user_crud.update_user_auth0_id"
        ) as mock_update:
            mock_update.return_value = False

            response = client.post(
                f"{settings.API_V1_STR}/legacy/migrate_users",
                json={"limit": 1, "dry_run": False},
                headers={"Authorization": f"Bearer {admin_token}"},
            )

            assert response.status_code == 200
            data = response.json()

            # Should have failed actions due to database update failure
            failed_actions = [a for a in data["actions"] if a["action"] == "failed"]
            assert len(failed_actions) >= 1

            for action in failed_actions:
                assert action["error"] == "Failed to update database with Auth0 user ID"
                assert action["auth0_user_id"] == "auth0|migrated1"


class TestMigrateUsersAuthorization:
    """Test authorization requirements."""

    def test_requires_authentication(
        self,
        client: TestClient,
        db: Session,
        test_users_for_migration: list[User],
    ):
        """Test that endpoint requires authentication."""
        response = client.post(
            f"{settings.API_V1_STR}/legacy/migrate_users",
            json={"limit": 10, "dry_run": True},
        )

        # Should return 401 or 403
        assert response.status_code in [401, 403]

    def test_requires_admin_scope(
        self,
        client: TestClient,
        db: Session,
        test_users_for_migration: list[User],
    ):
        """Test that endpoint requires admin scope."""
        # Create a non-admin user
        regular_user = User(
            id=8888,
            name="regular",
            email="regular@example.com",
            cryptpw="test",
            auth0_user_id="auth0|8888",
            firstname="Regular",
            surname="User",
            about="",
            email_valid="Y",
            public_ind="Y",
        )
        db.add(regular_user)
        db.commit()

        # Use a non-admin token (conftest recognizes auth0_user_{id} pattern)
        response = client.post(
            f"{settings.API_V1_STR}/legacy/migrate_users",
            json={"limit": 10, "dry_run": True},
            headers={"Authorization": "Bearer auth0_user_8888"},
        )

        # Should return 403 (forbidden)
        assert response.status_code == 403


class TestMigrateUsersLimitParameter:
    """Test limit parameter."""

    def test_respects_limit(
        self,
        client: TestClient,
        db: Session,
        test_users_for_migration: list[User],
        admin_user: User,
        admin_token: str,
    ):
        """Test that limit parameter is respected."""
        # Request with limit=1
        response = client.post(
            f"{settings.API_V1_STR}/legacy/migrate_users",
            json={"limit": 1, "dry_run": True},
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        assert response.status_code == 200
        data = response.json()

        # Should only process 1 unique email
        assert data["total_unique_emails_found"] <= 1
        assert data["total_processed"] <= 1
