"""
Tests for CRUD operations on trig_type and trig_category tables (admin functions).

Tests the new CRUD functions: create, update, delete, reorder.
"""

import uuid
from typing import cast

import pytest
from sqlalchemy.orm import Session

from api.crud import trig_type as trig_type_crud
from api.models.trig_type import TrigCategory


def _get_unique_sort_orders(db: Session, count: int = 2) -> list[int]:
    """Find unique sort_order values that don't exist in the database."""
    import random

    existing = {
        row[0] for row in db.query(TrigCategory.sort_order).all() if row[0] is not None
    }

    attempts = 0
    while attempts < 100:
        base = random.randint(10000, 32000 - count)
        candidates = [base + i for i in range(count)]
        if not any(c in existing for c in candidates):
            return candidates
        attempts += 1

    return [32000 + i for i in range(count)]


class TestCategoryCreate:
    """Tests for create_category CRUD function."""

    def test_create_category_basic(self, db: Session):
        """Test basic category creation."""
        unique_code = f"TESTCAT_{uuid.uuid4().hex[:6]}"
        sort_order = _get_unique_sort_orders(db, count=1)[0]

        category = trig_type_crud.create_category(
            db,
            code=unique_code,
            name="Test Category",
            sort_order=sort_order,
        )

        assert category.id is not None
        assert category.code == unique_code.upper()
        assert category.name == "Test Category"
        assert category.sort_order == sort_order
        assert category.description is None
        assert category.wiki_url is None

    def test_create_category_with_all_fields(self, db: Session):
        """Test category creation with all optional fields."""
        unique_code = f"FULLCAT_{uuid.uuid4().hex[:6]}"
        sort_order = _get_unique_sort_orders(db, count=1)[0]

        category = trig_type_crud.create_category(
            db,
            code=unique_code,
            name="Full Category",
            sort_order=sort_order,
            description="A test description",
            wiki_url="https://example.com/wiki",
        )

        assert category.code == unique_code.upper()
        assert category.name == "Full Category"
        assert category.description == "A test description"
        assert category.wiki_url == "https://example.com/wiki"

    def test_create_category_code_uppercase(self, db: Session):
        """Test that category code is converted to uppercase."""
        unique_code = f"lowercase_{uuid.uuid4().hex[:6]}"
        sort_order = _get_unique_sort_orders(db, count=1)[0]

        category = trig_type_crud.create_category(
            db,
            code=unique_code,
            name="Lowercase Test",
            sort_order=sort_order,
        )

        assert category.code == unique_code.upper()


class TestCategoryUpdate:
    """Tests for update_category CRUD function."""

    def test_update_category_name(self, db: Session):
        """Test updating category name."""
        sort_order = _get_unique_sort_orders(db, count=1)[0]
        category = trig_type_crud.create_category(
            db,
            code=f"UPCAT_{uuid.uuid4().hex[:6]}",
            name="Original Name",
            sort_order=sort_order,
        )

        updated = trig_type_crud.update_category(
            db,
            cast(int, category.id),
            name="Updated Name",
        )

        assert updated is not None
        assert updated.name == "Updated Name"
        assert updated.code == category.code  # Unchanged

    def test_update_category_all_fields(self, db: Session):
        """Test updating all category fields."""
        sort_order = _get_unique_sort_orders(db, count=1)[0]
        category = trig_type_crud.create_category(
            db,
            code=f"ALLUP_{uuid.uuid4().hex[:6]}",
            name="Original",
            sort_order=sort_order,
        )
        new_code = f"NEWCODE_{uuid.uuid4().hex[:6]}"

        updated = trig_type_crud.update_category(
            db,
            cast(int, category.id),
            code=new_code,
            name="New Name",
            description="New description",
            wiki_url="https://new.example.com",
            sort_order=sort_order + 100,
        )

        assert updated is not None
        assert updated.code == new_code.upper()
        assert updated.name == "New Name"
        assert updated.description == "New description"
        assert updated.wiki_url == "https://new.example.com"
        assert updated.sort_order == sort_order + 100

    def test_update_category_clear_optional_fields(self, db: Session):
        """Test clearing optional fields by passing empty string."""
        sort_order = _get_unique_sort_orders(db, count=1)[0]
        category = trig_type_crud.create_category(
            db,
            code=f"CLEAR_{uuid.uuid4().hex[:6]}",
            name="Clear Test",
            sort_order=sort_order,
            description="Has description",
            wiki_url="https://example.com",
        )

        updated = trig_type_crud.update_category(
            db,
            cast(int, category.id),
            description="",
            wiki_url="",
        )

        assert updated is not None
        assert updated.description is None
        assert updated.wiki_url is None

    def test_update_category_not_found(self, db: Session):
        """Test updating non-existent category returns None."""
        result = trig_type_crud.update_category(
            db,
            999999,
            name="Test",
        )

        assert result is None


class TestCategoryDelete:
    """Tests for delete_category CRUD function."""

    def test_delete_empty_category(self, db: Session):
        """Test deleting a category with no types."""
        sort_order = _get_unique_sort_orders(db, count=1)[0]
        category = trig_type_crud.create_category(
            db,
            code=f"DELCAT_{uuid.uuid4().hex[:6]}",
            name="To Delete",
            sort_order=sort_order,
        )
        category_id = cast(int, category.id)

        result = trig_type_crud.delete_category(db, category_id)

        assert result is True
        assert trig_type_crud.get_category_by_id(db, category_id) is None

    def test_delete_category_with_types_fails(self, db: Session):
        """Test that deleting a category with types raises an error."""
        sort_order = _get_unique_sort_orders(db, count=1)[0]
        category = trig_type_crud.create_category(
            db,
            code=f"HASTYPE_{uuid.uuid4().hex[:6]}",
            name="Has Types",
            sort_order=sort_order,
        )

        # Add a type
        trig_type_crud.create_type(
            db,
            category_id=cast(int, category.id),
            code=f"TYPE_{uuid.uuid4().hex[:6]}",
            name="Test Type",
            sort_order=1,
        )

        with pytest.raises(ValueError) as exc_info:
            trig_type_crud.delete_category(db, cast(int, category.id))

        assert "types are assigned" in str(exc_info.value)

    def test_delete_category_not_found(self, db: Session):
        """Test deleting non-existent category returns False."""
        result = trig_type_crud.delete_category(db, 999999)
        assert result is False


class TestCategoryReorder:
    """Tests for reorder_categories CRUD function."""

    def test_reorder_categories(self, db: Session):
        """Test reordering categories."""
        sort_orders = _get_unique_sort_orders(db, count=3)

        cat1 = trig_type_crud.create_category(
            db,
            code=f"ORD1_{uuid.uuid4().hex[:6]}",
            name="Order 1",
            sort_order=sort_orders[0],
        )
        cat2 = trig_type_crud.create_category(
            db,
            code=f"ORD2_{uuid.uuid4().hex[:6]}",
            name="Order 2",
            sort_order=sort_orders[1],
        )
        cat3 = trig_type_crud.create_category(
            db,
            code=f"ORD3_{uuid.uuid4().hex[:6]}",
            name="Order 3",
            sort_order=sort_orders[2],
        )

        # Reorder: 3, 1, 2 - the function takes existing sort_orders, sorts them,
        # and assigns in the new order. So cat3 (first) gets smallest, cat2 (last) gets largest.
        trig_type_crud.reorder_categories(
            db, [cast(int, cat3.id), cast(int, cat1.id), cast(int, cat2.id)]
        )

        # Refresh
        db.refresh(cat1)
        db.refresh(cat2)
        db.refresh(cat3)

        # After reorder, they should have the sorted existing values assigned in new order
        assert cat3.sort_order == sort_orders[0]  # cat3 now first
        assert cat1.sort_order == sort_orders[1]  # cat1 now second
        assert cat2.sort_order == sort_orders[2]  # cat2 now third


class TestGetNextCategorySortOrder:
    """Tests for get_next_category_sort_order CRUD function."""

    def test_get_next_category_sort_order(self, db: Session):
        """Test getting next available sort order."""
        sort_order = _get_unique_sort_orders(db, count=1)[0]
        trig_type_crud.create_category(
            db,
            code=f"MAXCAT_{uuid.uuid4().hex[:6]}",
            name="Max Test",
            sort_order=sort_order,
        )

        next_order = trig_type_crud.get_next_category_sort_order(db)

        # Next order should be greater than what we just inserted
        assert next_order > sort_order


class TestTypeCreate:
    """Tests for create_type CRUD function."""

    @pytest.fixture
    def test_category(self, db: Session):
        """Create a test category for type tests."""
        sort_order = _get_unique_sort_orders(db, count=1)[0]
        return trig_type_crud.create_category(
            db,
            code=f"TYPECAT_{uuid.uuid4().hex[:6]}",
            name="Type Test Category",
            sort_order=sort_order,
        )

    def test_create_type_basic(self, db: Session, test_category):
        """Test basic type creation."""
        unique_code = f"TESTTYPE_{uuid.uuid4().hex[:6]}"

        trig_type = trig_type_crud.create_type(
            db,
            category_id=cast(int, test_category.id),
            code=unique_code,
            name="Test Type",
            sort_order=1,
        )

        assert trig_type.id is not None
        assert trig_type.code == unique_code.upper()
        assert trig_type.name == "Test Type"
        assert trig_type.category_id == test_category.id
        assert trig_type.sort_order == 1

    def test_create_type_with_all_fields(self, db: Session, test_category):
        """Test type creation with all optional fields."""
        unique_code = f"FULLTYPE_{uuid.uuid4().hex[:6]}"

        trig_type = trig_type_crud.create_type(
            db,
            category_id=cast(int, test_category.id),
            code=unique_code,
            name="Full Type",
            sort_order=2,
            description="A test description",
            wiki_url="https://example.com/type",
            legacy_physical_type="TestLegacy",
        )

        assert trig_type.description == "A test description"
        assert trig_type.wiki_url == "https://example.com/type"
        assert trig_type.legacy_physical_type == "TestLegacy"


class TestTypeUpdate:
    """Tests for update_type CRUD function."""

    @pytest.fixture
    def test_type(self, db: Session):
        """Create a test type for update tests."""
        sort_order = _get_unique_sort_orders(db, count=1)[0]
        category = trig_type_crud.create_category(
            db,
            code=f"UPCAT_{uuid.uuid4().hex[:6]}",
            name="Update Category",
            sort_order=sort_order,
        )
        return trig_type_crud.create_type(
            db,
            category_id=cast(int, category.id),
            code=f"UPTYPE_{uuid.uuid4().hex[:6]}",
            name="Original Type",
            sort_order=1,
            description="Original description",
        )

    def test_update_type_name(self, db: Session, test_type):
        """Test updating type name."""
        updated = trig_type_crud.update_type(
            db,
            cast(int, test_type.id),
            name="Updated Name",
        )

        assert updated is not None
        assert updated.name == "Updated Name"
        assert updated.code == test_type.code  # Unchanged

    def test_update_type_move_category(self, db: Session, test_type):
        """Test moving type to different category."""
        sort_order = _get_unique_sort_orders(db, count=1)[0]
        new_category = trig_type_crud.create_category(
            db,
            code=f"NEWCAT_{uuid.uuid4().hex[:6]}",
            name="New Category",
            sort_order=sort_order,
        )

        updated = trig_type_crud.update_type(
            db,
            cast(int, test_type.id),
            category_id=cast(int, new_category.id),
        )

        assert updated is not None
        assert updated.category_id == new_category.id

    def test_update_type_clear_optional_fields(self, db: Session, test_type):
        """Test clearing optional fields by passing empty string."""
        # First set the fields
        trig_type_crud.update_type(
            db,
            cast(int, test_type.id),
            wiki_url="https://example.com",
            legacy_physical_type="Legacy",
        )

        # Then clear them
        updated = trig_type_crud.update_type(
            db,
            cast(int, test_type.id),
            description="",
            wiki_url="",
            legacy_physical_type="",
        )

        assert updated is not None
        assert updated.description is None
        assert updated.wiki_url is None
        assert updated.legacy_physical_type is None

    def test_update_type_not_found(self, db: Session):
        """Test updating non-existent type returns None."""
        result = trig_type_crud.update_type(
            db,
            999999,
            name="Test",
        )

        assert result is None


class TestTypeDelete:
    """Tests for delete_type CRUD function."""

    def test_delete_type(self, db: Session):
        """Test deleting a type."""
        sort_order = _get_unique_sort_orders(db, count=1)[0]
        category = trig_type_crud.create_category(
            db,
            code=f"DELCAT_{uuid.uuid4().hex[:6]}",
            name="Delete Category",
            sort_order=sort_order,
        )
        trig_type = trig_type_crud.create_type(
            db,
            category_id=cast(int, category.id),
            code=f"DELTYPE_{uuid.uuid4().hex[:6]}",
            name="To Delete",
            sort_order=1,
        )
        type_id = cast(int, trig_type.id)

        result = trig_type_crud.delete_type(db, type_id)

        assert result is True
        assert trig_type_crud.get_type_by_id(db, type_id) is None

    def test_delete_type_not_found(self, db: Session):
        """Test deleting non-existent type returns False."""
        result = trig_type_crud.delete_type(db, 999999)
        assert result is False


class TestTypeReorder:
    """Tests for reorder_types CRUD function."""

    def test_reorder_types_within_category(self, db: Session):
        """Test reordering types within a category."""
        sort_order = _get_unique_sort_orders(db, count=1)[0]
        category = trig_type_crud.create_category(
            db,
            code=f"ORDCAT_{uuid.uuid4().hex[:6]}",
            name="Reorder Category",
            sort_order=sort_order,
        )

        type1 = trig_type_crud.create_type(
            db,
            category_id=cast(int, category.id),
            code=f"ORD1_{uuid.uuid4().hex[:6]}",
            name="Order 1",
            sort_order=1,
        )
        type2 = trig_type_crud.create_type(
            db,
            category_id=cast(int, category.id),
            code=f"ORD2_{uuid.uuid4().hex[:6]}",
            name="Order 2",
            sort_order=2,
        )
        type3 = trig_type_crud.create_type(
            db,
            category_id=cast(int, category.id),
            code=f"ORD3_{uuid.uuid4().hex[:6]}",
            name="Order 3",
            sort_order=3,
        )

        # Reorder: 3, 1, 2
        trig_type_crud.reorder_types(
            db,
            cast(int, category.id),
            [cast(int, type3.id), cast(int, type1.id), cast(int, type2.id)],
        )

        # Refresh
        db.refresh(type1)
        db.refresh(type2)
        db.refresh(type3)

        assert type3.sort_order == 1
        assert type1.sort_order == 2
        assert type2.sort_order == 3


class TestGetNextTypeSortOrder:
    """Tests for get_next_type_sort_order CRUD function."""

    def test_get_next_type_sort_order_empty_category(self, db: Session):
        """Test getting next sort order for empty category."""
        sort_order = _get_unique_sort_orders(db, count=1)[0]
        category = trig_type_crud.create_category(
            db,
            code=f"EMPTYCAT_{uuid.uuid4().hex[:6]}",
            name="Empty Category",
            sort_order=sort_order,
        )

        next_order = trig_type_crud.get_next_type_sort_order(db, cast(int, category.id))

        assert next_order == 1

    def test_get_next_type_sort_order_with_types(self, db: Session):
        """Test getting next sort order for category with types."""
        sort_order = _get_unique_sort_orders(db, count=1)[0]
        category = trig_type_crud.create_category(
            db,
            code=f"HASTYPE_{uuid.uuid4().hex[:6]}",
            name="Has Types",
            sort_order=sort_order,
        )
        trig_type_crud.create_type(
            db,
            category_id=cast(int, category.id),
            code=f"TYPE1_{uuid.uuid4().hex[:6]}",
            name="Type 1",
            sort_order=5,
        )

        next_order = trig_type_crud.get_next_type_sort_order(db, cast(int, category.id))

        assert next_order == 6


class TestGetTypeUsageCount:
    """Tests for get_type_usage_count CRUD function."""

    def test_get_type_usage_count_no_usage(self, db: Session):
        """Test usage count for type with no trigs."""
        sort_order = _get_unique_sort_orders(db, count=1)[0]
        category = trig_type_crud.create_category(
            db,
            code=f"USAGECAT_{uuid.uuid4().hex[:6]}",
            name="Usage Category",
            sort_order=sort_order,
        )
        trig_type = trig_type_crud.create_type(
            db,
            category_id=cast(int, category.id),
            code=f"USAGE_{uuid.uuid4().hex[:6]}",
            name="Usage Type",
            sort_order=1,
        )

        count = trig_type_crud.get_type_usage_count(db, cast(int, trig_type.id))

        assert count == 0
