"""
Tests for the /v1/admin/types endpoint.

Tests admin CRUD operations for trig_type and trig_category.
"""

import uuid
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from api.models.trig_type import TrigCategory, TrigType


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


@pytest.fixture
def admin_auth_mock():
    """Mock authentication to return admin token."""

    def _mock(user_id: int = 1):
        return {
            "token_type": "auth0",
            "auth0_user_id": f"auth0|{user_id}",
            "sub": f"auth0|{user_id}",
            "scope": "api:write api:admin",
        }

    return _mock


@pytest.fixture
def non_admin_auth_mock():
    """Mock authentication to return non-admin token."""

    def _mock(user_id: int = 1):
        return {
            "token_type": "auth0",
            "auth0_user_id": f"auth0|{user_id}",
            "sub": f"auth0|{user_id}",
            "scope": "api:write",  # Missing api:admin
        }

    return _mock


@pytest.fixture
def admin_test_data(db: Session):
    """Create test categories and types for admin endpoint testing."""
    unique_suffix = uuid.uuid4().hex[:6]
    sort_orders = _get_unique_sort_orders(db, count=3)

    # Create test categories
    category1 = TrigCategory(
        code=f"ACAT1_{unique_suffix}",
        name="Admin Test Category 1",
        description="First admin test category",
        wiki_url="https://example.com/acat1",
        sort_order=sort_orders[0],
    )
    category2 = TrigCategory(
        code=f"ACAT2_{unique_suffix}",
        name="Admin Test Category 2",
        description="Second admin test category",
        sort_order=sort_orders[1],
    )
    db.add(category1)
    db.add(category2)
    db.flush()

    # Create test types
    type1 = TrigType(
        category_id=category1.id,
        code=f"ATYPE1_{unique_suffix}",
        name="Admin Test Type 1",
        description="First admin test type",
        wiki_url="https://example.com/atype1",
        sort_order=1,
        legacy_physical_type="TestPillar",
    )
    type2 = TrigType(
        category_id=category1.id,
        code=f"ATYPE2_{unique_suffix}",
        name="Admin Test Type 2",
        description="Second admin test type",
        sort_order=2,
    )
    type3 = TrigType(
        category_id=category2.id,
        code=f"ATYPE3_{unique_suffix}",
        name="Admin Test Type 3",
        sort_order=1,
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
        "sort_orders": sort_orders,
    }


class TestAdminGetCategories:
    """Tests for GET /v1/admin/types/categories."""

    def test_get_categories_requires_admin(
        self, client: TestClient, admin_test_data, db: Session, non_admin_auth_mock
    ):
        """Test that non-admin users cannot access admin categories endpoint."""
        with patch("api.api.deps.auth0_validator.validate_auth0_token") as mock:
            mock.return_value = non_admin_auth_mock(1)

            response = client.get(
                "/v1/admin/types/categories",
                headers={"Authorization": "Bearer mock_token"},
            )

            assert response.status_code == 403

    def test_get_categories_as_admin(
        self, client: TestClient, admin_test_data, db: Session, admin_auth_mock
    ):
        """Test that admin users can get categories."""
        with patch("api.api.deps.auth0_validator.validate_auth0_token") as mock:
            mock.return_value = admin_auth_mock(1)

            response = client.get(
                "/v1/admin/types/categories",
                headers={"Authorization": "Bearer mock_token"},
            )

            assert response.status_code == 200
            data = response.json()
            assert isinstance(data, list)

            # Find our test categories
            suffix = admin_test_data["suffix"]
            our_categories = [c for c in data if c["code"].endswith(suffix)]
            assert len(our_categories) == 2

            # Check that types are included
            cat1 = next(
                (c for c in our_categories if c["code"] == f"ACAT1_{suffix}"), None
            )
            assert cat1 is not None
            assert "types" in cat1
            assert len(cat1["types"]) == 2


class TestAdminCreateCategory:
    """Tests for POST /v1/admin/types/categories."""

    def test_create_category_requires_admin(
        self, client: TestClient, db: Session, non_admin_auth_mock
    ):
        """Test that non-admin users cannot create categories."""
        with patch("api.api.deps.auth0_validator.validate_auth0_token") as mock:
            mock.return_value = non_admin_auth_mock(1)

            response = client.post(
                "/v1/admin/types/categories",
                json={"code": "TEST", "name": "Test"},
                headers={"Authorization": "Bearer mock_token"},
            )

            assert response.status_code == 403

    def test_create_category_success(
        self, client: TestClient, db: Session, admin_auth_mock
    ):
        """Test successful category creation."""
        unique_code = f"NEWCAT_{uuid.uuid4().hex[:6]}"

        with patch("api.api.deps.auth0_validator.validate_auth0_token") as mock:
            mock.return_value = admin_auth_mock(1)

            response = client.post(
                "/v1/admin/types/categories",
                json={
                    "code": unique_code,
                    "name": "New Test Category",
                    "description": "A new test category",
                    "wiki_url": "https://example.com/newcat",
                },
                headers={"Authorization": "Bearer mock_token"},
            )

            assert response.status_code == 201
            data = response.json()
            assert data["code"] == unique_code.upper()
            assert data["name"] == "New Test Category"
            assert data["description"] == "A new test category"
            assert "id" in data
            assert "sort_order" in data

    def test_create_category_duplicate_code(
        self, client: TestClient, admin_test_data, db: Session, admin_auth_mock
    ):
        """Test that duplicate codes are rejected."""
        existing_code = admin_test_data["category1"].code

        with patch("api.api.deps.auth0_validator.validate_auth0_token") as mock:
            mock.return_value = admin_auth_mock(1)

            response = client.post(
                "/v1/admin/types/categories",
                json={"code": existing_code, "name": "Duplicate"},
                headers={"Authorization": "Bearer mock_token"},
            )

            assert response.status_code == 400
            assert "already exists" in response.json()["detail"]


class TestAdminUpdateCategory:
    """Tests for PATCH /v1/admin/types/categories/{category_id}."""

    def test_update_category_requires_admin(
        self, client: TestClient, admin_test_data, db: Session, non_admin_auth_mock
    ):
        """Test that non-admin users cannot update categories."""
        category_id = admin_test_data["category1"].id

        with patch("api.api.deps.auth0_validator.validate_auth0_token") as mock:
            mock.return_value = non_admin_auth_mock(1)

            response = client.patch(
                f"/v1/admin/types/categories/{category_id}",
                json={"name": "Updated Name"},
                headers={"Authorization": "Bearer mock_token"},
            )

            assert response.status_code == 403

    def test_update_category_success(
        self, client: TestClient, admin_test_data, db: Session, admin_auth_mock
    ):
        """Test successful category update."""
        category_id = admin_test_data["category1"].id

        with patch("api.api.deps.auth0_validator.validate_auth0_token") as mock:
            mock.return_value = admin_auth_mock(1)

            response = client.patch(
                f"/v1/admin/types/categories/{category_id}",
                json={
                    "name": "Updated Category Name",
                    "description": "Updated description",
                },
                headers={"Authorization": "Bearer mock_token"},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["name"] == "Updated Category Name"
            assert data["description"] == "Updated description"

    def test_update_category_not_found(
        self, client: TestClient, db: Session, admin_auth_mock
    ):
        """Test 404 for non-existent category."""
        with patch("api.api.deps.auth0_validator.validate_auth0_token") as mock:
            mock.return_value = admin_auth_mock(1)

            response = client.patch(
                "/v1/admin/types/categories/999999",
                json={"name": "Test"},
                headers={"Authorization": "Bearer mock_token"},
            )

            assert response.status_code == 404


class TestAdminDeleteCategory:
    """Tests for DELETE /v1/admin/types/categories/{category_id}."""

    def test_delete_category_requires_admin(
        self, client: TestClient, admin_test_data, db: Session, non_admin_auth_mock
    ):
        """Test that non-admin users cannot delete categories."""
        category_id = admin_test_data["category1"].id

        with patch("api.api.deps.auth0_validator.validate_auth0_token") as mock:
            mock.return_value = non_admin_auth_mock(1)

            response = client.delete(
                f"/v1/admin/types/categories/{category_id}",
                headers={"Authorization": "Bearer mock_token"},
            )

            assert response.status_code == 403

    def test_delete_category_with_types_fails(
        self, client: TestClient, admin_test_data, db: Session, admin_auth_mock
    ):
        """Test that deleting a category with types fails."""
        category_id = admin_test_data["category1"].id

        with patch("api.api.deps.auth0_validator.validate_auth0_token") as mock:
            mock.return_value = admin_auth_mock(1)

            response = client.delete(
                f"/v1/admin/types/categories/{category_id}",
                headers={"Authorization": "Bearer mock_token"},
            )

            assert response.status_code == 400
            assert "types are assigned" in response.json()["detail"]

    def test_delete_empty_category_success(
        self, client: TestClient, db: Session, admin_auth_mock
    ):
        """Test successful deletion of empty category."""
        # Create an empty category
        sort_orders = _get_unique_sort_orders(db, count=1)
        empty_category = TrigCategory(
            code=f"EMPTY_{uuid.uuid4().hex[:6]}",
            name="Empty Category",
            sort_order=sort_orders[0],
        )
        db.add(empty_category)
        db.commit()
        category_id = empty_category.id

        with patch("api.api.deps.auth0_validator.validate_auth0_token") as mock:
            mock.return_value = admin_auth_mock(1)

            response = client.delete(
                f"/v1/admin/types/categories/{category_id}",
                headers={"Authorization": "Bearer mock_token"},
            )

            assert response.status_code == 204

            # Verify deletion
            deleted = (
                db.query(TrigCategory).filter(TrigCategory.id == category_id).first()
            )
            assert deleted is None


class TestAdminReorderCategories:
    """Tests for POST /v1/admin/types/categories/reorder."""

    def test_reorder_categories_requires_admin(
        self, client: TestClient, admin_test_data, db: Session, non_admin_auth_mock
    ):
        """Test that non-admin users cannot reorder categories."""
        with patch("api.api.deps.auth0_validator.validate_auth0_token") as mock:
            mock.return_value = non_admin_auth_mock(1)

            response = client.post(
                "/v1/admin/types/categories/reorder",
                json={"order": [1, 2]},
                headers={"Authorization": "Bearer mock_token"},
            )

            assert response.status_code == 403

    def test_reorder_categories_success(
        self, client: TestClient, admin_test_data, db: Session, admin_auth_mock
    ):
        """Test successful category reordering."""
        cat1_id = admin_test_data["category1"].id
        cat2_id = admin_test_data["category2"].id

        with patch("api.api.deps.auth0_validator.validate_auth0_token") as mock:
            mock.return_value = admin_auth_mock(1)

            # Reverse the order
            response = client.post(
                "/v1/admin/types/categories/reorder",
                json={"order": [cat2_id, cat1_id]},
                headers={"Authorization": "Bearer mock_token"},
            )

            assert response.status_code == 200
            data = response.json()

            # Find our categories in response
            cat1_result = next((c for c in data if c["id"] == cat1_id), None)
            cat2_result = next((c for c in data if c["id"] == cat2_id), None)

            # cat2 should now have lower sort_order than cat1 (order reversed)
            assert cat2_result is not None
            assert cat1_result is not None
            assert cat2_result["sort_order"] < cat1_result["sort_order"]


class TestAdminCreateType:
    """Tests for POST /v1/admin/types/types."""

    def test_create_type_requires_admin(
        self, client: TestClient, admin_test_data, db: Session, non_admin_auth_mock
    ):
        """Test that non-admin users cannot create types."""
        with patch("api.api.deps.auth0_validator.validate_auth0_token") as mock:
            mock.return_value = non_admin_auth_mock(1)

            response = client.post(
                "/v1/admin/types/types",
                json={
                    "category_id": admin_test_data["category1"].id,
                    "code": "TEST",
                    "name": "Test",
                },
                headers={"Authorization": "Bearer mock_token"},
            )

            assert response.status_code == 403

    def test_create_type_success(
        self, client: TestClient, admin_test_data, db: Session, admin_auth_mock
    ):
        """Test successful type creation."""
        unique_code = f"NEWTYPE_{uuid.uuid4().hex[:6]}"
        category_id = admin_test_data["category1"].id

        with patch("api.api.deps.auth0_validator.validate_auth0_token") as mock:
            mock.return_value = admin_auth_mock(1)

            response = client.post(
                "/v1/admin/types/types",
                json={
                    "category_id": category_id,
                    "code": unique_code,
                    "name": "New Test Type",
                    "description": "A new test type",
                    "wiki_url": "https://example.com/newtype",
                    "legacy_physical_type": "TestLegacy",
                },
                headers={"Authorization": "Bearer mock_token"},
            )

            assert response.status_code == 201
            data = response.json()
            assert data["code"] == unique_code.upper()
            assert data["name"] == "New Test Type"
            assert data["description"] == "A new test type"
            assert "category" in data
            assert data["category"]["id"] == category_id

    def test_create_type_invalid_category(
        self, client: TestClient, db: Session, admin_auth_mock
    ):
        """Test that creating a type with invalid category fails."""
        with patch("api.api.deps.auth0_validator.validate_auth0_token") as mock:
            mock.return_value = admin_auth_mock(1)

            response = client.post(
                "/v1/admin/types/types",
                json={
                    "category_id": 999999,
                    "code": "TEST",
                    "name": "Test",
                },
                headers={"Authorization": "Bearer mock_token"},
            )

            assert response.status_code == 400
            assert "not found" in response.json()["detail"]

    def test_create_type_duplicate_code(
        self, client: TestClient, admin_test_data, db: Session, admin_auth_mock
    ):
        """Test that duplicate type codes are rejected."""
        existing_code = admin_test_data["type1"].code

        with patch("api.api.deps.auth0_validator.validate_auth0_token") as mock:
            mock.return_value = admin_auth_mock(1)

            response = client.post(
                "/v1/admin/types/types",
                json={
                    "category_id": admin_test_data["category1"].id,
                    "code": existing_code,
                    "name": "Duplicate",
                },
                headers={"Authorization": "Bearer mock_token"},
            )

            assert response.status_code == 400
            assert "already exists" in response.json()["detail"]


class TestAdminUpdateType:
    """Tests for PATCH /v1/admin/types/types/{type_id}."""

    def test_update_type_requires_admin(
        self, client: TestClient, admin_test_data, db: Session, non_admin_auth_mock
    ):
        """Test that non-admin users cannot update types."""
        type_id = admin_test_data["type1"].id

        with patch("api.api.deps.auth0_validator.validate_auth0_token") as mock:
            mock.return_value = non_admin_auth_mock(1)

            response = client.patch(
                f"/v1/admin/types/types/{type_id}",
                json={"name": "Updated Name"},
                headers={"Authorization": "Bearer mock_token"},
            )

            assert response.status_code == 403

    def test_update_type_success(
        self, client: TestClient, admin_test_data, db: Session, admin_auth_mock
    ):
        """Test successful type update."""
        type_id = admin_test_data["type1"].id

        with patch("api.api.deps.auth0_validator.validate_auth0_token") as mock:
            mock.return_value = admin_auth_mock(1)

            response = client.patch(
                f"/v1/admin/types/types/{type_id}",
                json={
                    "name": "Updated Type Name",
                    "description": "Updated description",
                    "legacy_physical_type": "UpdatedLegacy",
                },
                headers={"Authorization": "Bearer mock_token"},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["name"] == "Updated Type Name"
            assert data["description"] == "Updated description"
            assert data["legacy_physical_type"] == "UpdatedLegacy"

    def test_update_type_move_category(
        self, client: TestClient, admin_test_data, db: Session, admin_auth_mock
    ):
        """Test moving a type to a different category."""
        type_id = admin_test_data["type1"].id
        new_category_id = admin_test_data["category2"].id

        with patch("api.api.deps.auth0_validator.validate_auth0_token") as mock:
            mock.return_value = admin_auth_mock(1)

            response = client.patch(
                f"/v1/admin/types/types/{type_id}",
                json={"category_id": new_category_id},
                headers={"Authorization": "Bearer mock_token"},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["category"]["id"] == new_category_id

    def test_update_type_not_found(
        self, client: TestClient, db: Session, admin_auth_mock
    ):
        """Test 404 for non-existent type."""
        with patch("api.api.deps.auth0_validator.validate_auth0_token") as mock:
            mock.return_value = admin_auth_mock(1)

            response = client.patch(
                "/v1/admin/types/types/999999",
                json={"name": "Test"},
                headers={"Authorization": "Bearer mock_token"},
            )

            assert response.status_code == 404


class TestAdminDeleteType:
    """Tests for DELETE /v1/admin/types/types/{type_id}."""

    def test_delete_type_requires_admin(
        self, client: TestClient, admin_test_data, db: Session, non_admin_auth_mock
    ):
        """Test that non-admin users cannot delete types."""
        type_id = admin_test_data["type1"].id

        with patch("api.api.deps.auth0_validator.validate_auth0_token") as mock:
            mock.return_value = non_admin_auth_mock(1)

            response = client.delete(
                f"/v1/admin/types/types/{type_id}",
                headers={"Authorization": "Bearer mock_token"},
            )

            assert response.status_code == 403

    def test_delete_type_success(
        self, client: TestClient, admin_test_data, db: Session, admin_auth_mock
    ):
        """Test successful type deletion."""
        # Create a new type to delete (to avoid affecting other tests)
        new_type = TrigType(
            category_id=admin_test_data["category1"].id,
            code=f"DELTYPE_{uuid.uuid4().hex[:6]}",
            name="Type to Delete",
            sort_order=99,
        )
        db.add(new_type)
        db.commit()
        type_id = new_type.id

        with patch("api.api.deps.auth0_validator.validate_auth0_token") as mock:
            mock.return_value = admin_auth_mock(1)

            response = client.delete(
                f"/v1/admin/types/types/{type_id}",
                headers={"Authorization": "Bearer mock_token"},
            )

            assert response.status_code == 204

            # Verify deletion
            deleted = db.query(TrigType).filter(TrigType.id == type_id).first()
            assert deleted is None

    def test_delete_type_not_found(
        self, client: TestClient, db: Session, admin_auth_mock
    ):
        """Test 404 for non-existent type."""
        with patch("api.api.deps.auth0_validator.validate_auth0_token") as mock:
            mock.return_value = admin_auth_mock(1)

            response = client.delete(
                "/v1/admin/types/types/999999",
                headers={"Authorization": "Bearer mock_token"},
            )

            assert response.status_code == 404


class TestAdminReorderTypes:
    """Tests for POST /v1/admin/types/types/reorder."""

    def test_reorder_types_requires_admin(
        self, client: TestClient, admin_test_data, db: Session, non_admin_auth_mock
    ):
        """Test that non-admin users cannot reorder types."""
        with patch("api.api.deps.auth0_validator.validate_auth0_token") as mock:
            mock.return_value = non_admin_auth_mock(1)

            response = client.post(
                "/v1/admin/types/types/reorder",
                json={
                    "category_id": admin_test_data["category1"].id,
                    "order": [1, 2],
                },
                headers={"Authorization": "Bearer mock_token"},
            )

            assert response.status_code == 403

    def test_reorder_types_success(
        self, client: TestClient, admin_test_data, db: Session, admin_auth_mock
    ):
        """Test successful type reordering within a category."""
        category_id = admin_test_data["category1"].id
        type1_id = admin_test_data["type1"].id
        type2_id = admin_test_data["type2"].id

        with patch("api.api.deps.auth0_validator.validate_auth0_token") as mock:
            mock.return_value = admin_auth_mock(1)

            # Reverse the order
            response = client.post(
                "/v1/admin/types/types/reorder",
                json={"category_id": category_id, "order": [type2_id, type1_id]},
                headers={"Authorization": "Bearer mock_token"},
            )

            assert response.status_code == 200
            data = response.json()

            # Find our types in response
            type1_result = next((t for t in data if t["id"] == type1_id), None)
            type2_result = next((t for t in data if t["id"] == type2_id), None)

            # type2 should now have lower sort_order (1) than type1 (2)
            assert type2_result is not None
            assert type1_result is not None
            assert type2_result["sort_order"] == 1
            assert type1_result["sort_order"] == 2

    def test_reorder_types_wrong_category(
        self, client: TestClient, admin_test_data, db: Session, admin_auth_mock
    ):
        """Test that reordering types from wrong category fails."""
        category1_id = admin_test_data["category1"].id
        type3_id = admin_test_data["type3"].id  # In category2

        with patch("api.api.deps.auth0_validator.validate_auth0_token") as mock:
            mock.return_value = admin_auth_mock(1)

            response = client.post(
                "/v1/admin/types/types/reorder",
                json={"category_id": category1_id, "order": [type3_id]},
                headers={"Authorization": "Bearer mock_token"},
            )

            assert response.status_code == 400
            assert "does not belong to category" in response.json()["detail"]


class TestAdminGetTypeUsage:
    """Tests for GET /v1/admin/types/types/{type_id}/usage."""

    def test_get_type_usage_requires_admin(
        self, client: TestClient, admin_test_data, db: Session, non_admin_auth_mock
    ):
        """Test that non-admin users cannot get type usage."""
        type_id = admin_test_data["type1"].id

        with patch("api.api.deps.auth0_validator.validate_auth0_token") as mock:
            mock.return_value = non_admin_auth_mock(1)

            response = client.get(
                f"/v1/admin/types/types/{type_id}/usage",
                headers={"Authorization": "Bearer mock_token"},
            )

            assert response.status_code == 403

    def test_get_type_usage_success(
        self, client: TestClient, admin_test_data, db: Session, admin_auth_mock
    ):
        """Test successful type usage query."""
        type_id = admin_test_data["type1"].id

        with patch("api.api.deps.auth0_validator.validate_auth0_token") as mock:
            mock.return_value = admin_auth_mock(1)

            response = client.get(
                f"/v1/admin/types/types/{type_id}/usage",
                headers={"Authorization": "Bearer mock_token"},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["type_id"] == type_id
            assert "usage_count" in data
            assert isinstance(data["usage_count"], int)

    def test_get_type_usage_not_found(
        self, client: TestClient, db: Session, admin_auth_mock
    ):
        """Test 404 for non-existent type."""
        with patch("api.api.deps.auth0_validator.validate_auth0_token") as mock:
            mock.return_value = admin_auth_mock(1)

            response = client.get(
                "/v1/admin/types/types/999999/usage",
                headers={"Authorization": "Bearer mock_token"},
            )

            assert response.status_code == 404
