"""
Tests for the /v1/types endpoint.

Tests trig type and category queries.
"""

import uuid

import pytest
from fastapi.testclient import TestClient

from api.models.trig_type import TrigCategory, TrigType


@pytest.fixture
def type_test_data(db):
    """Create test categories and types for endpoint testing."""
    import random

    unique_suffix = uuid.uuid4().hex[:6]

    # Use completely random large numbers for sort_order to avoid collisions
    # SmallInteger max is 32767, so use 20000-32000 range with random offset
    base_sort = random.randint(20000, 32000)

    # Create test categories
    category1 = TrigCategory(
        code=f"CAT1_{unique_suffix}",
        name="Test Category 1",
        description="First test category",
        wiki_url="https://example.com/cat1",
        sort_order=base_sort,
    )
    category2 = TrigCategory(
        code=f"CAT2_{unique_suffix}",
        name="Test Category 2",
        description="Second test category",
        wiki_url="https://example.com/cat2",
        sort_order=base_sort + 1,
    )
    db.add(category1)
    db.add(category2)
    db.flush()

    # Create test types in category1
    type1 = TrigType(
        category_id=category1.id,
        code=f"TYPE1_{unique_suffix}",
        name="Test Type 1",
        description="First test type",
        wiki_url="https://example.com/type1",
        sort_order=1,
        legacy_physical_type="Pillar",
    )
    type2 = TrigType(
        category_id=category1.id,
        code=f"TYPE2_{unique_suffix}",
        name="Test Type 2",
        description="Second test type",
        wiki_url="https://example.com/type2",
        sort_order=2,
        legacy_physical_type="Bolt",
    )

    # Create test type in category2
    type3 = TrigType(
        category_id=category2.id,
        code=f"TYPE3_{unique_suffix}",
        name="Test Type 3",
        description="Third test type",
        wiki_url="https://example.com/type3",
        sort_order=1,
        legacy_physical_type="Block",
    )

    db.add(type1)
    db.add(type2)
    db.add(type3)
    db.commit()

    return {
        "category1": category1,
        "category2": category2,
        "type1": type1,
        "type2": type2,
        "type3": type3,
        "suffix": unique_suffix,
    }


class TestListTypeCategories:
    """Tests for GET /v1/types/categories."""

    def test_list_categories_returns_data(self, client: TestClient, type_test_data, db):
        """Test that listing categories returns test data."""
        response = client.get("/v1/types/categories")

        assert response.status_code == 200
        data = response.json()

        # Should return a list
        assert isinstance(data, list)

        # Find our test categories in the response
        suffix = type_test_data["suffix"]
        our_categories = [c for c in data if c["code"].endswith(suffix)]

        # We should have our 2 test categories
        assert len(our_categories) == 2

        # Check category structure
        cat = our_categories[0]
        assert "id" in cat
        assert "code" in cat
        assert "name" in cat
        assert "sort_order" in cat
        assert "types" in cat  # Should include nested types

    def test_list_categories_includes_types(
        self, client: TestClient, type_test_data, db
    ):
        """Test that categories include their nested types."""
        response = client.get("/v1/types/categories")

        assert response.status_code == 200
        data = response.json()

        suffix = type_test_data["suffix"]
        cat1_code = f"CAT1_{suffix}"

        # Find category 1
        cat1 = next((c for c in data if c["code"] == cat1_code), None)
        assert cat1 is not None

        # Should have 2 types
        types = cat1.get("types", [])
        assert len(types) == 2

        # Check type structure
        type_codes = [t["code"] for t in types]
        assert f"TYPE1_{suffix}" in type_codes
        assert f"TYPE2_{suffix}" in type_codes


class TestGetCategoryByCode:
    """Tests for GET /v1/types/categories/{code}."""

    def test_get_category_by_code(self, client: TestClient, type_test_data, db):
        """Test fetching a specific category by code."""
        suffix = type_test_data["suffix"]
        code = f"CAT1_{suffix}"

        response = client.get(f"/v1/types/categories/{code}")

        assert response.status_code == 200
        data = response.json()

        assert data["code"] == code
        assert data["name"] == "Test Category 1"
        assert "types" in data
        assert len(data["types"]) == 2

    def test_get_category_case_insensitive(
        self, client: TestClient, type_test_data, db
    ):
        """Test that category lookup is case-insensitive."""
        suffix = type_test_data["suffix"]
        code = f"cat1_{suffix}"  # lowercase

        response = client.get(f"/v1/types/categories/{code}")

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == f"CAT1_{suffix}"

    def test_get_category_not_found(self, client: TestClient, db):
        """Test 404 for non-existent category."""
        response = client.get("/v1/types/categories/NONEXISTENT_CATEGORY_XYZ")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()


class TestListTypes:
    """Tests for GET /v1/types."""

    def test_list_all_types(self, client: TestClient, type_test_data, db):
        """Test listing all types."""
        response = client.get("/v1/types")

        assert response.status_code == 200
        data = response.json()

        # Should return a list
        assert isinstance(data, list)

        # Find our test types
        suffix = type_test_data["suffix"]
        our_types = [t for t in data if t["code"].endswith(suffix)]

        # Should have our 3 test types
        assert len(our_types) == 3

        # Check type structure includes category
        type_item = our_types[0]
        assert "id" in type_item
        assert "code" in type_item
        assert "name" in type_item
        assert "category" in type_item

        # Check nested category structure
        category = type_item["category"]
        assert "id" in category
        assert "code" in category
        assert "name" in category

    def test_list_types_filter_by_category(
        self, client: TestClient, type_test_data, db
    ):
        """Test filtering types by category code."""
        suffix = type_test_data["suffix"]
        category_code = f"CAT1_{suffix}"

        response = client.get(f"/v1/types?category={category_code}")

        assert response.status_code == 200
        data = response.json()

        # Should only return types from category 1
        our_types = [t for t in data if t["code"].endswith(suffix)]
        assert len(our_types) == 2  # TYPE1 and TYPE2 only

        # All should belong to category 1
        for t in our_types:
            assert t["category"]["code"] == category_code

    def test_list_types_filter_category_not_found(self, client: TestClient, db):
        """Test 404 when filtering by non-existent category."""
        response = client.get("/v1/types?category=NONEXISTENT_XYZ")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()


class TestGetTypeByCode:
    """Tests for GET /v1/types/{code}."""

    def test_get_type_by_code(self, client: TestClient, type_test_data, db):
        """Test fetching a specific type by code."""
        suffix = type_test_data["suffix"]
        code = f"TYPE1_{suffix}"

        response = client.get(f"/v1/types/{code}")

        assert response.status_code == 200
        data = response.json()

        assert data["code"] == code
        assert data["name"] == "Test Type 1"
        assert data["description"] == "First test type"
        assert "category" in data
        assert data["category"]["code"] == f"CAT1_{suffix}"

    def test_get_type_case_insensitive(self, client: TestClient, type_test_data, db):
        """Test that type lookup is case-insensitive."""
        suffix = type_test_data["suffix"]
        code = f"type1_{suffix}"  # lowercase

        response = client.get(f"/v1/types/{code}")

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == f"TYPE1_{suffix}"

    def test_get_type_not_found(self, client: TestClient, db):
        """Test 404 for non-existent type."""
        response = client.get("/v1/types/NONEXISTENT_TYPE_XYZ")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()


class TestTypeResponseStructure:
    """Tests for response structure validation."""

    def test_type_with_category_structure(self, client: TestClient, type_test_data, db):
        """Test TrigTypeWithCategory response structure."""
        suffix = type_test_data["suffix"]
        code = f"TYPE1_{suffix}"

        response = client.get(f"/v1/types/{code}")

        assert response.status_code == 200
        data = response.json()

        # Required fields for type
        assert "id" in data
        assert "code" in data
        assert "name" in data
        assert "sort_order" in data
        assert "category" in data

        # Optional fields for type (check they're present, values can be None)
        assert "description" in data
        assert "wiki_url" in data

        # Category nested structure
        category = data["category"]
        assert "id" in category
        assert "code" in category
        assert "name" in category
        assert "sort_order" in category

    def test_category_with_types_structure(
        self, client: TestClient, type_test_data, db
    ):
        """Test TrigCategoryWithTypes response structure."""
        suffix = type_test_data["suffix"]
        code = f"CAT1_{suffix}"

        response = client.get(f"/v1/types/categories/{code}")

        assert response.status_code == 200
        data = response.json()

        # Required category fields
        assert "id" in data
        assert "code" in data
        assert "name" in data
        assert "sort_order" in data
        assert "types" in data

        # Types should be a list
        assert isinstance(data["types"], list)
        assert len(data["types"]) > 0

        # Each type should have the right structure
        for type_item in data["types"]:
            assert "id" in type_item
            assert "code" in type_item
            assert "name" in type_item
            assert "sort_order" in type_item
