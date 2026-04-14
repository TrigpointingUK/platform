"""
Tests for the send_archives command scheduling logic.
"""

from datetime import datetime, timedelta, timezone

from api.commands.send_archives import _is_user_due
from api.models.user import User, UserArchive


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
