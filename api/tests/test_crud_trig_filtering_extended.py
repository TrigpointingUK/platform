"""
Tests for extended trig CRUD filtering operations.

Tests the historic_use, current_use, conditions, and logged_conditions
filtering functionality in list_trigs_filtered and count_trigs_filtered.
"""

import uuid
from datetime import date, time
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from api.crud.trig import (
    count_trigs_filtered,
    list_trigs_filtered,
)
from api.models.trig import Trig
from api.models.user import TLog, User


@pytest.fixture
def seed_trigs_with_attributes(db: Session):
    """Seed trigs with various historic_use, current_use, and condition values."""
    # Generate unique base ID to avoid conflicts
    base_id = abs(hash(uuid.uuid4().hex[:8])) % 20000 + 10000

    # Create trigs with different attributes
    trigs = []
    test_data = [
        {
            "name": "Primary Passive",
            "historic_use": "Primary",
            "current_use": "Passive station",
            "condition": "G",
        },
        {
            "name": "Secondary GPS",
            "historic_use": "Secondary",
            "current_use": "Active station",
            "condition": "G",
        },
        {
            "name": "Primary None",
            "historic_use": "Primary",
            "current_use": "none",
            "condition": "R",
        },
        {
            "name": "Tertiary Passive",
            "historic_use": "Tertiary",
            "current_use": "Passive station",
            "condition": "N",
        },
        {
            "name": "Secondary None",
            "historic_use": "Secondary",
            "current_use": "none",
            "condition": "P",
        },
    ]

    for i, data in enumerate(test_data):
        trig = Trig(
            waypoint=f"TE{base_id + i}"[:8],
            name=data["name"],
            fb_number=f"FB{base_id + i}",
            stn_number=f"STN{base_id + i}",
            status_id=10,
            user_added=0,
            current_use=data["current_use"],
            historic_use=data["historic_use"],
            wgs_lat=Decimal("51.5") + Decimal(str(i * 0.01)),
            wgs_long=Decimal("-0.1") + Decimal(str(i * 0.01)),
            wgs_height=100 + i * 10,
            osgb_eastings=530000 + i * 1000,
            osgb_northings=180000 + i * 1000,
            osgb_gridref=f"TQ {30000 + i * 1000} 80000",
            osgb_height=95 + i * 10,
            condition=data["condition"],
            town="Westminster",
            permission_ind="Y",
            needs_attention=0,
            attention_comment="",
            crt_date=date(2023, 1, 1),
            crt_time=time(12, 0, 0),
            crt_ip_addr="127.0.0.1",
        )
        trigs.append(trig)

    db.add_all(trigs)
    db.flush()

    return {
        "trigs": trigs,
        "base_id": base_id,
    }


# =============================================================================
# Historic Use Filtering Tests
# =============================================================================


class TestListTrigsFilteredByHistoricUse:
    """Tests for list_trigs_filtered with historic_use parameter."""

    def test_filters_by_single_historic_use(
        self, db: Session, seed_trigs_with_attributes
    ):
        """Filters trigs by single historic use value."""
        data = seed_trigs_with_attributes

        result = list_trigs_filtered(db, historic_use=["Primary"], limit=100)

        # Should include trigs with historic_use = "Primary"
        result_ids = [t.id for t in result]
        primary_trig_ids = [t.id for t in data["trigs"] if t.historic_use == "Primary"]

        for pid in primary_trig_ids:
            assert pid in result_ids

    def test_filters_by_multiple_historic_use(
        self, db: Session, seed_trigs_with_attributes
    ):
        """Filters trigs by multiple historic use values."""
        data = seed_trigs_with_attributes

        result = list_trigs_filtered(
            db, historic_use=["Primary", "Secondary"], limit=100
        )

        # Should include trigs with historic_use in ["Primary", "Secondary"]
        result_ids = [t.id for t in result]
        expected_trig_ids = [
            t.id for t in data["trigs"] if t.historic_use in ["Primary", "Secondary"]
        ]

        for tid in expected_trig_ids:
            assert tid in result_ids

    def test_unknown_historic_use_returns_empty(
        self, db: Session, seed_trigs_with_attributes
    ):
        """Unknown historic use value returns empty result."""
        result = list_trigs_filtered(db, historic_use=["NONEXISTENT_USE"], limit=100)

        assert len(result) == 0


# =============================================================================
# Current Use Filtering Tests
# =============================================================================


class TestListTrigsFilteredByCurrentUse:
    """Tests for list_trigs_filtered with current_use parameter."""

    def test_filters_by_single_current_use(
        self, db: Session, seed_trigs_with_attributes
    ):
        """Filters trigs by single current use value."""
        data = seed_trigs_with_attributes

        result = list_trigs_filtered(db, current_use=["Passive station"], limit=100)

        # Should include trigs with current_use = "Passive station"
        result_ids = [t.id for t in result]
        passive_trig_ids = [
            t.id for t in data["trigs"] if t.current_use == "Passive station"
        ]

        for pid in passive_trig_ids:
            assert pid in result_ids

    def test_filters_by_multiple_current_use(
        self, db: Session, seed_trigs_with_attributes
    ):
        """Filters trigs by multiple current use values."""
        data = seed_trigs_with_attributes

        result = list_trigs_filtered(
            db, current_use=["Passive station", "Active station"], limit=100
        )

        # Should include trigs with current_use in ["Passive station", "Active station"]
        result_ids = [t.id for t in result]
        expected_trig_ids = [
            t.id
            for t in data["trigs"]
            if t.current_use in ["Passive station", "Active station"]
        ]

        for tid in expected_trig_ids:
            assert tid in result_ids


# =============================================================================
# Condition Filtering Tests
# =============================================================================


class TestListTrigsFilteredByConditions:
    """Tests for list_trigs_filtered with conditions parameter."""

    def test_filters_by_single_condition(self, db: Session, seed_trigs_with_attributes):
        """Filters trigs by single condition code."""
        data = seed_trigs_with_attributes

        result = list_trigs_filtered(db, conditions=["G"], limit=100)

        # Should include trigs with condition = "G"
        result_ids = [t.id for t in result]
        good_trig_ids = [t.id for t in data["trigs"] if t.condition == "G"]

        for pid in good_trig_ids:
            assert pid in result_ids

    def test_filters_by_multiple_conditions(
        self, db: Session, seed_trigs_with_attributes
    ):
        """Filters trigs by multiple condition codes."""
        data = seed_trigs_with_attributes

        result = list_trigs_filtered(db, conditions=["G", "R"], limit=100)

        # Should include trigs with condition in ["G", "R"]
        result_ids = [t.id for t in result]
        expected_trig_ids = [t.id for t in data["trigs"] if t.condition in ["G", "R"]]

        for tid in expected_trig_ids:
            assert tid in result_ids

    def test_unknown_condition_returns_empty(
        self, db: Session, seed_trigs_with_attributes
    ):
        """Unknown condition code returns empty result."""
        result = list_trigs_filtered(db, conditions=["NONEXISTENT"], limit=100)

        assert len(result) == 0


# =============================================================================
# Count Filtering Tests
# =============================================================================


class TestCountTrigsFilteredExtended:
    """Tests for count_trigs_filtered with new filters."""

    def test_count_historic_use_matches_list(
        self, db: Session, seed_trigs_with_attributes
    ):
        """Count matches the number of items from list query for historic_use."""
        list_result = list_trigs_filtered(db, historic_use=["Primary"], limit=1000)
        count_result = count_trigs_filtered(db, historic_use=["Primary"])

        assert count_result == len(list_result)

    def test_count_current_use_matches_list(
        self, db: Session, seed_trigs_with_attributes
    ):
        """Count matches the number of items from list query for current_use."""
        list_result = list_trigs_filtered(
            db, current_use=["Passive station"], limit=1000
        )
        count_result = count_trigs_filtered(db, current_use=["Passive station"])

        assert count_result == len(list_result)

    def test_count_conditions_matches_list(
        self, db: Session, seed_trigs_with_attributes
    ):
        """Count matches the number of items from list query for conditions."""
        list_result = list_trigs_filtered(db, conditions=["G"], limit=1000)
        count_result = count_trigs_filtered(db, conditions=["G"])

        assert count_result == len(list_result)


# =============================================================================
# Logged Conditions Filtering Tests
# =============================================================================


@pytest.fixture
def seed_user_with_varied_logs(db: Session, seed_trigs_with_attributes):
    """Seed a user with log entries with different conditions."""
    data = seed_trigs_with_attributes
    base_id = data["base_id"]

    # Create a test user
    user = User(
        name=f"test_user_lc_{base_id}",
        email=f"test_lc_{base_id}@example.com",
        cryptpw="",
        email_valid="Y",
        public_ind="Y",
    )
    db.add(user)
    db.flush()

    # Create logs with different conditions (single-char codes)
    trigs = data["trigs"]
    logs = []
    log_conditions = ["G", "G", "R", "N", "P"]  # Different conditions for each log

    for i, (trig, log_cond) in enumerate(zip(trigs, log_conditions)):
        log = TLog(
            trig_id=trig.id,
            user_id=user.id,
            date=date(2024, 1, i + 1),
            time=time(12, 0, 0),
            comment=f"Test log {i + 1}",
            condition=log_cond,
            score=5,
        )
        logs.append(log)

    db.add_all(logs)
    db.flush()

    return {
        **data,
        "user": user,
        "logs": logs,
        "log_conditions": log_conditions,
    }


class TestListTrigsFilteredByLoggedConditions:
    """Tests for list_trigs_filtered with logged_conditions parameter."""

    def test_filters_by_logged_condition(self, db: Session, seed_user_with_varied_logs):
        """Filters trigs by logged condition when combined with only_found_by_user_id."""
        data = seed_user_with_varied_logs
        user_id = data["user"].id

        # Get trigs logged with "G" condition
        result = list_trigs_filtered(
            db,
            only_found_by_user_id=user_id,
            logged_conditions=["G"],
            limit=100,
        )

        # Should return exactly the trigs logged with condition "G"
        expected_count = data["log_conditions"].count("G")
        assert len(result) == expected_count

    def test_filters_by_multiple_logged_conditions(
        self, db: Session, seed_user_with_varied_logs
    ):
        """Filters trigs by multiple logged conditions."""
        data = seed_user_with_varied_logs
        user_id = data["user"].id

        # Get trigs logged with "G" or "R" conditions
        result = list_trigs_filtered(
            db,
            only_found_by_user_id=user_id,
            logged_conditions=["G", "R"],
            limit=100,
        )

        # Should return trigs logged with either condition
        expected_count = data["log_conditions"].count("G") + data[
            "log_conditions"
        ].count("R")
        assert len(result) == expected_count

    def test_logged_conditions_requires_user_filter(
        self, db: Session, seed_user_with_varied_logs  # noqa: ARG002 - fixture needed
    ):
        """logged_conditions without only_found_by_user_id returns all trigs."""
        # Without user filter, logged_conditions has no effect
        result_with_filter = list_trigs_filtered(
            db, logged_conditions=["G"], limit=1000
        )
        result_without_filter = list_trigs_filtered(db, limit=1000)

        # Should return same results
        assert len(result_with_filter) == len(result_without_filter)
