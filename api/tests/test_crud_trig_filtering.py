"""
Tests for trig CRUD filtering operations.

Tests the category_codes, type_codes, and user log filtering functionality
in list_trigs_filtered and count_trigs_filtered.
"""

import uuid
from datetime import date, time
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from api.crud.trig import (
    _get_type_ids_for_categories,
    _get_type_ids_for_codes,
    count_trigs_filtered,
    list_trigs_filtered,
)
from api.models.trig import Trig
from api.models.trig_type import TrigCategory, TrigType
from api.models.user import TLog, User


@pytest.fixture
def seed_trig_types(db: Session):
    """Seed trig_category and trig_type tables for testing.

    Creates two categories (PILLAR and FBM) with types in each.
    Uses unique IDs based on UUID to avoid conflicts with parallel tests.
    """
    # Generate unique base ID to avoid conflicts
    # sort_order is SmallInteger (max 32767), so use smaller range
    base_id = abs(hash(uuid.uuid4().hex[:8])) % 20000 + 10000

    # Create categories
    pillar_category = TrigCategory(
        code=f"PILLAR_{base_id}",
        name="Pillar",
        description="Trig pillars",
        sort_order=1,
    )
    fbm_category = TrigCategory(
        code=f"FBM_{base_id}",
        name="FBM",
        description="Fundamental benchmark",
        sort_order=2,
    )
    db.add_all([pillar_category, fbm_category])
    db.flush()

    # Create types within each category
    hotine_type = TrigType(
        category_id=pillar_category.id,
        code=f"HOTINE_{base_id}",
        name="Hotine Pillar",
        description="Standard Hotine pillar",
        sort_order=1,
    )
    vanessa_type = TrigType(
        category_id=pillar_category.id,
        code=f"VANESSA_{base_id}",
        name="Vanessa Pillar",
        description="Vanessa style pillar",
        sort_order=2,
    )
    fbm_type = TrigType(
        category_id=fbm_category.id,
        code=f"FBM_MARK_{base_id}",
        name="Flush Bracket",
        description="Fundamental benchmark",
        sort_order=1,
    )
    db.add_all([hotine_type, vanessa_type, fbm_type])
    db.flush()

    return {
        "pillar_category": pillar_category,
        "fbm_category": fbm_category,
        "hotine_type": hotine_type,
        "vanessa_type": vanessa_type,
        "fbm_type": fbm_type,
        "base_id": base_id,
    }


@pytest.fixture
def seed_trigs_with_types(db: Session, seed_trig_types):
    """Seed trigs with type_id set to test filtering."""
    types = seed_trig_types
    base_id = types["base_id"]

    # Create trigs with different types
    trigs = []
    for i, (name, type_obj) in enumerate(
        [
            ("Hotine Trig 1", types["hotine_type"]),
            ("Hotine Trig 2", types["hotine_type"]),
            ("Vanessa Trig 1", types["vanessa_type"]),
            ("FBM Trig 1", types["fbm_type"]),
            ("FBM Trig 2", types["fbm_type"]),
        ]
    ):
        trig = Trig(
            waypoint=f"T{base_id + i}"[:8],
            name=name,
            fb_number=f"FB{base_id + i}",
            stn_number=f"STN{base_id + i}",
            status_id=10,
            user_added=0,
            type_id=type_obj.id,
            current_use="Passive station",
            historic_use="Primary",
            physical_type="Pillar" if "Pillar" in type_obj.name else "FBM",
            wgs_lat=Decimal("51.5") + Decimal(str(i * 0.01)),
            wgs_long=Decimal("-0.1") + Decimal(str(i * 0.01)),
            wgs_height=100,
            osgb_eastings=530000 + i * 1000,
            osgb_northings=180000 + i * 1000,
            osgb_gridref=f"TQ {30000 + i * 1000} 80000",
            osgb_height=95,
            condition="G",
            county="London",
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
        **types,
        "trigs": trigs,
    }


# =============================================================================
# Group 1: Basic Type/Group Filtering Tests
# =============================================================================


class TestGetTypeIdsForCodes:
    """Tests for _get_type_ids_for_codes helper function."""

    def test_returns_correct_type_ids(self, db: Session, seed_trig_types):
        """Helper returns correct type IDs for given codes."""
        types = seed_trig_types
        hotine_code = types["hotine_type"].code

        result = _get_type_ids_for_codes(db, [hotine_code])

        assert types["hotine_type"].id in result
        assert len(result) == 1

    def test_returns_multiple_type_ids(self, db: Session, seed_trig_types):
        """Helper returns multiple type IDs when multiple codes given."""
        types = seed_trig_types
        codes = [types["hotine_type"].code, types["fbm_type"].code]

        result = _get_type_ids_for_codes(db, codes)

        assert types["hotine_type"].id in result
        assert types["fbm_type"].id in result
        assert len(result) == 2

    def test_returns_empty_for_unknown_codes(self, db: Session, seed_trig_types):
        """Returns empty list for unknown type codes."""
        result = _get_type_ids_for_codes(db, ["NONEXISTENT_CODE_XYZ"])

        assert result == []

    def test_case_insensitive(self, db: Session, seed_trig_types):
        """Type code matching is case-insensitive."""
        types = seed_trig_types
        hotine_code = types["hotine_type"].code.lower()

        result = _get_type_ids_for_codes(db, [hotine_code])

        assert types["hotine_type"].id in result


class TestGetTypeIdsForCategories:
    """Tests for _get_type_ids_for_categories helper function."""

    def test_returns_all_types_in_category(self, db: Session, seed_trig_types):
        """Helper returns all type IDs in a category."""
        types = seed_trig_types
        pillar_code = types["pillar_category"].code

        result = _get_type_ids_for_categories(db, [pillar_code])

        # Pillar category has hotine and vanessa types
        assert types["hotine_type"].id in result
        assert types["vanessa_type"].id in result
        # FBM type should not be included
        assert types["fbm_type"].id not in result

    def test_returns_types_from_multiple_categories(self, db: Session, seed_trig_types):
        """Helper returns type IDs from multiple categories."""
        types = seed_trig_types
        codes = [types["pillar_category"].code, types["fbm_category"].code]

        result = _get_type_ids_for_categories(db, codes)

        assert types["hotine_type"].id in result
        assert types["vanessa_type"].id in result
        assert types["fbm_type"].id in result
        assert len(result) == 3

    def test_returns_empty_for_unknown_categories(self, db: Session, seed_trig_types):
        """Returns empty list for unknown category codes."""
        result = _get_type_ids_for_categories(db, ["NONEXISTENT_CATEGORY_XYZ"])

        assert result == []

    def test_case_insensitive(self, db: Session, seed_trig_types):
        """Category code matching is case-insensitive."""
        types = seed_trig_types
        pillar_code = types["pillar_category"].code.lower()

        result = _get_type_ids_for_categories(db, [pillar_code])

        assert types["hotine_type"].id in result
        assert types["vanessa_type"].id in result


class TestListTrigsFilteredByCategory:
    """Tests for list_trigs_filtered with category_codes parameter."""

    def test_filters_by_single_category(self, db: Session, seed_trigs_with_types):
        """Filters trigs by single category code."""
        data = seed_trigs_with_types
        pillar_code = data["pillar_category"].code

        result = list_trigs_filtered(db, category_codes=[pillar_code], limit=100)

        # Should include trigs with hotine and vanessa types (pillar category)
        trig_ids = [t.id for t in result]
        pillar_trig_ids = [
            t.id
            for t in data["trigs"]
            if t.type_id in [data["hotine_type"].id, data["vanessa_type"].id]
        ]

        for pid in pillar_trig_ids:
            assert pid in trig_ids

    def test_filters_by_multiple_categories(self, db: Session, seed_trigs_with_types):
        """Filters trigs by multiple category codes."""
        data = seed_trigs_with_types
        codes = [data["pillar_category"].code, data["fbm_category"].code]

        result = list_trigs_filtered(db, category_codes=codes, limit=100)

        # Should include all 5 seeded trigs
        trig_ids = [t.id for t in result]
        for trig in data["trigs"]:
            assert trig.id in trig_ids

    def test_unknown_category_returns_empty(self, db: Session, seed_trigs_with_types):
        """Unknown category code returns empty result."""
        result = list_trigs_filtered(
            db, category_codes=["NONEXISTENT_CATEGORY_XYZ"], limit=100
        )

        assert len(result) == 0


class TestListTrigsFilteredByTypeCode:
    """Tests for list_trigs_filtered with type_codes parameter."""

    def test_filters_by_single_type(self, db: Session, seed_trigs_with_types):
        """Filters trigs by single type code."""
        data = seed_trigs_with_types
        hotine_code = data["hotine_type"].code

        result = list_trigs_filtered(db, type_codes=[hotine_code], limit=100)

        # Should only include hotine trigs
        for trig in result:
            assert trig.type_id == data["hotine_type"].id

    def test_filters_by_multiple_types(self, db: Session, seed_trigs_with_types):
        """Filters trigs by multiple type codes."""
        data = seed_trigs_with_types
        codes = [data["hotine_type"].code, data["vanessa_type"].code]

        result = list_trigs_filtered(db, type_codes=codes, limit=100)

        # Should include hotine and vanessa trigs
        for trig in result:
            assert trig.type_id in [data["hotine_type"].id, data["vanessa_type"].id]


class TestCountTrigsFilteredByCategory:
    """Tests for count_trigs_filtered with category_codes parameter."""

    def test_count_matches_list(self, db: Session, seed_trigs_with_types):
        """Count matches the number of items from list query."""
        data = seed_trigs_with_types
        pillar_code = data["pillar_category"].code

        list_result = list_trigs_filtered(db, category_codes=[pillar_code], limit=100)
        count_result = count_trigs_filtered(db, category_codes=[pillar_code])

        # Count should be at least the number we seeded (may include other test data)
        assert count_result >= len(
            [
                t
                for t in data["trigs"]
                if t.type_id in [data["hotine_type"].id, data["vanessa_type"].id]
            ]
        )
        assert count_result == len(list_result)

    def test_unknown_category_returns_zero(self, db: Session, seed_trigs_with_types):
        """Unknown category code returns zero count."""
        count = count_trigs_filtered(db, category_codes=["NONEXISTENT_CATEGORY_XYZ"])

        assert count == 0


# =============================================================================
# Group 2: User Log Filtering Tests
# =============================================================================


@pytest.fixture
def seed_user_with_logs(db: Session, seed_trigs_with_types):
    """Seed a user with log entries for some trigs."""
    data = seed_trigs_with_types
    base_id = data["base_id"]

    # Create a test user
    user = User(
        name=f"test_user_{base_id}",
        email=f"test_{base_id}@example.com",
        cryptpw="",
        email_valid="Y",
        public_ind="Y",
    )
    db.add(user)
    db.flush()

    # Create logs for first 2 trigs
    logged_trigs = data["trigs"][:2]
    logs = []
    for i, trig in enumerate(logged_trigs):
        log = TLog(
            trig_id=trig.id,
            user_id=user.id,
            date=date(2024, 1, i + 1),
            time=time(12, 0, 0),
            comment=f"Test log {i + 1}",
            condition="G",
            score=5,
        )
        logs.append(log)

    db.add_all(logs)
    db.flush()

    return {
        **data,
        "user": user,
        "logs": logs,
        "logged_trigs": logged_trigs,
        "unlogged_trigs": data["trigs"][2:],
    }


class TestListTrigsExcludeFoundByUser:
    """Tests for list_trigs_filtered with exclude_found_by_user_id parameter."""

    def test_excludes_logged_trigs(self, db: Session, seed_user_with_logs):
        """NOT EXISTS filter excludes trigs the user has logged."""
        data = seed_user_with_logs
        user_id = data["user"].id
        pillar_code = data["pillar_category"].code

        # Filter by our seeded category to isolate test data
        result = list_trigs_filtered(
            db,
            exclude_found_by_user_id=user_id,
            category_codes=[pillar_code],
            limit=1000,
        )

        result_ids = [t.id for t in result]

        # Logged trigs should NOT be in result
        for trig in data["logged_trigs"]:
            assert trig.id not in result_ids

        # At least some unlogged trigs should be in results
        unlogged_ids = [t.id for t in data["unlogged_trigs"]]
        found_unlogged = [tid for tid in unlogged_ids if tid in result_ids]
        assert len(found_unlogged) > 0, "No unlogged trigs found in filtered results"

    def test_returns_all_if_user_has_no_logs(self, db: Session, seed_trigs_with_types):
        """Returns all trigs if user has no log entries."""
        data = seed_trigs_with_types
        pillar_code = data["pillar_category"].code

        # Create a user with no logs
        user = User(
            name=f"nologs_user_{data['base_id']}",
            email=f"nologs_{data['base_id']}@example.com",
            cryptpw="",
            email_valid="Y",
            public_ind="Y",
        )
        db.add(user)
        db.flush()

        # Get all trigs (no exclusion) - filter to our seeded category
        all_trigs = list_trigs_filtered(db, category_codes=[pillar_code], limit=1000)

        # Get trigs with exclusion for user with no logs
        filtered_trigs = list_trigs_filtered(
            db,
            exclude_found_by_user_id=int(user.id),
            category_codes=[pillar_code],
            limit=1000,
        )

        # Should return same count (user has no logs to exclude)
        assert len(filtered_trigs) == len(all_trigs)


class TestListTrigsOnlyFoundByUser:
    """Tests for list_trigs_filtered with only_found_by_user_id parameter."""

    def test_returns_only_logged_trigs(self, db: Session, seed_user_with_logs):
        """EXISTS filter returns only trigs the user has logged."""
        data = seed_user_with_logs
        user_id = data["user"].id

        result = list_trigs_filtered(db, only_found_by_user_id=user_id, limit=1000)

        result_ids = [t.id for t in result]
        logged_ids = [t.id for t in data["logged_trigs"]]

        # Result should only contain logged trigs
        for rid in result_ids:
            assert rid in logged_ids

        # All logged trigs should be in result
        for lid in logged_ids:
            assert lid in result_ids

    def test_returns_empty_if_user_has_no_logs(
        self, db: Session, seed_trigs_with_types
    ):
        """Returns empty if user has no log entries."""
        data = seed_trigs_with_types

        # Create a user with no logs
        user = User(
            name=f"nologs2_user_{data['base_id']}",
            email=f"nologs2_{data['base_id']}@example.com",
            cryptpw="",
            email_valid="Y",
            public_ind="Y",
        )
        db.add(user)
        db.flush()

        result = list_trigs_filtered(db, only_found_by_user_id=int(user.id), limit=1000)

        assert len(result) == 0


class TestCountTrigsExcludeFoundByUser:
    """Tests for count_trigs_filtered with exclude_found_by_user_id parameter."""

    def test_count_respects_exclude_filter(self, db: Session, seed_user_with_logs):
        """Count respects exclude_found_by_user_id filter."""
        data = seed_user_with_logs
        user_id = data["user"].id
        pillar_code = data["pillar_category"].code

        # Get counts - filter to our seeded category to isolate test data
        all_count = count_trigs_filtered(db, category_codes=[pillar_code])
        filtered_count = count_trigs_filtered(
            db, exclude_found_by_user_id=user_id, category_codes=[pillar_code]
        )

        # Filtered count should be less by number of logged trigs
        expected_diff = len(data["logged_trigs"])
        assert all_count - filtered_count == expected_diff

    def test_count_matches_list(self, db: Session, seed_user_with_logs):
        """Count matches the list result for exclude_found filter."""
        data = seed_user_with_logs
        user_id = data["user"].id
        pillar_code = data["pillar_category"].code

        # Filter to our seeded category to isolate test data
        list_result = list_trigs_filtered(
            db,
            exclude_found_by_user_id=user_id,
            category_codes=[pillar_code],
            limit=10000,
        )
        count_result = count_trigs_filtered(
            db, exclude_found_by_user_id=user_id, category_codes=[pillar_code]
        )

        assert count_result == len(list_result)
