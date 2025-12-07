"""
Tests for trig condition update when tlog is created or updated.

When a tlog is created or updated, if the trig.condition is in a
"pending/unknown" state ('P', 'U', 'N', 'Z', '', null) and the tlog.condition
is a "known" state (not in 'P', 'Q', 'U', 'N', 'Z', '', null), then the
trig.condition should be updated to match the tlog.condition.

Note: The trig.condition column has a NOT NULL constraint in the database,
so null is never a valid value in practice. However, our code handles it
defensively. The empty string case is also unlikely in PostgreSQL due to
CHAR(1) type, but the logic handles it.
"""

from datetime import date, time
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from api.crud.tlog import (
    TLOG_CONDITIONS_TO_SKIP,
    TRIG_CONDITIONS_TO_UPDATE,
    create_log,
    maybe_update_trig_condition,
    update_log,
)
from api.models.trig import Trig
from api.models.user import TLog


def create_test_trig(db: Session, condition: str) -> Trig:
    """Create a test trig with a specific condition."""
    import uuid

    waypoint = f"TP{uuid.uuid4().hex[:6]}"[:8]
    trig = Trig(
        waypoint=waypoint,
        name=f"Condition Test {waypoint}",
        status_id=10,
        user_added=0,
        current_use="Passive station",
        historic_use="Primary",
        physical_type="Pillar",
        wgs_lat=Decimal("51.50000"),
        wgs_long=Decimal("-0.12500"),
        wgs_height=100,
        osgb_eastings=530000,
        osgb_northings=180000,
        osgb_gridref="TQ 30000 80000",
        osgb_height=95,
        fb_number="S1234",
        stn_number=f"COND{waypoint}",
        permission_ind="Y",
        condition=condition,
        postcode="SW1A 1",
        county="London",
        town="Westminster",
        needs_attention=0,
        attention_comment="",
        crt_date=date(2023, 1, 1),
        crt_time=time(12, 0, 0),
        crt_user_id=1,
        crt_ip_addr="127.0.0.1",
    )
    db.add(trig)
    db.commit()
    db.refresh(trig)
    return trig


class TestMaybeUpdateTrigCondition:
    """Tests for the maybe_update_trig_condition helper function."""

    def test_updates_trig_when_conditions_met(self, db: Session):
        """Test that trig condition is updated when all conditions are met."""
        # Create a trig with 'P' (pending) condition
        trig = create_test_trig(db, "P")

        # Call maybe_update_trig_condition with a known condition
        result = maybe_update_trig_condition(
            db, trig_id=int(trig.id), tlog_condition="G"
        )
        db.commit()

        # Verify the update happened
        assert result is True
        db.refresh(trig)
        assert trig.condition == "G"

    @pytest.mark.parametrize("trig_condition", ["P", "U", "N", "Z"])
    def test_updates_from_pending_conditions(self, db: Session, trig_condition: str):
        """Test that trig condition is updated from all pending conditions.

        Note: Empty string is not tested because CHAR(1) in PostgreSQL
        will pad it to a space character, and the database has NOT NULL constraint.
        """
        trig = create_test_trig(db, trig_condition)

        result = maybe_update_trig_condition(
            db, trig_id=int(trig.id), tlog_condition="G"
        )
        db.commit()

        assert result is True
        db.refresh(trig)
        assert trig.condition == "G"

    def test_code_handles_null_condition_defensively(self, db: Session):
        """Test that the code handles null condition gracefully.

        Note: The trig.condition column has NOT NULL constraint, so this tests
        the defensive code path that would handle an unexpected null value.
        We can't actually insert a null, but we can test the logic handles it.
        """
        # Simply verify that None is in the set of conditions to update
        assert None in TRIG_CONDITIONS_TO_UPDATE

    @pytest.mark.parametrize("trig_condition", ["G", "D", "S", "R", "T", "C", "V", "X"])
    def test_does_not_update_known_conditions(self, db: Session, trig_condition: str):
        """Test that trig condition is NOT updated when already a known condition."""
        trig = create_test_trig(db, trig_condition)

        result = maybe_update_trig_condition(
            db, trig_id=int(trig.id), tlog_condition="D"
        )
        db.commit()

        # Should not update
        assert result is False
        db.refresh(trig)
        assert trig.condition == trig_condition

    @pytest.mark.parametrize("tlog_condition", ["P", "Q", "U", "N", "Z", ""])
    def test_does_not_update_with_pending_tlog_conditions(
        self, db: Session, tlog_condition: str
    ):
        """Test that trig condition is NOT updated when tlog condition is pending."""
        trig = create_test_trig(db, "P")

        result = maybe_update_trig_condition(
            db, trig_id=int(trig.id), tlog_condition=tlog_condition
        )
        db.commit()

        # Should not update
        assert result is False
        db.refresh(trig)
        assert trig.condition == "P"

    def test_does_not_update_with_null_tlog_condition(self, db: Session):
        """Test that trig condition is NOT updated when tlog condition is null."""
        trig = create_test_trig(db, "P")

        result = maybe_update_trig_condition(
            db, trig_id=int(trig.id), tlog_condition=None
        )
        db.commit()

        # Should not update
        assert result is False
        db.refresh(trig)
        assert trig.condition == "P"

    def test_does_not_update_nonexistent_trig(self, db: Session):
        """Test that function handles nonexistent trig gracefully."""
        result = maybe_update_trig_condition(db, trig_id=999999, tlog_condition="G")

        assert result is False


class TestCreateLogWithConditionUpdate:
    """Tests for create_log function with trig condition update."""

    def test_create_log_updates_trig_condition(self, db: Session, test_user):
        """Test that creating a log updates trig condition when appropriate."""
        # Create a trig with pending condition
        trig = create_test_trig(db, "P")

        # Create a log with a known condition
        log_values = {
            "date": date(2024, 1, 1),
            "time": time(12, 0, 0),
            "condition": "G",
            "comment": "Found in good condition",
            "fb_number": "",
            "score": 5,
            "source": "W",
            "ip_addr": "127.0.0.1",
        }

        log = create_log(
            db, trig_id=int(trig.id), user_id=int(test_user.id), values=log_values
        )

        # Verify log was created
        assert log.id is not None
        assert log.condition == "G"

        # Verify trig condition was updated
        db.refresh(trig)
        assert trig.condition == "G"

    def test_create_log_does_not_update_known_trig_condition(
        self, db: Session, test_user
    ):
        """Test that creating a log does NOT update trig with known condition."""
        # Create a trig with known condition
        trig = create_test_trig(db, "G")

        # Create a log with different condition
        log_values = {
            "date": date(2024, 1, 2),
            "time": time(12, 0, 0),
            "condition": "D",  # Destroyed
            "comment": "Now destroyed",
            "fb_number": "",
            "score": 1,
            "source": "W",
            "ip_addr": "127.0.0.1",
        }

        log = create_log(
            db, trig_id=int(trig.id), user_id=int(test_user.id), values=log_values
        )

        # Verify log was created
        assert log.id is not None
        assert log.condition == "D"

        # Verify trig condition was NOT updated
        db.refresh(trig)
        assert trig.condition == "G"


class TestUpdateLogWithConditionUpdate:
    """Tests for update_log function with trig condition update."""

    def test_update_log_updates_trig_condition(self, db: Session, test_user):
        """Test that updating a log condition updates trig condition when appropriate."""
        # Create a trig with pending condition
        trig = create_test_trig(db, "P")

        # Create a log with pending condition first
        log = TLog(
            trig_id=trig.id,
            user_id=test_user.id,
            date=date(2024, 1, 1),
            time=time(12, 0, 0),
            condition="U",  # Unknown initially
            comment="Initial log",
            fb_number="",
            score=0,
            source="W",
            ip_addr="127.0.0.1",
        )
        db.add(log)
        db.commit()
        db.refresh(log)

        # Now update the log with a known condition
        updated_log = update_log(db, log_id=int(log.id), updates={"condition": "G"})

        # Verify log was updated
        assert updated_log is not None
        assert updated_log.condition == "G"

        # Verify trig condition was updated
        db.refresh(trig)
        assert trig.condition == "G"

    def test_update_log_does_not_update_known_trig_condition(
        self, db: Session, test_user
    ):
        """Test that updating a log does NOT update trig with known condition."""
        # Create a trig with known condition
        trig = create_test_trig(db, "G")

        # Create a log
        log = TLog(
            trig_id=trig.id,
            user_id=test_user.id,
            date=date(2024, 1, 3),
            time=time(12, 0, 0),
            condition="G",
            comment="Initial log",
            fb_number="",
            score=5,
            source="W",
            ip_addr="127.0.0.1",
        )
        db.add(log)
        db.commit()
        db.refresh(log)

        # Update the log with a different condition
        updated_log = update_log(db, log_id=int(log.id), updates={"condition": "D"})

        # Verify log was updated
        assert updated_log is not None
        assert updated_log.condition == "D"

        # Verify trig condition was NOT updated
        db.refresh(trig)
        assert trig.condition == "G"

    def test_update_log_without_condition_does_not_affect_trig(
        self, db: Session, test_user
    ):
        """Test that updating a log without condition change doesn't affect trig."""
        # Create a trig with pending condition
        trig = create_test_trig(db, "P")

        # Create a log with known condition
        log = TLog(
            trig_id=trig.id,
            user_id=test_user.id,
            date=date(2024, 1, 4),
            time=time(12, 0, 0),
            condition="G",
            comment="Initial log",
            fb_number="",
            score=5,
            source="W",
            ip_addr="127.0.0.1",
        )
        db.add(log)
        db.commit()
        db.refresh(log)

        # Note: The trig condition should have been updated already when creating
        # the log manually (if we used create_log). But since we created directly,
        # the trig still has "P".

        # Update the log comment only
        updated_log = update_log(
            db, log_id=int(log.id), updates={"comment": "Updated comment"}
        )

        # Verify log was updated
        assert updated_log is not None
        assert updated_log.comment == "Updated comment"

        # Verify trig condition was NOT changed (still P since condition wasn't
        # part of the update)
        db.refresh(trig)
        assert trig.condition == "P"


class TestConditionConstants:
    """Tests for the condition constants."""

    def test_trig_conditions_to_update_contains_expected_values(self):
        """Verify TRIG_CONDITIONS_TO_UPDATE has the expected values."""
        expected = {"P", "U", "N", "Z", "", None}
        assert TRIG_CONDITIONS_TO_UPDATE == expected

    def test_tlog_conditions_to_skip_contains_expected_values(self):
        """Verify TLOG_CONDITIONS_TO_SKIP has the expected values."""
        expected = {"P", "Q", "U", "N", "Z", "", None}
        assert TLOG_CONDITIONS_TO_SKIP == expected

    def test_q_is_in_skip_but_not_in_update(self):
        """Verify Q is only in skip list, not update list.

        Q means "Not looked for" in tlog (a valid log state) but shouldn't
        be used to update trig condition.
        """
        assert "Q" in TLOG_CONDITIONS_TO_SKIP
        assert "Q" not in TRIG_CONDITIONS_TO_UPDATE
