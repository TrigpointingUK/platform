"""
Tests for the recent-activity log mode.

The home page uses mode=recent to show all logs from today and yesterday,
with a guaranteed minimum of `limit` rows (default 10).
"""

from datetime import date, datetime, time, timedelta

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from api.core.config import settings
from api.crud import tlog as tlog_crud
from api.models.user import TLog


def _make_log(db, trig_id, user_id, log_date):
    """Helper to create a published log on the given date."""
    log = TLog(
        trig_id=trig_id,
        user_id=user_id,
        date=log_date,
        time=time(12, 0, 0),
        condition="G",
        comment=f"Log on {log_date}",
        score=5,
        ip_addr="127.0.0.1",
        source="W",
        status="P",
        upd_timestamp=datetime.combine(log_date, time(12, 0, 0)),
    )
    db.add(log)
    return log


class TestListRecentActivityLogsCrud:
    """Tests for the list_recent_activity_logs CRUD function."""

    def test_returns_list(self, db: Session, test_trig, test_user):
        """Basic smoke test — the function returns a list."""
        result = tlog_crud.list_recent_activity_logs(db, min_count=10)
        assert isinstance(result, list)

    def test_includes_today_logs(self, db: Session, test_trig, test_user):
        """Logs dated today are always included."""
        _make_log(db, test_trig.id, test_user.id, date.today())
        db.flush()

        result = tlog_crud.list_recent_activity_logs(db, min_count=1)
        dates = [r.date for r in result]
        assert date.today() in dates

    def test_includes_yesterday_logs(self, db: Session, test_trig, test_user):
        """Logs dated yesterday are always included."""
        yesterday = date.today() - timedelta(days=1)
        _make_log(db, test_trig.id, test_user.id, yesterday)
        db.flush()

        result = tlog_crud.list_recent_activity_logs(db, min_count=1)
        dates = [r.date for r in result]
        assert yesterday in dates

    def test_backfills_when_recent_is_sparse(self, db: Session, test_trig, test_user):
        """When fewer than min_count logs exist for today+yesterday, older
        logs are added to reach the minimum."""
        _make_log(db, test_trig.id, test_user.id, date.today())
        for i in range(2, 7):
            _make_log(db, test_trig.id, test_user.id, date.today() - timedelta(days=i))
        db.flush()

        result = tlog_crud.list_recent_activity_logs(db, min_count=5)
        assert len(result) >= 5

    def test_returns_more_than_min_if_recent_days_busy(
        self, db: Session, test_trig, test_user
    ):
        """If today+yesterday have more than min_count logs, all are returned."""
        for i in range(15):
            _make_log(db, test_trig.id, test_user.id, date.today())
        db.flush()

        result = tlog_crud.list_recent_activity_logs(db, min_count=10)
        assert len(result) >= 15

    def test_excludes_drafts(self, db: Session, test_trig, test_user):
        """Draft logs (status='D') are never included."""
        draft = TLog(
            trig_id=test_trig.id,
            user_id=test_user.id,
            date=date.today(),
            time=time(12, 0, 0),
            status="D",
            ip_addr="127.0.0.1",
            source="W",
        )
        db.add(draft)
        db.flush()

        result = tlog_crud.list_recent_activity_logs(db, min_count=1)
        ids = [r.id for r in result]
        assert draft.id not in ids

    def test_ordering_newest_first(self, db: Session, test_trig, test_user):
        """Results are ordered newest-first by date."""
        yesterday = date.today() - timedelta(days=1)
        _make_log(db, test_trig.id, test_user.id, yesterday)
        _make_log(db, test_trig.id, test_user.id, date.today())
        db.flush()

        result = tlog_crud.list_recent_activity_logs(db, min_count=2)
        if len(result) >= 2:
            assert result[0].date >= result[1].date


class TestRecentModeEndpoint:
    """Tests for GET /v1/logs?mode=recent via the API."""

    def test_mode_recent_returns_200(self, client: TestClient):
        resp = client.get(f"{settings.API_V1_STR}/logs?mode=recent")
        assert resp.status_code == 200
        body = resp.json()
        assert "items" in body
        assert "pagination" in body

    def test_mode_recent_pagination_shape(self, client: TestClient):
        resp = client.get(f"{settings.API_V1_STR}/logs?mode=recent&limit=5")
        assert resp.status_code == 200
        body = resp.json()
        assert body["pagination"]["offset"] == 0
        assert body["pagination"]["has_more"] is False

    def test_mode_recent_with_photos_include(self, client: TestClient):
        resp = client.get(
            f"{settings.API_V1_STR}/logs?mode=recent&limit=5&include=photos"
        )
        assert resp.status_code == 200

    def test_mode_recent_invalid_include(self, client: TestClient):
        resp = client.get(f"{settings.API_V1_STR}/logs?mode=recent&include=bananas")
        assert resp.status_code == 400
