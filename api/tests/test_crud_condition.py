"""
Tests for condition CRUD operations.

Tests the condition CRUD functions directly.
"""

import pytest
from sqlalchemy.orm import Session

from api.crud import condition as condition_crud
from api.models.condition import Condition


def _get_unique_sort_orders(db: Session, count: int = 2) -> list[int]:
    """Find unique sort_order values that don't exist in the database."""
    import random

    existing = {
        row[0] for row in db.query(Condition.sort_order).all() if row[0] is not None
    }

    attempts = 0
    while attempts < 100:
        base = random.randint(10000, 32000 - count)
        candidates = [base + i for i in range(count)]
        if not any(c in existing for c in candidates):
            return candidates
        attempts += 1

    return [32000 + i for i in range(count)]


def _get_unique_codes(db: Session, count: int = 3) -> list[str]:
    """Find unique single-letter codes that don't exist in the database."""
    existing = {row[0] for row in db.query(Condition.code).all()}
    available = [chr(i) for i in range(ord("Z"), ord("A") - 1, -1)]
    codes = [c for c in available if c not in existing][:count]
    if len(codes) < count:
        raise ValueError("Not enough available condition codes for testing")
    return codes


@pytest.fixture
def crud_test_conditions(db: Session):
    """Create test conditions for CRUD testing."""
    sort_orders = _get_unique_sort_orders(db, count=3)
    codes = _get_unique_codes(db, count=3)

    condition1 = Condition(
        code=codes[0],
        name=f"CRUD Test Condition {codes[0]}",
        description=f"Description for CRUD condition {codes[0]}",
        icon_file=f"c_crud_{codes[0].lower()}.png",
        trig_colour="green",
        log_colour="blue",
        similar_codes=codes[1],
        wiki_url=f"https://example.com/crud/{codes[0].lower()}",
        sort_order=sort_orders[0],
    )
    condition2 = Condition(
        code=codes[1],
        name=f"CRUD Test Condition {codes[1]}",
        description=None,
        icon_file=None,
        trig_colour=None,
        log_colour=None,
        similar_codes=None,
        wiki_url=None,
        sort_order=sort_orders[1],
    )

    db.add(condition1)
    db.add(condition2)
    db.commit()

    return {
        "condition1": condition1,
        "condition2": condition2,
        "codes": codes,
        "sort_orders": sort_orders,
    }


class TestGetConditionByCode:
    """Tests for get_condition_by_code."""

    def test_get_existing_condition(self, db: Session, crud_test_conditions):
        """Test retrieving an existing condition by code."""
        code = crud_test_conditions["codes"][0]
        result = condition_crud.get_condition_by_code(db, code)

        assert result is not None
        assert result.code == code
        assert result.name == f"CRUD Test Condition {code}"

    def test_get_nonexistent_condition(self, db: Session):
        """Test retrieving a non-existent condition returns None."""
        result = condition_crud.get_condition_by_code(db, "9")

        assert result is None

    def test_get_condition_case_sensitivity(self, db: Session, crud_test_conditions):
        """Test that codes are stored as uppercase."""
        code = crud_test_conditions["codes"][0]
        # Query with uppercase
        result = condition_crud.get_condition_by_code(db, code.upper())
        assert result is not None


class TestGetConditionNameByCode:
    """Tests for get_condition_name_by_code."""

    def test_get_name_existing(self, db: Session, crud_test_conditions):
        """Test retrieving name for existing condition."""
        code = crud_test_conditions["codes"][0]
        result = condition_crud.get_condition_name_by_code(db, code)

        assert result == f"CRUD Test Condition {code}"

    def test_get_name_nonexistent(self, db: Session):
        """Test retrieving name for non-existent condition returns None."""
        result = condition_crud.get_condition_name_by_code(db, "9")

        assert result is None


class TestGetAllConditions:
    """Tests for get_all_conditions."""

    def test_get_all_returns_list(self, db: Session, crud_test_conditions):
        """Test that get_all_conditions returns a list."""
        results = condition_crud.get_all_conditions(db)

        assert isinstance(results, list)
        assert len(results) >= 2  # At least our test conditions

    def test_get_all_ordered_by_sort_order(self, db: Session, crud_test_conditions):
        """Test that results are ordered by sort_order."""
        results = condition_crud.get_all_conditions(db)

        sort_orders = [c.sort_order for c in results]
        assert sort_orders == sorted(sort_orders)


class TestCreateCondition:
    """Tests for create_condition."""

    def test_create_with_all_fields(self, db: Session):
        """Test creating a condition with all fields."""
        codes = _get_unique_codes(db, count=1)
        code = codes[0]
        sort_orders = _get_unique_sort_orders(db, count=1)

        result = condition_crud.create_condition(
            db,
            code=code,
            name="Full Condition",
            sort_order=sort_orders[0],
            description="Full description",
            icon_file="c_full.png",
            trig_colour="green",
            log_colour="blue",
            similar_codes="XY",
            wiki_url="https://example.com/full",
        )

        assert result.code == code.upper()
        assert result.name == "Full Condition"
        assert result.sort_order == sort_orders[0]
        assert result.description == "Full description"
        assert result.icon_file == "c_full.png"
        assert result.trig_colour == "green"
        assert result.log_colour == "blue"
        assert result.similar_codes == "XY"
        assert result.wiki_url == "https://example.com/full"

    def test_create_with_minimal_fields(self, db: Session):
        """Test creating a condition with only required fields."""
        codes = _get_unique_codes(db, count=1)
        code = codes[0]
        sort_orders = _get_unique_sort_orders(db, count=1)

        result = condition_crud.create_condition(
            db,
            code=code,
            name="Minimal Condition",
            sort_order=sort_orders[0],
        )

        assert result.code == code.upper()
        assert result.name == "Minimal Condition"
        assert result.sort_order == sort_orders[0]
        assert result.description is None
        assert result.icon_file is None

    def test_create_strips_whitespace(self, db: Session):
        """Test that create_condition strips whitespace from fields."""
        codes = _get_unique_codes(db, count=1)
        code = codes[0]
        sort_orders = _get_unique_sort_orders(db, count=1)

        result = condition_crud.create_condition(
            db,
            code=f" {code} ",
            name="  Whitespace Name  ",
            sort_order=sort_orders[0],
            description="  Description with spaces  ",
        )

        assert result.code == code.upper()
        assert result.name == "Whitespace Name"
        assert result.description == "Description with spaces"

    def test_create_uppercases_code(self, db: Session):
        """Test that create_condition uppercases the code."""
        codes = _get_unique_codes(db, count=1)
        code = codes[0].lower()  # Use lowercase
        sort_orders = _get_unique_sort_orders(db, count=1)

        result = condition_crud.create_condition(
            db,
            code=code,
            name="Lowercase Code",
            sort_order=sort_orders[0],
        )

        assert result.code == code.upper()

    def test_create_uppercases_similar_codes(self, db: Session):
        """Test that create_condition uppercases similar_codes."""
        codes = _get_unique_codes(db, count=1)
        code = codes[0]
        sort_orders = _get_unique_sort_orders(db, count=1)

        result = condition_crud.create_condition(
            db,
            code=code,
            name="Similar Codes Test",
            sort_order=sort_orders[0],
            similar_codes="ab",
        )

        assert result.similar_codes == "AB"


class TestUpdateCondition:
    """Tests for update_condition."""

    def test_update_single_field(self, db: Session, crud_test_conditions):
        """Test updating a single field."""
        code = crud_test_conditions["codes"][0]

        result = condition_crud.update_condition(
            db,
            code=code,
            name="Updated Name Only",
        )

        assert result is not None
        assert result.name == "Updated Name Only"
        # Other fields unchanged
        assert result.description == f"Description for CRUD condition {code}"

    def test_update_multiple_fields(self, db: Session, crud_test_conditions):
        """Test updating multiple fields."""
        code = crud_test_conditions["codes"][0]

        result = condition_crud.update_condition(
            db,
            code=code,
            name="Multi Update Name",
            description="Multi Update Description",
            trig_colour="yellow",
        )

        assert result is not None
        assert result.name == "Multi Update Name"
        assert result.description == "Multi Update Description"
        assert result.trig_colour == "yellow"

    def test_update_to_null(self, db: Session, crud_test_conditions):
        """Test updating a field to empty string (treated as None)."""
        code = crud_test_conditions["codes"][0]

        result = condition_crud.update_condition(
            db,
            code=code,
            description="",  # Empty string
        )

        assert result is not None
        assert result.description is None

    def test_update_nonexistent(self, db: Session):
        """Test updating a non-existent condition returns None."""
        result = condition_crud.update_condition(
            db,
            code="9",
            name="Should Not Work",
        )

        assert result is None

    def test_update_strips_whitespace(self, db: Session, crud_test_conditions):
        """Test that update_condition strips whitespace."""
        code = crud_test_conditions["codes"][0]

        result = condition_crud.update_condition(
            db,
            code=code,
            name="  Whitespace  ",
        )

        assert result is not None
        assert result.name == "Whitespace"


class TestDeleteCondition:
    """Tests for delete_condition."""

    def test_delete_existing(self, db: Session):
        """Test deleting an existing condition."""
        # Create a condition to delete
        codes = _get_unique_codes(db, count=1)
        code = codes[0]
        sort_orders = _get_unique_sort_orders(db, count=1)

        condition = Condition(
            code=code,
            name="To Delete",
            sort_order=sort_orders[0],
        )
        db.add(condition)
        db.commit()

        result = condition_crud.delete_condition(db, code)

        assert result is True
        # Verify deletion
        deleted = db.query(Condition).filter(Condition.code == code).first()
        assert deleted is None

    def test_delete_nonexistent(self, db: Session):
        """Test deleting a non-existent condition returns False."""
        result = condition_crud.delete_condition(db, "9")

        assert result is False


class TestGetConditionUsageCount:
    """Tests for get_condition_usage_count."""

    def test_usage_count_no_usage(self, db: Session, crud_test_conditions):
        """Test usage count for condition with no logs."""
        code = crud_test_conditions["codes"][0]

        result = condition_crud.get_condition_usage_count(db, code)

        assert isinstance(result, int)
        assert result >= 0

    def test_usage_count_nonexistent_code(self, db: Session):
        """Test usage count for non-existent code (should return 0)."""
        result = condition_crud.get_condition_usage_count(db, "9")

        assert result == 0
