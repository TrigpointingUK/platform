"""
Tests for user merge functionality.
"""

from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from api.crud import user_merge as user_merge_crud
from api.main import app
from api.models.user import TLog, TPhotoVote, User

client = TestClient(app)


def create_test_user(
    db: Session, username: str, email: str, auth0_id: str = None
) -> User:
    """Helper to create a test user."""
    from datetime import date as date_type
    from datetime import time as time_type

    user = User(
        name=username,
        email=email,
        firstname="",
        surname="",
        auth0_user_id=auth0_id,
        cryptpw="test",
        crt_date=date_type.today(),
        crt_time=time_type(0, 0, 0),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def create_test_activity(db: Session, user_id: int, days_ago: int = 0) -> None:
    """Helper to create test activity for a user."""
    activity_date = datetime.now(timezone.utc) - timedelta(days=days_ago)

    # Create a tlog entry
    tlog = TLog(
        user_id=user_id,
        trig_id=1,
        date=activity_date.date(),
        time=activity_date.time(),
        osgb_eastings=0,
        osgb_northings=0,
        osgb_gridref="",
        fb_number="",
        condition="G",
        comment="Test",
        score=0,
        ip_addr="127.0.0.1",
        source="T",
        upd_timestamp=activity_date,
    )
    db.add(tlog)
    db.commit()


@pytest.fixture
def mock_admin_token(monkeypatch):
    """Mock admin token validation."""

    def mock_verify(token_payload: dict):
        return {"scope": "openid profile api:admin"}

    from api.api import deps

    monkeypatch.setattr(deps, "require_scopes", lambda scope: lambda: None)


class TestEmailDuplicatesEndpoint:
    """Tests for GET /v1/legacy/email-duplicates endpoint."""

    def test_get_duplicates_no_admin(self, db: Session):
        """Test that endpoint requires admin scope."""
        response = client.get("/v1/legacy/email-duplicates")
        # Should fail authentication
        assert response.status_code in [401, 403]

    def test_get_duplicates_empty(self, db: Session, mock_admin_token):
        """Test when there are no duplicate emails."""
        # Create users with unique emails
        create_test_user(db, "user1", "user1@example.com", "auth0|1")
        create_test_user(db, "user2", "user2@example.com", "auth0|2")

        response = client.get("/v1/legacy/email-duplicates")
        assert response.status_code == 200
        data = response.json()
        assert data["total_duplicate_emails"] == 0
        assert len(data["duplicates"]) == 0

    def test_get_duplicates_with_duplicates(self, db: Session, mock_admin_token):
        """Test when there are duplicate emails."""
        # Create users with duplicate email
        user1 = create_test_user(db, "user1", "duplicate@example.com", "auth0|1")
        user2 = create_test_user(db, "user2", "duplicate@example.com", "auth0|2")

        # Add some activity
        create_test_activity(db, int(user1.id), days_ago=10)
        create_test_activity(db, int(user2.id), days_ago=5)

        response = client.get("/v1/legacy/email-duplicates")
        assert response.status_code == 200
        data = response.json()
        assert data["total_duplicate_emails"] == 1
        assert len(data["duplicates"]) == 1
        assert data["duplicates"][0]["email"] == "duplicate@example.com"
        assert data["duplicates"][0]["user_count"] == 2
        assert len(data["duplicates"][0]["users"]) == 2

    def test_get_duplicates_with_filter(self, db: Session, mock_admin_token):
        """Test filtering by specific email."""
        # Create multiple duplicate email sets
        create_test_user(db, "user1", "dup1@example.com", "auth0|1")
        create_test_user(db, "user2", "dup1@example.com", "auth0|2")
        create_test_user(db, "user3", "dup2@example.com", "auth0|3")
        create_test_user(db, "user4", "dup2@example.com", "auth0|4")

        response = client.get("/v1/legacy/email-duplicates?email=dup1@example.com")
        assert response.status_code == 200
        data = response.json()
        assert data["total_duplicate_emails"] == 1
        assert data["duplicates"][0]["email"] == "dup1@example.com"


class TestMergeUsersEndpoint:
    """Tests for POST /v1/legacy/merge_users endpoint."""

    def test_merge_no_admin(self, db: Session):
        """Test that endpoint requires admin scope."""
        response = client.post(
            "/v1/legacy/merge_users",
            json={"email": "test@example.com"},
        )
        # Should fail authentication
        assert response.status_code in [401, 403]

    def test_merge_email_not_found(self, db: Session, mock_admin_token):
        """Test merge with non-existent email."""
        response = client.post(
            "/v1/legacy/merge_users",
            json={"email": "nonexistent@example.com", "dry_run": True},
        )
        assert response.status_code == 404
        assert "No users found" in response.json()["detail"]

    def test_merge_single_user(self, db: Session, mock_admin_token):
        """Test merge when only one user has the email."""
        create_test_user(db, "user1", "single@example.com", "auth0|1")

        response = client.post(
            "/v1/legacy/merge_users",
            json={"email": "single@example.com", "dry_run": True},
        )
        assert response.status_code == 400
        assert "Only one user" in response.json()["detail"]

    def test_merge_dry_run_no_conflicts(self, db: Session, mock_admin_token):
        """Test dry run merge with no conflicts."""
        # Create users with old activity (no conflict)
        user1 = create_test_user(db, "user1", "merge@example.com", "auth0|1")
        user2 = create_test_user(db, "user2", "merge@example.com", "auth0|2")

        # User1 has recent activity, user2 has old activity
        create_test_activity(db, int(user1.id), days_ago=10)
        create_test_activity(db, int(user2.id), days_ago=200)  # > 180 days

        response = client.post(
            "/v1/legacy/merge_users",
            json={
                "email": "merge@example.com",
                "dry_run": True,
                "activity_threshold_days": 180,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["dry_run"] is True
        assert data["email"] == "merge@example.com"
        assert data["primary_user_id"] == int(user1.id)
        assert int(user2.id) in data["users_to_merge"]

    def test_merge_with_conflicts(self, db: Session, mock_admin_token):
        """Test merge with activity conflicts."""
        # Create users with recent activity (conflict)
        user1 = create_test_user(db, "user1", "conflict@example.com", "auth0|1")
        user2 = create_test_user(db, "user2", "conflict@example.com", "auth0|2")

        # Both users have recent activity
        create_test_activity(db, int(user1.id), days_ago=10)
        create_test_activity(db, int(user2.id), days_ago=20)  # < 180 days

        response = client.post(
            "/v1/legacy/merge_users",
            json={
                "email": "conflict@example.com",
                "dry_run": True,
                "activity_threshold_days": 180,
            },
        )
        assert response.status_code == 409
        data = response.json()["detail"]
        assert data["error"] == "merge_conflict"
        assert data["email"] == "conflict@example.com"
        assert len(data["conflicting_users"]) == 1

    def test_merge_execute_no_conflicts(self, db: Session, mock_admin_token):
        """Test actual merge execution."""
        # Create users with old activity
        user1 = create_test_user(db, "primary", "execute@example.com", "auth0|1")
        user2 = create_test_user(db, "secondary", "execute@example.com", "auth0|2")

        # Add activity and profile data
        user1.firstname = "Primary"
        user1.surname = "User"
        user2.homepage = "http://example.com"
        user2.about = "About text"
        db.commit()

        create_test_activity(db, int(user1.id), days_ago=10)
        create_test_activity(db, int(user2.id), days_ago=200)

        # Create additional activity records
        tphotovote = TPhotoVote(
            tphoto_id=1,
            user_id=int(user2.id),
            score=5,
            upd_timestamp=datetime.now(timezone.utc) - timedelta(days=200),
        )
        db.add(tphotovote)
        db.commit()

        response = client.post(
            "/v1/legacy/merge_users",
            json={
                "email": "execute@example.com",
                "dry_run": False,
                "activity_threshold_days": 180,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["primary_user_id"] == int(user1.id)
        assert int(user2.id) in data["merged_user_ids"]

        # Verify user2 was deleted
        deleted_user = db.query(User).filter(User.id == user2.id).first()
        assert deleted_user is None

        # Verify primary user still exists
        primary_user = db.query(User).filter(User.id == user1.id).first()
        assert primary_user is not None

        # Verify profile was updated with best values
        assert primary_user.homepage == "http://example.com"
        assert primary_user.about == "About text"

        # Verify activity was reassigned
        vote = db.query(TPhotoVote).filter(TPhotoVote.tphoto_id == 1).first()
        assert vote.user_id == int(user1.id)

    def test_merge_no_activity_users(self, db: Session, mock_admin_token):
        """Test merge with users having no activity."""
        # Create users with no activity
        user1 = create_test_user(db, "user1", "noactivity@example.com", "auth0|1")
        user2 = create_test_user(db, "user2", "noactivity@example.com", "auth0|2")

        # Older creation date = less recent
        user1.crt_date = (datetime.now() - timedelta(days=100)).date()
        user2.crt_date = (datetime.now() - timedelta(days=300)).date()
        db.commit()

        response = client.post(
            "/v1/legacy/merge_users",
            json={
                "email": "noactivity@example.com",
                "dry_run": True,
            },
        )
        assert response.status_code == 200
        data = response.json()
        # User with more recent creation date should be primary
        assert data["primary_user_id"] == int(user1.id)


class TestUserMergeCRUD:
    """Tests for CRUD operations."""

    def test_find_users_by_email(self, db: Session):
        """Test finding users by email."""
        user1 = create_test_user(db, "user1", "test@example.com", "auth0|1")
        user2 = create_test_user(db, "user2", "test@example.com", "auth0|2")

        users = user_merge_crud.find_users_by_email(db, "test@example.com")
        assert len(users) == 2
        user_ids = [u.id for u in users]
        assert user1.id in user_ids
        assert user2.id in user_ids

    def test_find_users_by_email_case_insensitive(self, db: Session):
        """Test case-insensitive email search."""
        create_test_user(db, "user1", "Test@Example.COM", "auth0|1")

        users = user_merge_crud.find_users_by_email(db, "test@example.com")
        assert len(users) == 1

    def test_get_user_last_activity(self, db: Session):
        """Test getting user's last activity."""
        user = create_test_user(db, "user1", "test@example.com", "auth0|1")
        create_test_activity(db, int(user.id), days_ago=10)

        last_activity = user_merge_crud.get_user_last_activity(db, int(user.id))
        assert last_activity is not None
        # Should be approximately 10 days ago
        days_diff = (datetime.now(timezone.utc) - last_activity).days
        assert 9 <= days_diff <= 11

    def test_get_user_activity_counts(self, db: Session):
        """Test getting activity counts."""
        user = create_test_user(db, "user1", "test@example.com", "auth0|1")
        create_test_activity(db, int(user.id), days_ago=10)
        create_test_activity(db, int(user.id), days_ago=20)

        counts = user_merge_crud.get_user_activity_counts(db, int(user.id))
        assert counts["logs"] == 2
        assert counts["photos"] >= 0
        assert counts["photo_votes"] >= 0

    def test_check_merge_conflicts(self, db: Session):
        """Test conflict detection."""
        user1 = create_test_user(db, "user1", "test@example.com", "auth0|1")
        user2 = create_test_user(db, "user2", "test@example.com", "auth0|2")

        # User1 recent, user2 old
        create_test_activity(db, int(user1.id), days_ago=10)
        create_test_activity(db, int(user2.id), days_ago=200)

        users = [user1, user2]
        users_with_activity = user_merge_crud.get_users_with_activity(db, users)

        primary, conflicts = user_merge_crud.check_merge_conflicts(
            db, users_with_activity, 180
        )
        assert primary.id == user1.id
        assert len(conflicts) == 0

    def test_check_merge_conflicts_with_conflict(self, db: Session):
        """Test conflict detection with actual conflict."""
        user1 = create_test_user(db, "user1", "test@example.com", "auth0|1")
        user2 = create_test_user(db, "user2", "test@example.com", "auth0|2")

        # Both users recent
        create_test_activity(db, int(user1.id), days_ago=10)
        create_test_activity(db, int(user2.id), days_ago=20)

        users = [user1, user2]
        users_with_activity = user_merge_crud.get_users_with_activity(db, users)

        primary, conflicts = user_merge_crud.check_merge_conflicts(
            db, users_with_activity, 180
        )
        assert primary.id == user1.id
        assert len(conflicts) == 1
        assert conflicts[0].user_id == int(user2.id)

    def test_select_best_profile_values(self, db: Session):
        """Test selecting best profile values."""
        user1 = create_test_user(db, "user1", "test@example.com", "auth0|1")
        user2 = create_test_user(db, "user2", "test@example.com", "auth0|2")

        # User1 has firstname, user2 has surname and homepage
        user1.firstname = "John"
        user1.upd_timestamp = datetime.now(timezone.utc) - timedelta(days=10)
        user2.surname = "Doe"
        user2.homepage = "http://example.com"
        user2.upd_timestamp = datetime.now(timezone.utc) - timedelta(days=5)
        db.commit()

        best_values = user_merge_crud.select_best_profile_values(
            db, [int(user1.id), int(user2.id)], ["firstname", "surname", "homepage"]
        )

        # Most recent non-empty values should be selected
        assert best_values["surname"] == "Doe"
        assert best_values["homepage"] == "http://example.com"

    def test_count_records_for_users(self, db: Session):
        """Test counting records."""
        user = create_test_user(db, "user1", "test@example.com", "auth0|1")
        create_test_activity(db, int(user.id), days_ago=10)
        create_test_activity(db, int(user.id), days_ago=20)

        counts = user_merge_crud.count_records_for_users(db, [int(user.id)])
        assert counts.tlog == 2

    def test_merge_users_operation(self, db: Session):
        """Test actual merge operation."""
        user1 = create_test_user(db, "primary", "test@example.com", "auth0|1")
        user2 = create_test_user(db, "secondary", "test@example.com", "auth0|2")

        create_test_activity(db, int(user2.id), days_ago=10)

        # Execute merge
        counts = user_merge_crud.merge_users(db, int(user1.id), [int(user2.id)])

        # Verify counts
        assert counts.tlog == 1

        # Verify user2 deleted
        deleted = db.query(User).filter(User.id == user2.id).first()
        assert deleted is None

        # Verify activity reassigned
        logs = db.query(TLog).filter(TLog.user_id == user1.id).all()
        assert len(logs) == 1
