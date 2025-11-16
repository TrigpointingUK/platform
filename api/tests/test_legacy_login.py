"""
Comprehensive tests for the legacy login endpoint (authenticates and syncs with Auth0).

This endpoint authenticates users against the legacy database and synchronises
their credentials and email with Auth0.
"""

import crypt
import uuid
from datetime import date, time
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from api.core.config import settings
from api.models.trig import Trig
from api.models.user import TLog, User


@pytest.fixture
def test_user(db: Session) -> User:
    """Create a test user with known credentials."""
    test_password = "testpass123"
    cryptpw = crypt.crypt(test_password, "$1$testsalt$")
    suffix = uuid.uuid4().hex[:6]
    username = f"legacy_test_user_{suffix}"
    email = f"{username}@example.com"

    user = User(
        name=username,
        firstname="Legacy",
        surname="Test",
        email=email,
        cryptpw=cryptpw,
        about="Test user for legacy login",
        email_valid="N",
        public_ind="Y",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    user.auth0_user_id = f"auth0|{user.id}"  # type: ignore
    db.commit()
    db.refresh(user)
    user.plaintext_password = test_password  # type: ignore
    user.original_email = email  # type: ignore
    return user


@pytest.fixture
def test_user_no_auth0(db: Session) -> User:
    """Create a test user without Auth0 ID."""
    test_password = "testpass456"
    cryptpw = crypt.crypt(test_password, "$1$testsalt$")
    suffix = uuid.uuid4().hex[:6]
    username = f"legacy_no_auth0_{suffix}"
    email = f"{username}@example.com"

    user = User(
        name=username,
        firstname="No",
        surname="Auth0",
        email=email,
        cryptpw=cryptpw,
        about="Test user without Auth0",
        email_valid="N",
        public_ind="Y",
        auth0_user_id=None,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    user.plaintext_password = test_password
    user.original_email = email
    return user


class TestLegacyLoginAuthentication:
    """Test authentication functionality."""

    @patch("api.api.v1.endpoints.legacy.auth0_service")
    def test_login_success_with_auth0_user(
        self,
        mock_auth0_service: MagicMock,
        client: TestClient,
        db: Session,
        test_user: User,
    ):
        """Test successful login for user with Auth0 account."""
        mock_auth0_service.update_user_password.return_value = True
        mock_auth0_service.update_user_email.return_value = True
        new_email = f"{uuid.uuid4().hex}@example.com"

        response = client.post(
            f"{settings.API_V1_STR}/legacy/login",
            json={
                "username": test_user.name,
                "password": test_user.plaintext_password,
                "email": new_email,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_user.id
        assert data["name"] == test_user.name
        assert data["email"] == new_email
        assert data["email_valid"] == "Y"

        # Verify Auth0 calls
        mock_auth0_service.update_user_password.assert_called_once_with(
            user_id=test_user.auth0_user_id, password=test_user.plaintext_password
        )
        mock_auth0_service.update_user_email.assert_called_once_with(
            user_id=test_user.auth0_user_id,
            email=new_email,
            username=test_user.name,
        )

    @patch("api.api.v1.endpoints.legacy.auth0_service")
    def test_login_success_without_auth0_user(
        self,
        mock_auth0_service: MagicMock,
        client: TestClient,
        db: Session,
        test_user_no_auth0: User,
    ):
        """Test successful login for user without Auth0 account - creates one."""
        new_email = f"{uuid.uuid4().hex}@example.com"
        mock_auth0_service.create_user.return_value = {
            "user_id": "auth0|newuser123",
            "email": new_email,
        }

        response = client.post(
            f"{settings.API_V1_STR}/legacy/login",
            json={
                "username": test_user_no_auth0.name,
                "password": test_user_no_auth0.plaintext_password,
                "email": new_email,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_user_no_auth0.id
        assert data["name"] == test_user_no_auth0.name
        assert data["email"] == new_email

        # Verify Auth0 create_user was called
        mock_auth0_service.create_user.assert_called_once_with(
            username=test_user_no_auth0.name,
            email=new_email,
            password=test_user_no_auth0.plaintext_password,
            name=test_user_no_auth0.name,
            user_id=test_user_no_auth0.id,
            firstname=test_user_no_auth0.firstname,
            surname=test_user_no_auth0.surname,
        )

        # Verify user now has Auth0 ID in database
        db.refresh(test_user_no_auth0)
        assert test_user_no_auth0.auth0_user_id == "auth0|newuser123"

    def test_login_wrong_username(self, client: TestClient, db: Session):
        """Test login with non-existent username."""
        response = client.post(
            f"{settings.API_V1_STR}/legacy/login",
            json={
                "username": "nonexistent",
                "password": "anypassword",
                "email": "test@example.com",
            },
        )

        assert response.status_code == 401
        assert "Incorrect username or password" in response.json()["detail"]

    def test_login_wrong_password(
        self, client: TestClient, db: Session, test_user: User
    ):
        """Test login with wrong password."""
        response = client.post(
            f"{settings.API_V1_STR}/legacy/login",
            json={
                "username": test_user.name,
                "password": "wrongpassword",
                "email": "test@example.com",
            },
        )

        assert response.status_code == 401
        assert "Incorrect username or password" in response.json()["detail"]

    def test_login_missing_username(self, client: TestClient):
        """Test login with missing username."""
        response = client.post(
            f"{settings.API_V1_STR}/legacy/login",
            json={"password": "testpass", "email": "test@example.com"},
        )

        assert response.status_code == 422

    def test_login_missing_password(self, client: TestClient):
        """Test login with missing password."""
        response = client.post(
            f"{settings.API_V1_STR}/legacy/login",
            json={"username": "testuser", "email": "test@example.com"},
        )

        assert response.status_code == 422

    @patch("api.api.v1.endpoints.legacy.auth0_service")
    def test_login_without_email_with_auth0_user(
        self,
        mock_auth0_service: MagicMock,
        client: TestClient,
        db: Session,
        test_user: User,
    ):
        """Test login without email returns user data without Auth0 sync."""
        # Auth0 service should not be called when email is not provided
        response = client.post(
            f"{settings.API_V1_STR}/legacy/login",
            json={
                "username": test_user.name,
                "password": test_user.plaintext_password,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_user.id
        assert data["name"] == test_user.name
        # Email should remain unchanged in database
        assert data["email"] == test_user.original_email

        # Verify Auth0 was not called at all
        mock_auth0_service.update_user_password.assert_not_called()
        mock_auth0_service.update_user_email.assert_not_called()
        mock_auth0_service.create_user.assert_not_called()

    def test_login_without_email_no_auth0_user(
        self,
        client: TestClient,
        db: Session,
        test_user_no_auth0: User,
    ):
        """Test login without email returns user data without Auth0 sync."""
        response = client.post(
            f"{settings.API_V1_STR}/legacy/login",
            json={
                "username": test_user_no_auth0.name,
                "password": test_user_no_auth0.plaintext_password,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_user_no_auth0.id
        assert data["name"] == test_user_no_auth0.name
        # Email should remain unchanged
        assert data["email"] == test_user_no_auth0.original_email

        # Verify user still doesn't have Auth0 ID (no sync without email)
        db.refresh(test_user_no_auth0)
        assert test_user_no_auth0.auth0_user_id is None


class TestLegacyLoginAuth0Sync:
    """Test Auth0 synchronisation functionality."""

    @patch("api.api.v1.endpoints.legacy.auth0_service")
    def test_email_not_changed_skips_auth0_email_update(
        self,
        mock_auth0_service: MagicMock,
        client: TestClient,
        db: Session,
        test_user: User,
    ):
        """Test that unchanged email skips Auth0 email update."""
        mock_auth0_service.update_user_password.return_value = True

        response = client.post(
            f"{settings.API_V1_STR}/legacy/login",
            json={
                "username": test_user.name,
                "password": test_user.plaintext_password,
                "email": test_user.original_email,  # Same as user's current email
            },
        )

        assert response.status_code == 200

        # Password should be updated
        mock_auth0_service.update_user_password.assert_called_once()
        # Email update should NOT be called
        mock_auth0_service.update_user_email.assert_not_called()

    @patch("api.api.v1.endpoints.legacy.auth0_service")
    def test_email_changed_triggers_auth0_email_update(
        self,
        mock_auth0_service: MagicMock,
        client: TestClient,
        db: Session,
        test_user: User,
    ):
        """Test that changed email triggers Auth0 email update."""
        mock_auth0_service.update_user_password.return_value = True
        mock_auth0_service.update_user_email.return_value = True
        new_email = f"{uuid.uuid4().hex}@example.com"

        response = client.post(
            f"{settings.API_V1_STR}/legacy/login",
            json={
                "username": test_user.name,
                "password": test_user.plaintext_password,
                "email": new_email,
            },
        )

        assert response.status_code == 200

        # Both password and email should be updated
        mock_auth0_service.update_user_password.assert_called_once()
        mock_auth0_service.update_user_email.assert_called_once_with(
            user_id=test_user.auth0_user_id,
            email=new_email,
            username=test_user.name,
        )

    @patch("api.api.v1.endpoints.legacy.auth0_service")
    def test_auth0_password_update_failure(
        self,
        mock_auth0_service: MagicMock,
        client: TestClient,
        db: Session,
        test_user: User,
    ):
        """Test that Auth0 password update failure returns 500."""
        mock_auth0_service.update_user_password.return_value = False
        sync_email = f"{uuid.uuid4().hex}@example.com"

        response = client.post(
            f"{settings.API_V1_STR}/legacy/login",
            json={
                "username": test_user.name,
                "password": test_user.plaintext_password,
                "email": sync_email,
            },
        )

        assert response.status_code == 500
        assert "Failed to update Auth0 password" in response.json()["detail"]

    @patch("api.api.v1.endpoints.legacy.auth0_service")
    def test_auth0_email_update_failure(
        self,
        mock_auth0_service: MagicMock,
        client: TestClient,
        db: Session,
        test_user: User,
    ):
        """Test that Auth0 email update failure returns 500."""
        mock_auth0_service.update_user_password.return_value = True
        mock_auth0_service.update_user_email.return_value = False

        new_email = f"{uuid.uuid4().hex}@example.com"

        response = client.post(
            f"{settings.API_V1_STR}/legacy/login",
            json={
                "username": test_user.name,
                "password": test_user.plaintext_password,
                "email": new_email,
            },
        )

        assert response.status_code == 500
        assert "Failed to update Auth0 email" in response.json()["detail"]

    @patch("api.api.v1.endpoints.legacy.auth0_service")
    def test_auth0_create_user_failure(
        self,
        mock_auth0_service: MagicMock,
        client: TestClient,
        db: Session,
        test_user_no_auth0: User,
    ):
        """Test that Auth0 create user failure returns 500."""
        mock_auth0_service.create_user.return_value = None
        failure_email = f"{uuid.uuid4().hex}@example.com"

        response = client.post(
            f"{settings.API_V1_STR}/legacy/login",
            json={
                "username": test_user_no_auth0.name,
                "password": test_user_no_auth0.plaintext_password,
                "email": failure_email,
            },
        )

        assert response.status_code == 500
        assert "Failed to create Auth0 user" in response.json()["detail"]

    @patch("api.api.v1.endpoints.legacy.auth0_service")
    def test_auth0_create_user_no_user_id(
        self,
        mock_auth0_service: MagicMock,
        client: TestClient,
        db: Session,
        test_user_no_auth0: User,
    ):
        """Test that Auth0 create user with no user_id returns 500."""
        mock_auth0_service.create_user.return_value = {"email": "test@example.com"}
        failure_email = f"{uuid.uuid4().hex}@example.com"

        response = client.post(
            f"{settings.API_V1_STR}/legacy/login",
            json={
                "username": test_user_no_auth0.name,
                "password": test_user_no_auth0.plaintext_password,
                "email": failure_email,
            },
        )

        assert response.status_code == 500
        assert "Failed to create Auth0 user" in response.json()["detail"]


class TestLegacyLoginIncludes:
    """Test include functionality for stats, breakdown, and prefs."""

    @patch("api.api.v1.endpoints.legacy.auth0_service")
    def test_login_without_includes(
        self,
        mock_auth0_service: MagicMock,
        client: TestClient,
        db: Session,
        test_user: User,
    ):
        """Test login without includes returns basic data only."""
        mock_auth0_service.update_user_password.return_value = True

        response = client.post(
            f"{settings.API_V1_STR}/legacy/login",
            json={
                "username": test_user.name,
                "password": test_user.plaintext_password,
                "email": test_user.original_email,
            },
        )

        assert response.status_code == 200
        data = response.json()

        # Basic fields should be present
        assert "id" in data
        assert "name" in data
        assert "email" in data

        # Include fields should be absent
        assert "stats" not in data
        assert "breakdown" not in data
        assert "prefs" not in data

    @patch("api.api.v1.endpoints.legacy.auth0_service")
    def test_login_with_stats_include(
        self,
        mock_auth0_service: MagicMock,
        client: TestClient,
        db: Session,
        test_user: User,
    ):
        """Test login with stats include."""
        mock_auth0_service.update_user_password.return_value = True

        # Create a log for the user
        log = TLog(
            trig_id=1,
            user_id=test_user.id,
            date=date(2023, 1, 1),
            time=time(12, 0),
            osgb_eastings=400000,
            osgb_northings=500000,
            osgb_gridref="SK 00000 00000",
            fb_number="S1234",
            condition="G",
            comment="Test log",
            score=5,
            ip_addr="127.0.0.1",
            source="W",
        )
        db.add(log)
        db.commit()

        response = client.post(
            f"{settings.API_V1_STR}/legacy/login",
            json={
                "username": test_user.name,
                "password": test_user.plaintext_password,
                "email": test_user.original_email,
                "include": "stats",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "stats" in data
        assert data["stats"]["total_logs"] == 1
        assert data["stats"]["total_trigs_logged"] == 1

    @patch("api.api.v1.endpoints.legacy.auth0_service")
    def test_login_with_breakdown_include(
        self,
        mock_auth0_service: MagicMock,
        client: TestClient,
        db: Session,
        test_user: User,
    ):
        """Test login with breakdown include."""
        mock_auth0_service.update_user_password.return_value = True

        # Create trig and log
        trig = Trig(
            name="Test Trig",
            waypoint=f"TP{uuid.uuid4().hex[:6]}"[:8],
            fb_number="S1234",
            stn_number="0001",
            status_id=0,
            user_added=0,
            current_use="Unknown",
            historic_use="Triangulation Station",
            physical_type="Pillar",
            condition="G",
            wgs_lat=51.5,
            wgs_long=-0.1,
            wgs_height=100,
            osgb_eastings=400000,
            osgb_northings=500000,
            osgb_gridref="SK 00000 00000",
            osgb_height=100,
            postcode="SW1A 1",
            county="Test County",
            town="Test Town",
            permission_ind="Y",
            needs_attention=0,
            attention_comment="",
            crt_date=date(2023, 1, 1),
            crt_time=time(12, 0),
            crt_user_id=test_user.id,
            crt_ip_addr="127.0.0.1",
        )
        db.add(trig)

        db.commit()
        db.refresh(trig)

        log = TLog(
            trig_id=trig.id,
            user_id=test_user.id,
            date=date(2023, 1, 1),
            time=time(12, 0),
            osgb_eastings=400000,
            osgb_northings=500000,
            osgb_gridref="SK 00000 00000",
            fb_number="S1234",
            condition="G",
            comment="Test log",
            score=5,
            ip_addr="127.0.0.1",
            source="W",
        )
        db.add(log)
        db.commit()

        response = client.post(
            f"{settings.API_V1_STR}/legacy/login",
            json={
                "username": test_user.name,
                "password": test_user.plaintext_password,
                "email": test_user.original_email,
                "include": "breakdown",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "breakdown" in data
        assert "by_current_use" in data["breakdown"]
        assert "by_historic_use" in data["breakdown"]
        assert "by_physical_type" in data["breakdown"]
        assert "by_condition" in data["breakdown"]

    @patch("api.api.v1.endpoints.legacy.auth0_service")
    def test_login_with_prefs_include(
        self,
        mock_auth0_service: MagicMock,
        client: TestClient,
        db: Session,
        test_user: User,
    ):
        """Test login with prefs include."""
        mock_auth0_service.update_user_password.return_value = True

        response = client.post(
            f"{settings.API_V1_STR}/legacy/login",
            json={
                "username": test_user.name,
                "password": test_user.plaintext_password,
                "email": test_user.original_email,
                "include": "prefs",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "prefs" in data
        assert "status_max" in data["prefs"]
        assert "distance_ind" in data["prefs"]
        assert "email" in data["prefs"]
        assert "email_valid" in data["prefs"]

    @patch("api.api.v1.endpoints.legacy.auth0_service")
    def test_login_with_multiple_includes(
        self,
        mock_auth0_service: MagicMock,
        client: TestClient,
        db: Session,
        test_user: User,
    ):
        """Test login with multiple includes."""
        mock_auth0_service.update_user_password.return_value = True

        response = client.post(
            f"{settings.API_V1_STR}/legacy/login",
            json={
                "username": test_user.name,
                "password": test_user.plaintext_password,
                "email": test_user.original_email,
                "include": "stats,prefs",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "stats" in data
        assert "prefs" in data
        assert "breakdown" not in data

    @patch("api.api.v1.endpoints.legacy.auth0_service")
    def test_login_with_invalid_include(
        self,
        mock_auth0_service: MagicMock,
        client: TestClient,
        db: Session,
        test_user: User,
    ):
        """Test login with invalid include parameter."""
        mock_auth0_service.update_user_password.return_value = True

        response = client.post(
            f"{settings.API_V1_STR}/legacy/login",
            json={
                "username": test_user.name,
                "password": test_user.plaintext_password,
                "email": test_user.original_email,
                "include": "invalid",
            },
        )

        assert response.status_code == 400
        assert "Invalid include parameter" in response.json()["detail"]


class TestLegacyLoginEmailUpdate:
    """Test database email update functionality."""

    @patch("api.api.v1.endpoints.legacy.auth0_service")
    def test_email_updated_in_database(
        self,
        mock_auth0_service: MagicMock,
        client: TestClient,
        db: Session,
        test_user: User,
    ):
        """Test that email is updated in database."""
        import uuid

        unique_suffix = uuid.uuid4().hex[:8]

        mock_auth0_service.update_user_password.return_value = True
        mock_auth0_service.update_user_email.return_value = True

        new_email = f"updated_{unique_suffix}@example.com"
        response = client.post(
            f"{settings.API_V1_STR}/legacy/login",
            json={
                "username": test_user.name,
                "password": test_user.plaintext_password,
                "email": new_email,
            },
        )

        assert response.status_code == 200

        # Verify database was updated
        db.refresh(test_user)
        assert test_user.email == new_email
        assert test_user.email_valid == "Y"

    @patch("api.api.v1.endpoints.legacy.auth0_service")
    def test_email_valid_set_to_y(
        self,
        mock_auth0_service: MagicMock,
        client: TestClient,
        db: Session,
        test_user: User,
    ):
        """Test that email_valid is set to Y."""
        mock_auth0_service.update_user_password.return_value = True

        # Ensure email_valid is N initially
        test_user.email_valid = "N"  # type: ignore
        db.commit()

        response = client.post(
            f"{settings.API_V1_STR}/legacy/login",
            json={
                "username": test_user.name,
                "password": test_user.plaintext_password,
                "email": test_user.original_email,
            },
        )

        assert response.status_code == 200

        # Verify email_valid was set to Y
        db.refresh(test_user)
        assert test_user.email_valid == "Y"
