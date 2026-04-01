"""
Tests for crud/user_merge.py — user merge CRUD operations.
"""

from datetime import date, datetime, time

import pytest

from api.crud.user_merge import (
    count_records_for_user,
    find_users_by_email,
    get_email_duplicates_summary,
    get_user_activity_counts,
    get_user_last_activity,
    merge_users_admin,
)
from api.models.user import TLog, User


@pytest.fixture
def two_users(db, make_user):
    """Create two users with the same email."""
    u1 = make_user(email="dup@example.com", name="user_alpha")
    u2 = make_user(email="dup@example.com", name="user_beta")
    return u1, u2


@pytest.fixture
def user_with_logs(db, make_user, make_trig):
    user = make_user()
    trig = make_trig()
    log = TLog(
        trig_id=trig.id,
        user_id=user.id,
        date=date(2024, 1, 15),
        time=time(10, 0),
        osgb_eastings=100000,
        osgb_northings=200000,
        osgb_gridref="TQ 00000 00000",
        fb_number="",
        condition="G",
        comment="Test",
        score=5,
        ip_addr="127.0.0.1",
        source="W",
        upd_timestamp=datetime(2024, 1, 15, 10, 0),
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return user, trig, log


class TestFindUsersByEmail:
    def test_finds_users_case_insensitive(self, db, two_users):
        u1, u2 = two_users
        results = find_users_by_email(db, "DUP@EXAMPLE.COM")
        assert len(results) >= 2
        ids = {u.id for u in results}
        assert u1.id in ids
        assert u2.id in ids

    def test_returns_empty_for_nonexistent_email(self, db):
        results = find_users_by_email(db, "nonexistent@example.com")
        assert results == []


class TestGetUserLastActivity:
    def test_returns_none_for_inactive_user(self, db, make_user):
        user = make_user()
        result = get_user_last_activity(db, user.id)
        assert result is None

    def test_returns_latest_tlog_timestamp(self, db, user_with_logs):
        user, _, log = user_with_logs
        result = get_user_last_activity(db, user.id)
        assert result is not None


class TestGetUserActivityCounts:
    def test_returns_zero_counts_for_new_user(self, db, make_user):
        user = make_user()
        counts = get_user_activity_counts(db, user.id)
        assert counts["logs"] == 0
        assert counts["photos"] == 0
        assert counts["photo_votes"] == 0

    def test_counts_logs(self, db, user_with_logs):
        user, _, _ = user_with_logs
        counts = get_user_activity_counts(db, user.id)
        assert counts["logs"] == 1


class TestGetEmailDuplicatesSummary:
    def test_finds_duplicate_emails(self, db, two_users):
        results = get_email_duplicates_summary(db)
        emails = [r[0] for r in results]
        assert "dup@example.com" in emails

    def test_filter_by_email(self, db, two_users):
        results = get_email_duplicates_summary(db, email_filter="dup@example.com")
        assert len(results) == 1
        assert results[0][0] == "dup@example.com"

    def test_no_duplicates_for_unique_emails(self, db, make_user):
        make_user(email="unique1@example.com")
        results = get_email_duplicates_summary(db, email_filter="unique1@example.com")
        assert results == []


class TestCountRecordsForUser:
    def test_returns_zero_for_user_without_records(self, db, make_user):
        user = make_user()
        counts = count_records_for_user(db, user.id)
        assert counts["tlog"] == 0
        assert counts["tphoto"] == 0
        assert counts["tphotovote"] == 0

    def test_counts_tlog_records(self, db, user_with_logs):
        user, _, _ = user_with_logs
        counts = count_records_for_user(db, user.id)
        assert counts["tlog"] == 1


class TestMergeUsersAdmin:
    def test_dry_run_returns_preview(self, db, two_users):
        target, source = two_users
        result = merge_users_admin(db, target.id, source.id, dry_run=True)
        assert result["dry_run"] is True
        assert result["target_user"]["id"] == target.id
        assert result["source_user"]["id"] == source.id
        assert "estimated_records" in result

    def test_raises_for_nonexistent_target(self, db, make_user):
        source = make_user()
        with pytest.raises(ValueError, match="Target user"):
            merge_users_admin(db, 999999, source.id)

    def test_raises_for_nonexistent_source(self, db, make_user):
        target = make_user()
        with pytest.raises(ValueError, match="Source user"):
            merge_users_admin(db, target.id, 999999)

    def test_raises_for_same_user(self, db, make_user):
        user = make_user()
        with pytest.raises(ValueError, match="different"):
            merge_users_admin(db, user.id, user.id)

    def test_execute_merge_moves_logs(self, db, make_user, make_trig):
        target = make_user(name="target_merge")
        source = make_user(name="source_merge")
        source_id = source.id
        trig = make_trig()

        log = TLog(
            trig_id=trig.id,
            user_id=source.id,
            date=date(2024, 3, 1),
            time=time(12, 0),
            osgb_eastings=100000,
            osgb_northings=200000,
            osgb_gridref="TQ 00000 00000",
            fb_number="",
            condition="G",
            comment="Merge test",
            score=5,
            ip_addr="127.0.0.1",
            source="W",
            upd_timestamp=datetime(2024, 3, 1, 12, 0),
        )
        db.add(log)
        db.commit()

        result = merge_users_admin(db, target.id, source_id, dry_run=False)
        assert result["success"] is True
        assert result["updated_records"]["tlog"] == 1

        remaining_source = db.query(User).filter(User.id == source_id).first()
        assert remaining_source is None

    def test_execute_merge_copies_profile_fields(self, db, make_user):
        target = make_user(name="tgt_profile", firstname="", surname="", about="")
        source = make_user(
            name="src_profile",
            firstname="Alice",
            surname="Smith",
            about="Keen walker",
        )

        result = merge_users_admin(db, target.id, source.id, dry_run=False)
        assert result["profile_updated"] is True

        db.refresh(target)
        assert target.firstname == "Alice"
        assert target.surname == "Smith"

    def test_dry_run_shows_auth0_will_update(self, db, make_user):
        target = make_user(name="tgt_auth", auth0_user_id=None)
        source = make_user(name="src_auth", auth0_user_id="auth0|12345")

        result = merge_users_admin(db, target.id, source.id, dry_run=True)
        assert result["auth0_will_update"] is True
