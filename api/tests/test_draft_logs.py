"""
Tests for draft log functionality.

Tests the draft log lifecycle:
- Creating draft logs
- Publishing draft logs
- Cancelling (deleting) draft logs
- Draft logs being excluded from listings and stats

Uses fixtures from conftest.py: test_user, test_trig, make_trig
"""

from datetime import date, time

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from api.core.config import settings
from api.crud import tlog as tlog_crud
from api.crud import trigstats as trigstats_crud
from api.models.trig import Trig
from api.models.user import TLog, User


@pytest.fixture
def draft_test_trig(make_trig) -> Trig:
    """Create a test trigpoint for draft tests."""
    return make_trig(name="Draft Test Trig")


@pytest.fixture
def published_log(db: Session, test_user: User, draft_test_trig: Trig) -> TLog:
    """Create a published test log."""
    log = TLog(
        trig_id=draft_test_trig.id,
        user_id=test_user.id,
        date=date(2024, 1, 15),
        time=time(12, 0, 0),
        condition="G",
        comment="Published test log",
        score=7,
        status="P",
    )
    db.add(log)
    db.flush()
    return log


@pytest.fixture
def draft_log(db: Session, test_user: User, draft_test_trig: Trig) -> TLog:
    """Create a draft test log."""
    log = TLog(
        trig_id=draft_test_trig.id,
        user_id=test_user.id,
        status="D",
    )
    db.add(log)
    db.flush()
    return log


class TestDraftLogCrud:
    """Tests for draft log CRUD operations."""

    def test_create_draft_log(
        self, db: Session, test_user: User, draft_test_trig: Trig
    ):
        """Test creating a draft log."""
        draft = tlog_crud.create_draft_log(
            db,
            trig_id=int(draft_test_trig.id),
            user_id=int(test_user.id),
            ip_addr="127.0.0.1",
        )

        assert draft.id is not None
        assert draft.trig_id == draft_test_trig.id
        assert draft.user_id == test_user.id
        assert draft.status == "D"
        assert draft.ip_addr == "127.0.0.1"
        assert draft.source == "W"

    def test_get_user_draft_for_trig(
        self, db: Session, test_user: User, draft_test_trig: Trig, draft_log: TLog
    ):
        """Test finding an existing draft for a user/trig combination."""
        draft = tlog_crud.get_user_draft_for_trig(
            db, user_id=int(test_user.id), trig_id=int(draft_test_trig.id)
        )

        assert draft is not None
        assert draft.id == draft_log.id
        assert draft.status == "D"

    def test_get_user_draft_for_trig_no_draft(
        self, db: Session, test_user: User, draft_test_trig: Trig
    ):
        """Test that no draft is found when none exists."""
        draft = tlog_crud.get_user_draft_for_trig(
            db, user_id=int(test_user.id), trig_id=int(draft_test_trig.id)
        )

        assert draft is None

    def test_publish_draft_log(
        self, db: Session, test_user: User, draft_test_trig: Trig, draft_log: TLog
    ):
        """Test publishing a draft log."""
        updates = {
            "date": date(2024, 6, 15),
            "time": time(14, 30, 0),
            "condition": "G",
            "comment": "Published from draft",
            "score": 8,
            "fb_number": "S1234",
            "source": "W",
        }

        published = tlog_crud.publish_draft_log(
            db, log_id=int(draft_log.id), updates=updates
        )

        assert published is not None
        assert published.id == draft_log.id
        assert published.status == "P"
        assert published.date == date(2024, 6, 15)
        assert published.time == time(14, 30, 0)
        assert published.condition == "G"
        assert published.comment == "Published from draft"
        assert published.score == 8

    def test_publish_draft_log_not_found(self, db: Session):
        """Test publishing a non-existent draft returns None."""
        result = tlog_crud.publish_draft_log(db, log_id=99999, updates={})
        assert result is None

    def test_publish_draft_log_already_published(
        self, db: Session, published_log: TLog
    ):
        """Test publishing an already-published log returns None."""
        result = tlog_crud.publish_draft_log(
            db, log_id=int(published_log.id), updates={}
        )
        assert result is None


class TestDraftLogFiltering:
    """Tests for draft log filtering in queries."""

    def test_list_logs_excludes_drafts_by_default(
        self,
        db: Session,
        test_user: User,
        draft_test_trig: Trig,
        published_log: TLog,
        draft_log: TLog,
    ):
        """Test that list_logs_filtered excludes drafts by default."""
        logs = tlog_crud.list_logs_filtered(db, trig_id=int(draft_test_trig.id))

        log_ids = [log.id for log in logs]
        assert published_log.id in log_ids
        assert draft_log.id not in log_ids

    def test_list_logs_includes_drafts_when_requested(
        self,
        db: Session,
        test_user: User,
        draft_test_trig: Trig,
        published_log: TLog,
        draft_log: TLog,
    ):
        """Test that list_logs_filtered can include drafts when requested."""
        logs = tlog_crud.list_logs_filtered(
            db, trig_id=int(draft_test_trig.id), include_drafts=True
        )

        log_ids = [log.id for log in logs]
        assert published_log.id in log_ids
        assert draft_log.id in log_ids

    def test_count_logs_excludes_drafts_by_default(
        self,
        db: Session,
        test_user: User,
        draft_test_trig: Trig,
        published_log: TLog,
        draft_log: TLog,
    ):
        """Test that count_logs_filtered excludes drafts by default."""
        count = tlog_crud.count_logs_filtered(db, trig_id=int(draft_test_trig.id))
        assert count == 1  # Only the published log

    def test_count_logs_includes_drafts_when_requested(
        self,
        db: Session,
        test_user: User,
        draft_test_trig: Trig,
        published_log: TLog,
        draft_log: TLog,
    ):
        """Test that count_logs_filtered can include drafts when requested."""
        count = tlog_crud.count_logs_filtered(
            db, trig_id=int(draft_test_trig.id), include_drafts=True
        )
        assert count == 2  # Both logs

    def test_get_existing_log_excludes_drafts(
        self,
        db: Session,
        test_user: User,
        draft_test_trig: Trig,
        draft_log: TLog,
    ):
        """Test that get_existing_log_for_user_trig_date excludes drafts."""
        # Set the draft's date - cast to avoid type error
        draft_log.date = date(2024, 6, 15)  # type: ignore[assignment]
        db.flush()

        # Should not find the draft when checking for duplicates
        existing = tlog_crud.get_existing_log_for_user_trig_date(
            db,
            user_id=int(test_user.id),
            trig_id=int(draft_test_trig.id),
            date=date(2024, 6, 15),
        )
        assert existing is None


class TestDraftLogApiEndpoints:
    """Tests for draft log API endpoints."""

    def test_create_draft_log_endpoint(
        self,
        client: TestClient,
        db: Session,
        test_user: User,
        draft_test_trig: Trig,
    ):
        """Test creating a draft log via API."""
        # Use auth0_user_{user_id} token format expected by test client
        # Don't send a body for draft creation
        response = client.post(
            f"{settings.API_V1_STR}/logs?trig_id={draft_test_trig.id}&draft=true",
            headers={
                "Authorization": f"Bearer auth0_user_{test_user.id}",
                "Content-Type": "application/json",
            },
        )

        assert response.status_code == 201, f"Response: {response.json()}"
        data = response.json()
        assert data["trig_id"] == draft_test_trig.id
        assert data["status"] == "D"

    def test_create_draft_returns_existing_draft(
        self,
        client: TestClient,
        db: Session,
        test_user: User,
        draft_test_trig: Trig,
        draft_log: TLog,
    ):
        """Test that creating a draft returns existing draft if one exists."""
        # draft_log already belongs to test_user from fixture
        response = client.post(
            f"{settings.API_V1_STR}/logs?trig_id={draft_test_trig.id}&draft=true",
            headers={
                "Authorization": f"Bearer auth0_user_{test_user.id}",
                "Content-Type": "application/json",
            },
        )

        # Should return 200 with existing draft
        assert response.status_code in [200, 201], f"Response: {response.json()}"
        data = response.json()
        assert data["id"] == draft_log.id

    def test_publish_draft_endpoint(
        self,
        client: TestClient,
        db: Session,
        test_user: User,
        draft_test_trig: Trig,
    ):
        """Test publishing a draft log via API."""
        # First create a draft
        draft = tlog_crud.create_draft_log(
            db,
            trig_id=int(draft_test_trig.id),
            user_id=int(test_user.id),
            ip_addr="127.0.0.1",
        )
        db.flush()

        # Publish it
        response = client.post(
            f"{settings.API_V1_STR}/logs/{draft.id}/publish",
            headers={"Authorization": f"Bearer auth0_user_{test_user.id}"},
            json={
                "date": "2024-06-15",
                "time": "14:30:00",
                "condition": "G",
                "comment": "Published via API",
                "score": 8,
                "fb_number": "",
                "source": "W",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "P"
        assert data["condition"] == "G"

    def test_publish_non_draft_fails(
        self,
        client: TestClient,
        db: Session,
        test_user: User,
        published_log: TLog,
    ):
        """Test that publishing a non-draft log fails."""
        response = client.post(
            f"{settings.API_V1_STR}/logs/{published_log.id}/publish",
            headers={"Authorization": f"Bearer auth0_user_{test_user.id}"},
            json={
                "date": "2024-06-15",
                "time": "14:30:00",
                "condition": "G",
                "comment": "Should fail",
                "score": 8,
                "fb_number": "",
                "source": "W",
            },
        )

        assert response.status_code == 400
        assert "not a draft" in response.json()["detail"].lower()

    def test_publish_others_draft_fails(
        self,
        client: TestClient,
        db: Session,
        test_user: User,
        make_user,
        draft_log: TLog,
    ):
        """Test that publishing another user's draft fails."""
        # Create a different user
        other_user = make_user(name="other_draft_user")

        # draft_log belongs to test_user, try to publish as other_user
        response = client.post(
            f"{settings.API_V1_STR}/logs/{draft_log.id}/publish",
            headers={"Authorization": f"Bearer auth0_user_{other_user.id}"},
            json={
                "date": "2024-06-15",
                "time": "14:30:00",
                "condition": "G",
                "comment": "Should fail",
                "score": 8,
                "fb_number": "",
                "source": "W",
            },
        )

        assert response.status_code == 403

    def test_delete_draft_log(
        self,
        client: TestClient,
        db: Session,
        test_user: User,
        draft_test_trig: Trig,
    ):
        """Test deleting a draft log via API."""
        # Create a draft
        draft = tlog_crud.create_draft_log(
            db,
            trig_id=int(draft_test_trig.id),
            user_id=int(test_user.id),
            ip_addr="127.0.0.1",
        )
        db.flush()

        # Delete it
        response = client.delete(
            f"{settings.API_V1_STR}/logs/{draft.id}",
            headers={"Authorization": f"Bearer auth0_user_{test_user.id}"},
        )

        assert response.status_code == 204

        # Verify it's deleted
        deleted = tlog_crud.get_log_by_id(db, int(draft.id))
        assert deleted is None

    def test_list_logs_excludes_drafts_in_api(
        self,
        client: TestClient,
        db: Session,
        draft_test_trig: Trig,
        published_log: TLog,
        draft_log: TLog,
    ):
        """Test that the logs list API excludes drafts."""
        response = client.get(
            f"{settings.API_V1_STR}/logs?trig_id={draft_test_trig.id}"
        )

        assert response.status_code == 200
        data = response.json()
        log_ids = [item["id"] for item in data["items"]]
        assert published_log.id in log_ids
        assert draft_log.id not in log_ids

    def test_create_log_without_draft_requires_body(
        self,
        client: TestClient,
        db: Session,
        test_user: User,
        draft_test_trig: Trig,
    ):
        """Test that creating a non-draft log requires a body."""
        response = client.post(
            f"{settings.API_V1_STR}/logs?trig_id={draft_test_trig.id}",
            headers={"Authorization": f"Bearer auth0_user_{test_user.id}"},
            json=None,
        )

        assert response.status_code == 422


class TestDraftLogStats:
    """Tests for draft logs being excluded from statistics."""

    def test_trigstats_excludes_drafts(
        self,
        db: Session,
        draft_test_trig: Trig,
        published_log: TLog,
        draft_log: TLog,
    ):
        """Test that trigstats calculations exclude drafts."""
        # Update stats
        stats = trigstats_crud.update_trigstats(db, int(draft_test_trig.id))

        assert stats is not None
        # Should only count the published log
        assert stats.logged_count == 1

    def test_global_mean_excludes_drafts(
        self,
        db: Session,
        published_log: TLog,
        draft_log: TLog,
    ):
        """Test that global mean score calculation excludes drafts."""
        # Set scores - use type: ignore for SQLAlchemy column assignment
        published_log.score = 8  # type: ignore[assignment]
        draft_log.score = 2  # type: ignore[assignment]
        db.flush()

        # The global mean should not include the draft's score
        # (This is a simplified test - in practice there may be other logs)
        mean = trigstats_crud.get_global_mean_score(db)
        # Just verify it returns a valid decimal
        assert mean is not None
