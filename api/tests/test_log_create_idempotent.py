"""
Tests for idempotent log creation behaviour.

When a user tries to create a log that already exists (same user, trig, date),
the API should return the existing log with HTTP 200 instead of 409 Conflict.
This supports mobile apps in poor connectivity where retries may occur after
the server successfully processed the first request.
"""

from typing import Optional

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from api.core.config import settings
from api.models.trig import Trig
from api.models.user import User


def get_or_create_test_trig(db: Session) -> Optional[Trig]:
    """Get existing trig or return None if none exists."""
    existing = db.query(Trig).first()
    return existing


def create_test_user(db: Session) -> User:
    """Create a unique test user with auth0_user_id set for authentication."""
    import uuid

    unique_suffix = uuid.uuid4().hex[:8]
    user = User(
        name=f"idempotent_user_{unique_suffix}",
        firstname="Idempotent",
        surname="TestUser",
        email=f"idempotent_{unique_suffix}@example.com",
        cryptpw="test",
        about="",
        email_valid="Y",
        public_ind="Y",
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # Set auth0_user_id to match the test mock pattern (auth0|{user_id})
    user.auth0_user_id = f"auth0|{user.id}"  # type: ignore[assignment]
    db.commit()
    db.refresh(user)
    return user


class TestLogCreateIdempotent:
    """Tests for idempotent POST /v1/logs behaviour."""

    def test_create_log_first_time_returns_201(self, client: TestClient, db: Session):
        """Test that creating a new log returns 201 Created."""
        trig = get_or_create_test_trig(db)
        if trig is None:
            pytest.skip("No trig available in test database")

        user = create_test_user(db)
        auth_header = {"Authorization": f"Bearer auth0_user_{user.id}"}

        payload = {
            "date": "2025-01-15",
            "time": "14:30:00",
            "osgb_eastings": 100000,
            "osgb_northings": 200000,
            "osgb_gridref": "TQ 00000 00000",
            "fb_number": "",
            "condition": "G",
            "comment": "First log creation",
            "score": 7,
            "source": "W",
        }

        resp = client.post(
            f"{settings.API_V1_STR}/logs?trig_id={trig.id}",
            json=payload,
            headers=auth_header,
        )

        assert (
            resp.status_code == 201
        ), f"Expected 201, got {resp.status_code}: {resp.text}"
        body = resp.json()
        assert body["trig_id"] == trig.id
        assert body["user_id"] == user.id
        assert body["date"] == "2025-01-15"
        assert body["condition"] == "G"

    def test_create_duplicate_log_returns_200_with_existing(
        self, client: TestClient, db: Session
    ):
        """Test that creating a duplicate log returns 200 OK with the existing log.

        This is the key idempotency test - simulating a retry after the first
        request succeeded but the client didn't receive the response.
        """
        trig = get_or_create_test_trig(db)
        if trig is None:
            pytest.skip("No trig available in test database")

        user = create_test_user(db)
        auth_header = {"Authorization": f"Bearer auth0_user_{user.id}"}

        payload = {
            "date": "2025-02-20",
            "time": "10:00:00",
            "osgb_eastings": 100000,
            "osgb_northings": 200000,
            "osgb_gridref": "TQ 00000 00000",
            "fb_number": "",
            "condition": "G",
            "comment": "Original comment",
            "score": 5,
            "source": "W",
        }

        # First request - should create the log (201)
        resp1 = client.post(
            f"{settings.API_V1_STR}/logs?trig_id={trig.id}",
            json=payload,
            headers=auth_header,
        )
        assert resp1.status_code == 201
        first_body = resp1.json()
        created_log_id = first_body["id"]

        # Second request with same payload - should return existing log (200)
        resp2 = client.post(
            f"{settings.API_V1_STR}/logs?trig_id={trig.id}",
            json=payload,
            headers=auth_header,
        )

        assert (
            resp2.status_code == 200
        ), f"Expected 200, got {resp2.status_code}: {resp2.text}"
        second_body = resp2.json()

        # Should return the same log that was created
        assert second_body["id"] == created_log_id
        assert second_body["trig_id"] == trig.id
        assert second_body["user_id"] == user.id
        assert second_body["date"] == "2025-02-20"

    def test_create_duplicate_log_with_different_payload_returns_existing(
        self, client: TestClient, db: Session
    ):
        """Test that duplicate detection is based on user+trig+date, not full payload.

        Even if the comment or other fields differ, if user+trig+date match,
        the existing log should be returned.
        """
        trig = get_or_create_test_trig(db)
        if trig is None:
            pytest.skip("No trig available in test database")

        user = create_test_user(db)
        auth_header = {"Authorization": f"Bearer auth0_user_{user.id}"}

        # Create first log
        payload1 = {
            "date": "2025-03-15",
            "time": "09:00:00",
            "osgb_eastings": 100000,
            "osgb_northings": 200000,
            "osgb_gridref": "TQ 00000 00000",
            "fb_number": "",
            "condition": "G",
            "comment": "Original comment",
            "score": 8,
            "source": "W",
        }

        resp1 = client.post(
            f"{settings.API_V1_STR}/logs?trig_id={trig.id}",
            json=payload1,
            headers=auth_header,
        )
        assert resp1.status_code == 201
        original_log = resp1.json()

        # Try to create second log with same date but different comment
        payload2 = {
            "date": "2025-03-15",  # Same date
            "time": "15:00:00",  # Different time
            "osgb_eastings": 100000,
            "osgb_northings": 200000,
            "osgb_gridref": "TQ 00000 00000",
            "fb_number": "",
            "condition": "D",  # Different condition
            "comment": "Different comment",  # Different comment
            "score": 3,  # Different score
            "source": "W",
        }

        resp2 = client.post(
            f"{settings.API_V1_STR}/logs?trig_id={trig.id}",
            json=payload2,
            headers=auth_header,
        )

        assert resp2.status_code == 200
        returned_log = resp2.json()

        # Should return the original log, not create a new one
        assert returned_log["id"] == original_log["id"]
        # Original values should be preserved
        assert returned_log["comment"] == "Original comment"
        assert returned_log["condition"] == "G"
        assert returned_log["score"] == 8

    def test_same_date_different_trig_creates_new_log(
        self, client: TestClient, db: Session
    ):
        """Test that same user+date but different trig creates a new log."""
        trigs = db.query(Trig).limit(2).all()
        if len(trigs) < 2:
            pytest.skip("Need at least 2 trigs in test database")

        user = create_test_user(db)
        auth_header = {"Authorization": f"Bearer auth0_user_{user.id}"}

        payload = {
            "date": "2025-04-10",
            "time": "12:00:00",
            "osgb_eastings": 100000,
            "osgb_northings": 200000,
            "osgb_gridref": "TQ 00000 00000",
            "fb_number": "",
            "condition": "G",
            "comment": "Test",
            "score": 5,
            "source": "W",
        }

        # Create log for first trig
        resp1 = client.post(
            f"{settings.API_V1_STR}/logs?trig_id={trigs[0].id}",
            json=payload,
            headers=auth_header,
        )
        assert resp1.status_code == 201
        log1_id = resp1.json()["id"]

        # Create log for second trig (same date) - should create new log
        resp2 = client.post(
            f"{settings.API_V1_STR}/logs?trig_id={trigs[1].id}",
            json=payload,
            headers=auth_header,
        )
        assert resp2.status_code == 201
        log2_id = resp2.json()["id"]

        # Should be different logs
        assert log1_id != log2_id

    def test_same_trig_different_date_creates_new_log(
        self, client: TestClient, db: Session
    ):
        """Test that same user+trig but different date creates a new log."""
        trig = get_or_create_test_trig(db)
        if trig is None:
            pytest.skip("No trig available in test database")

        user = create_test_user(db)
        auth_header = {"Authorization": f"Bearer auth0_user_{user.id}"}

        # Create first log
        payload1 = {
            "date": "2025-05-01",
            "time": "12:00:00",
            "osgb_eastings": 100000,
            "osgb_northings": 200000,
            "osgb_gridref": "TQ 00000 00000",
            "fb_number": "",
            "condition": "G",
            "comment": "May visit",
            "score": 5,
            "source": "W",
        }

        resp1 = client.post(
            f"{settings.API_V1_STR}/logs?trig_id={trig.id}",
            json=payload1,
            headers=auth_header,
        )
        assert resp1.status_code == 201
        log1_id = resp1.json()["id"]

        # Create second log with different date
        payload2 = {
            "date": "2025-05-15",  # Different date
            "time": "12:00:00",
            "osgb_eastings": 100000,
            "osgb_northings": 200000,
            "osgb_gridref": "TQ 00000 00000",
            "fb_number": "",
            "condition": "G",
            "comment": "Another visit",
            "score": 5,
            "source": "W",
        }

        resp2 = client.post(
            f"{settings.API_V1_STR}/logs?trig_id={trig.id}",
            json=payload2,
            headers=auth_header,
        )
        assert resp2.status_code == 201
        log2_id = resp2.json()["id"]

        # Should be different logs
        assert log1_id != log2_id
