"""
Tests for crud/status.py — status CRUD operations.
"""

from api.crud.status import (
    create_status,
    delete_status,
    get_all_statuses,
    get_status_by_id,
    get_status_name_by_id,
    get_status_usage_count,
    update_status,
)


class TestGetStatusNameById:
    def test_returns_name_for_seeded_status(self, db):
        name = get_status_name_by_id(db, 1)
        assert name.strip() == "ACTIVE"

    def test_returns_none_for_nonexistent(self, db):
        name = get_status_name_by_id(db, 999999)
        assert name is None


class TestGetAllStatuses:
    def test_returns_seeded_statuses(self, db):
        statuses = get_all_statuses(db)
        assert len(statuses) >= 2
        ids = {s.id for s in statuses}
        assert 0 in ids
        assert 1 in ids


class TestGetStatusById:
    def test_returns_status(self, db):
        status = get_status_by_id(db, 1)
        assert status is not None
        assert status.name.strip() == "ACTIVE"

    def test_returns_none_for_nonexistent(self, db):
        status = get_status_by_id(db, 999999)
        assert status is None


class TestCreateStatus:
    def test_creates_new_status(self, db):
        status = create_status(db, 900, "NEWSTAT", "New Status", "New limit desc")
        assert status.id == 900
        assert status.name.strip() == "NEWSTAT"
        assert status.descr.strip() == "New Status"

    def test_strips_whitespace(self, db):
        status = create_status(db, 901, "  TRIMMED  ", "  desc  ", "  limit  ")
        assert status.name.strip() == "TRIMMED"
        assert status.descr.strip() == "desc"
        assert status.limit_descr.strip() == "limit"


class TestUpdateStatus:
    def test_updates_existing_status(self, db):
        create_status(db, 902, "UPDT", "To Update", "Limit")
        updated = update_status(db, 902, name="UPDATED")
        assert updated is not None
        assert updated.name.strip() == "UPDATED"
        assert updated.descr.strip() == "To Update"

    def test_returns_none_for_nonexistent(self, db):
        result = update_status(db, 999999, name="X")
        assert result is None

    def test_partial_update(self, db):
        create_status(db, 903, "PARTIAL", "Orig Desc", "Orig Limit")
        updated = update_status(db, 903, descr="New Desc")
        assert updated.name.strip() == "PARTIAL"
        assert updated.descr.strip() == "New Desc"
        assert updated.limit_descr.strip() == "Orig Limit"


class TestDeleteStatus:
    def test_deletes_existing_status(self, db):
        create_status(db, 904, "DELME", "Delete Me", "Limit")
        assert delete_status(db, 904) is True
        assert get_status_by_id(db, 904) is None

    def test_returns_false_for_nonexistent(self, db):
        assert delete_status(db, 999999) is False


class TestGetStatusUsageCount:
    def test_returns_zero_for_unused_status(self, db):
        create_status(db, 905, "UNUSED", "Unused", "Limit")
        assert get_status_usage_count(db, 905) == 0

    def test_returns_count_for_used_status(self, db, make_trig):
        make_trig(status_id=1)
        count = get_status_usage_count(db, 1)
        assert count >= 1
