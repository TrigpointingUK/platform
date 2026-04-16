"""
Tests for the send_archives command scheduling logic.
"""

import uuid
from datetime import date, datetime, time, timedelta, timezone

from api.commands.send_archives import _is_user_due
from api.models.trig import Trig
from api.models.user import TLog, User, UserArchive


def _make_user(db, **overrides):
    from passlib.hash import des_crypt

    user = User(
        name=overrides.get("name", "scheduser"),
        firstname="Sched",
        surname="User",
        email=overrides.get("email", "sched@example.com"),
        cryptpw=des_crypt.hash("testpassword"),
        email_valid="Y",
        public_ind="Y",
        archive_frequency=overrides.get("archive_frequency", "N"),
        archive_format="C",
    )
    for k, v in overrides.items():
        setattr(user, k, v)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _add_published_log(db, user: User, *, upd_timestamp: datetime) -> None:
    suffix = uuid.uuid4().hex[:6]
    trig = Trig(
        waypoint=f"Z{suffix}"[:8],
        name="Schedule test trig",
        status_id=10,
        user_added=0,
        current_use="Passive station",
        historic_use="Primary",
        condition="G",
        wgs_lat=51.5,
        wgs_long=-0.1,
        wgs_height=0,
        osgb_eastings=530000,
        osgb_northings=180000,
        osgb_gridref="TQ 30000 80000",
        osgb_height=95,
        fb_number="",
        stn_number="",
        permission_ind="Y",
        postcode=None,
        town="Test",
        needs_attention=0,
        attention_comment="",
        crt_date=date(2023, 1, 1),
        crt_time=time(12, 0, 0),
        crt_user_id=user.id,
        crt_ip_addr="127.0.0.1",
    )
    db.add(trig)
    db.commit()
    db.refresh(trig)
    log = TLog(
        trig_id=trig.id,
        user_id=user.id,
        date=date(2024, 6, 15),
        time=time(14, 30),
        condition="G",
        comment="schedule test",
        score=1,
        ip_addr="127.0.0.1",
        source="W",
        status="P",
        upd_timestamp=upd_timestamp,
    )
    db.add(log)
    db.commit()


class TestIsUserDue:
    """Tests for the _is_user_due scheduling logic."""

    def test_frequency_never(self, db):
        user = _make_user(db, archive_frequency="N")
        now = datetime.now(timezone.utc)
        is_due, reason = _is_user_due(db, user, now)
        assert is_due is False
        assert "frequency=N" in reason

    def test_yearly_no_previous(self, db):
        user = _make_user(db, name="yearly1", archive_frequency="Y")
        now = datetime.now(timezone.utc)
        is_due, reason = _is_user_due(db, user, now)
        assert is_due is True
        assert "yearly" in reason

    def test_yearly_not_yet_due(self, db):
        user = _make_user(db, name="yearly2", archive_frequency="Y")
        now = datetime.now(timezone.utc)

        record = UserArchive(
            user_id=user.id,
            status="S",
            frequency_at_send="Y",
            format_at_send="C",
            created_at=now - timedelta(days=100),
        )
        db.add(record)
        db.commit()

        is_due, reason = _is_user_due(db, user, now)
        assert is_due is False
        assert "not yet due" in reason

    def test_yearly_past_due(self, db):
        user = _make_user(db, name="yearly3", archive_frequency="Y")
        now = datetime.now(timezone.utc)

        record = UserArchive(
            user_id=user.id,
            status="S",
            frequency_at_send="Y",
            format_at_send="C",
            created_at=now - timedelta(days=400),
        )
        db.add(record)
        db.commit()

        is_due, reason = _is_user_due(db, user, now)
        assert is_due is True

    def test_weekly_no_previous(self, db):
        user = _make_user(db, name="weekly1", archive_frequency="W")
        now = datetime.now(timezone.utc)
        is_due, _ = _is_user_due(db, user, now)
        assert is_due is True

    def test_monthly_no_previous(self, db):
        user = _make_user(db, name="monthly1", archive_frequency="M")
        now = datetime.now(timezone.utc)
        is_due, _ = _is_user_due(db, user, now)
        assert is_due is True

    def test_weekly_recently_sent(self, db):
        user = _make_user(db, name="weekly2", archive_frequency="W")
        now = datetime.now(timezone.utc)

        record = UserArchive(
            user_id=user.id,
            status="S",
            frequency_at_send="W",
            format_at_send="C",
            created_at=now - timedelta(days=2),
        )
        db.add(record)
        db.commit()

        is_due, reason = _is_user_due(db, user, now)
        assert is_due is False
        assert "not yet due" in reason

    def test_daily_no_previous(self, db):
        user = _make_user(db, name="daily1", archive_frequency="D")
        now = datetime.now(timezone.utc)
        is_due, reason = _is_user_due(db, user, now)
        assert is_due is True
        assert "daily" in reason

    def test_daily_recently_sent(self, db):
        user = _make_user(db, name="daily2", archive_frequency="D")
        now = datetime.now(timezone.utc)
        record = UserArchive(
            user_id=user.id,
            status="S",
            frequency_at_send="D",
            format_at_send="C",
            created_at=now - timedelta(hours=2),
        )
        db.add(record)
        db.commit()
        is_due, reason = _is_user_due(db, user, now)
        assert is_due is False
        assert "not yet due" in reason

    def test_daily_due_after_interval_without_new_activity(self, db):
        """D is unconditional daily: no requirement for new logs since last archive."""
        user = _make_user(db, name="daily3", archive_frequency="D")
        now = datetime.now(timezone.utc)
        sent_at = now - timedelta(days=2)
        record = UserArchive(
            user_id=user.id,
            status="S",
            frequency_at_send="D",
            format_at_send="C",
            created_at=sent_at,
        )
        db.add(record)
        db.commit()
        _add_published_log(db, user, upd_timestamp=sent_at - timedelta(days=1))
        is_due, reason = _is_user_due(db, user, now)
        assert is_due is True
        assert "daily: due" in reason

    def test_daily_new_activity_since_send(self, db):
        user = _make_user(db, name="daily4", archive_frequency="D")
        now = datetime.now(timezone.utc)
        sent_at = now - timedelta(days=2)
        record = UserArchive(
            user_id=user.id,
            status="S",
            frequency_at_send="D",
            format_at_send="C",
            created_at=sent_at,
        )
        db.add(record)
        db.commit()
        _add_published_log(db, user, upd_timestamp=now - timedelta(hours=1))
        is_due, reason = _is_user_due(db, user, now)
        assert is_due is True

    def test_bursty_active_daily_cadence(self, db):
        user = _make_user(db, name="burst1", archive_frequency="B")
        now = datetime.now(timezone.utc)
        sent_at = now - timedelta(days=2)
        record = UserArchive(
            user_id=user.id,
            status="S",
            frequency_at_send="B",
            format_at_send="C",
            created_at=sent_at,
        )
        db.add(record)
        db.commit()
        _add_published_log(db, user, upd_timestamp=now - timedelta(hours=1))
        is_due, reason = _is_user_due(db, user, now)
        assert is_due is True
        assert "daily" in reason

    def test_bursty_inactive_weekly_cadence(self, db):
        user = _make_user(db, name="burst2", archive_frequency="B")
        now = datetime.now(timezone.utc)
        sent_at = now - timedelta(days=10)
        record = UserArchive(
            user_id=user.id,
            status="S",
            frequency_at_send="B",
            format_at_send="C",
            created_at=sent_at,
        )
        db.add(record)
        db.commit()
        _add_published_log(db, user, upd_timestamp=now - timedelta(days=5))
        is_due, reason = _is_user_due(db, user, now)
        assert is_due is True
        assert "weekly-fallback" in reason
