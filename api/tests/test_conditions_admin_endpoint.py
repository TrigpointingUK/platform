"""
Tests for the /v1/admin/condition endpoint.

Tests admin CRUD operations for conditions.
"""

import uuid
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from api.models.condition import Condition
from api.models.user import TLog


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
def admin_user(db: Session):
    """Create an admin user for testing."""
    from api.crud.user import create_user

    unique_suffix = uuid.uuid4().hex[:8]
    user = create_user(
        db=db,
        username=f"cond_admin_{unique_suffix}",
        email=f"cond_admin_{unique_suffix}@example.com",
        auth0_user_id=f"auth0|cond_admin_{unique_suffix}",
    )
    return user


@pytest.fixture
def non_admin_user(db: Session):
    """Create a non-admin user for testing."""
    from api.crud.user import create_user

    unique_suffix = uuid.uuid4().hex[:8]
    user = create_user(
        db=db,
        username=f"cond_user_{unique_suffix}",
        email=f"cond_user_{unique_suffix}@example.com",
        auth0_user_id=f"auth0|cond_user_{unique_suffix}",
    )
    return user


@pytest.fixture
def admin_auth_mock(admin_user):
    """Mock authentication to return admin token using real user."""

    def _mock():
        return {
            "token_type": "auth0",
            "auth0_user_id": admin_user.auth0_user_id,
            "sub": admin_user.auth0_user_id,
            "scope": "api:write api:admin",
        }

    return _mock


@pytest.fixture
def non_admin_auth_mock(non_admin_user):
    """Mock authentication to return non-admin token using real user."""

    def _mock():
        return {
            "token_type": "auth0",
            "auth0_user_id": non_admin_user.auth0_user_id,
            "sub": non_admin_user.auth0_user_id,
            "scope": "api:write",  # Missing api:admin
        }

    return _mock


@pytest.fixture
def condition_admin_test_data(db: Session):
    """Create test conditions for admin endpoint testing."""
    sort_orders = _get_unique_sort_orders(db, count=3)
    codes = _get_unique_codes(db, count=3)

    condition1 = Condition(
        code=codes[0],
        name=f"Admin Test Condition {codes[0]}",
        description=f"Description for admin condition {codes[0]}",
        icon_file=f"c_admin_{codes[0].lower()}.png",
        trig_colour="green",
        log_colour="blue",
        similar_codes=codes[1],
        wiki_url=f"https://example.com/admin/{codes[0].lower()}",
        sort_order=sort_orders[0],
    )
    condition2 = Condition(
        code=codes[1],
        name=f"Admin Test Condition {codes[1]}",
        description=f"Description for admin condition {codes[1]}",
        icon_file=f"c_admin_{codes[1].lower()}.png",
        trig_colour="red",
        log_colour="orange",
        similar_codes=codes[0],
        wiki_url=f"https://example.com/admin/{codes[1].lower()}",
        sort_order=sort_orders[1],
    )
    condition3 = Condition(
        code=codes[2],
        name=f"Admin Test Condition {codes[2]}",
        description=None,
        icon_file=None,
        trig_colour=None,
        log_colour=None,
        similar_codes=None,
        wiki_url=None,
        sort_order=sort_orders[2],
    )

    db.add(condition1)
    db.add(condition2)
    db.add(condition3)
    db.commit()

    return {
        "condition1": condition1,
        "condition2": condition2,
        "condition3": condition3,
        "codes": codes,
        "sort_orders": sort_orders,
    }


class TestAdminGetConditions:
    """Tests for GET /v1/admin/condition/conditions."""

    def test_get_conditions_requires_admin(
        self,
        client: TestClient,
        condition_admin_test_data,
        db: Session,
        non_admin_auth_mock,
    ):
        """Test that non-admin users cannot access admin conditions endpoint."""
        with patch("api.api.deps.auth0_validator.validate_auth0_token") as mock:
            mock.return_value = non_admin_auth_mock()

            response = client.get(
                "/v1/admin/condition/conditions",
                headers={"Authorization": "Bearer mock_token"},
            )

            assert response.status_code == 403

    def test_get_conditions_as_admin(
        self,
        client: TestClient,
        condition_admin_test_data,
        db: Session,
        admin_auth_mock,
    ):
        """Test that admin users can get conditions."""
        with patch("api.api.deps.auth0_validator.validate_auth0_token") as mock:
            mock.return_value = admin_auth_mock()

            response = client.get(
                "/v1/admin/condition/conditions",
                headers={"Authorization": "Bearer mock_token"},
            )

            assert response.status_code == 200
            data = response.json()
            assert isinstance(data, list)

            # Find our test conditions
            codes = condition_admin_test_data["codes"]
            our_conditions = [c for c in data if c["code"] in codes]
            assert len(our_conditions) == 3


class TestAdminCreateCondition:
    """Tests for POST /v1/admin/condition/conditions."""

    def test_create_condition_requires_admin(
        self, client: TestClient, db: Session, non_admin_auth_mock
    ):
        """Test that non-admin users cannot create conditions."""
        with patch("api.api.deps.auth0_validator.validate_auth0_token") as mock:
            mock.return_value = non_admin_auth_mock()

            response = client.post(
                "/v1/admin/condition/conditions",
                json={"code": "X", "name": "Test", "sort_order": 100},
                headers={"Authorization": "Bearer mock_token"},
            )

            assert response.status_code == 403

    def test_create_condition_success(
        self, client: TestClient, db: Session, admin_auth_mock
    ):
        """Test successful condition creation."""
        # Find an unused code
        codes = _get_unique_codes(db, count=1)
        unique_code = codes[0]

        with patch("api.api.deps.auth0_validator.validate_auth0_token") as mock:
            mock.return_value = admin_auth_mock()

            response = client.post(
                "/v1/admin/condition/conditions",
                json={
                    "code": unique_code,
                    "name": "New Test Condition",
                    "sort_order": 9999,
                    "description": "A new test condition",
                    "icon_file": "c_new.png",
                    "trig_colour": "purple",
                    "log_colour": "pink",
                    "similar_codes": "AB",
                    "wiki_url": "https://example.com/new",
                },
                headers={"Authorization": "Bearer mock_token"},
            )

            assert response.status_code == 201
            data = response.json()
            assert data["code"] == unique_code.upper()
            assert data["name"] == "New Test Condition"
            assert data["sort_order"] == 9999
            assert data["description"] == "A new test condition"
            assert data["icon_file"] == "c_new.png"
            assert data["trig_colour"] == "purple"
            assert data["log_colour"] == "pink"
            assert data["similar_codes"] == "AB"
            assert data["wiki_url"] == "https://example.com/new"

    def test_create_condition_minimal(
        self, client: TestClient, db: Session, admin_auth_mock
    ):
        """Test creating condition with only required fields."""
        codes = _get_unique_codes(db, count=1)
        unique_code = codes[0]

        with patch("api.api.deps.auth0_validator.validate_auth0_token") as mock:
            mock.return_value = admin_auth_mock()

            response = client.post(
                "/v1/admin/condition/conditions",
                json={
                    "code": unique_code,
                    "name": "Minimal Condition",
                    "sort_order": 9998,
                },
                headers={"Authorization": "Bearer mock_token"},
            )

            assert response.status_code == 201
            data = response.json()
            assert data["code"] == unique_code.upper()
            assert data["name"] == "Minimal Condition"
            assert data["description"] is None
            assert data["icon_file"] is None

    def test_create_condition_duplicate_code(
        self,
        client: TestClient,
        condition_admin_test_data,
        db: Session,
        admin_auth_mock,
    ):
        """Test that duplicate codes are rejected."""
        existing_code = condition_admin_test_data["codes"][0]

        with patch("api.api.deps.auth0_validator.validate_auth0_token") as mock:
            mock.return_value = admin_auth_mock()

            response = client.post(
                "/v1/admin/condition/conditions",
                json={"code": existing_code, "name": "Duplicate", "sort_order": 100},
                headers={"Authorization": "Bearer mock_token"},
            )

            assert response.status_code == 400
            assert "already exists" in response.json()["detail"]

    def test_create_condition_invalid_code_format(
        self, client: TestClient, db: Session, admin_auth_mock
    ):
        """Test that invalid code formats are rejected."""
        with patch("api.api.deps.auth0_validator.validate_auth0_token") as mock:
            mock.return_value = admin_auth_mock()

            # Code too long
            response = client.post(
                "/v1/admin/condition/conditions",
                json={"code": "AB", "name": "Test", "sort_order": 100},
                headers={"Authorization": "Bearer mock_token"},
            )

            assert response.status_code == 422  # Validation error

    def test_create_condition_lowercase_code_rejected(
        self, client: TestClient, db: Session, admin_auth_mock
    ):
        """Test that lowercase codes are rejected (must be uppercase A-Z)."""
        with patch("api.api.deps.auth0_validator.validate_auth0_token") as mock:
            mock.return_value = admin_auth_mock()

            response = client.post(
                "/v1/admin/condition/conditions",
                json={
                    "code": "a",  # lowercase - should be rejected
                    "name": "Lowercase Code Test",
                    "sort_order": 9997,
                },
                headers={"Authorization": "Bearer mock_token"},
            )

            assert response.status_code == 422  # Validation error

    def test_create_condition_numeric_code_rejected(
        self, client: TestClient, db: Session, admin_auth_mock
    ):
        """Test that numeric codes are rejected."""
        with patch("api.api.deps.auth0_validator.validate_auth0_token") as mock:
            mock.return_value = admin_auth_mock()

            response = client.post(
                "/v1/admin/condition/conditions",
                json={
                    "code": "1",
                    "name": "Numeric Code Test",
                    "sort_order": 9997,
                },
                headers={"Authorization": "Bearer mock_token"},
            )

            assert response.status_code == 422

    def test_create_condition_special_char_code_rejected(
        self, client: TestClient, db: Session, admin_auth_mock
    ):
        """Test that special character codes are rejected."""
        with patch("api.api.deps.auth0_validator.validate_auth0_token") as mock:
            mock.return_value = admin_auth_mock()

            response = client.post(
                "/v1/admin/condition/conditions",
                json={
                    "code": "!",
                    "name": "Special Char Code Test",
                    "sort_order": 9997,
                },
                headers={"Authorization": "Bearer mock_token"},
            )

            assert response.status_code == 422

    def test_create_condition_empty_code_rejected(
        self, client: TestClient, db: Session, admin_auth_mock
    ):
        """Test that empty codes are rejected."""
        with patch("api.api.deps.auth0_validator.validate_auth0_token") as mock:
            mock.return_value = admin_auth_mock()

            response = client.post(
                "/v1/admin/condition/conditions",
                json={
                    "code": "",
                    "name": "Empty Code Test",
                    "sort_order": 9997,
                },
                headers={"Authorization": "Bearer mock_token"},
            )

            assert response.status_code == 422

    def test_create_condition_negative_sort_order_rejected(
        self, client: TestClient, db: Session, admin_auth_mock
    ):
        """Test that negative sort_order is rejected."""
        codes = _get_unique_codes(db, count=1)

        with patch("api.api.deps.auth0_validator.validate_auth0_token") as mock:
            mock.return_value = admin_auth_mock()

            response = client.post(
                "/v1/admin/condition/conditions",
                json={
                    "code": codes[0],
                    "name": "Negative Sort Test",
                    "sort_order": -1,
                },
                headers={"Authorization": "Bearer mock_token"},
            )

            assert response.status_code == 422

    def test_create_condition_sort_order_too_large_rejected(
        self, client: TestClient, db: Session, admin_auth_mock
    ):
        """Test that sort_order > 32767 is rejected."""
        codes = _get_unique_codes(db, count=1)

        with patch("api.api.deps.auth0_validator.validate_auth0_token") as mock:
            mock.return_value = admin_auth_mock()

            response = client.post(
                "/v1/admin/condition/conditions",
                json={
                    "code": codes[0],
                    "name": "Large Sort Test",
                    "sort_order": 32768,
                },
                headers={"Authorization": "Bearer mock_token"},
            )

            assert response.status_code == 422

    def test_create_condition_name_too_long_rejected(
        self, client: TestClient, db: Session, admin_auth_mock
    ):
        """Test that name > 50 characters is rejected."""
        codes = _get_unique_codes(db, count=1)

        with patch("api.api.deps.auth0_validator.validate_auth0_token") as mock:
            mock.return_value = admin_auth_mock()

            response = client.post(
                "/v1/admin/condition/conditions",
                json={
                    "code": codes[0],
                    "name": "A" * 51,  # 51 characters
                    "sort_order": 100,
                },
                headers={"Authorization": "Bearer mock_token"},
            )

            assert response.status_code == 422

    def test_create_condition_description_too_long_rejected(
        self, client: TestClient, db: Session, admin_auth_mock
    ):
        """Test that description > 255 characters is rejected."""
        codes = _get_unique_codes(db, count=1)

        with patch("api.api.deps.auth0_validator.validate_auth0_token") as mock:
            mock.return_value = admin_auth_mock()

            response = client.post(
                "/v1/admin/condition/conditions",
                json={
                    "code": codes[0],
                    "name": "Description Test",
                    "sort_order": 100,
                    "description": "A" * 256,  # 256 characters
                },
                headers={"Authorization": "Bearer mock_token"},
            )

            assert response.status_code == 422


class TestAdminUpdateCondition:
    """Tests for PATCH /v1/admin/condition/conditions/{code}."""

    def test_update_condition_requires_admin(
        self,
        client: TestClient,
        condition_admin_test_data,
        db: Session,
        non_admin_auth_mock,
    ):
        """Test that non-admin users cannot update conditions."""
        code = condition_admin_test_data["codes"][0]

        with patch("api.api.deps.auth0_validator.validate_auth0_token") as mock:
            mock.return_value = non_admin_auth_mock()

            response = client.patch(
                f"/v1/admin/condition/conditions/{code}",
                json={"name": "Updated Name"},
                headers={"Authorization": "Bearer mock_token"},
            )

            assert response.status_code == 403

    def test_update_condition_success(
        self,
        client: TestClient,
        condition_admin_test_data,
        db: Session,
        admin_auth_mock,
    ):
        """Test successful condition update."""
        code = condition_admin_test_data["codes"][0]

        with patch("api.api.deps.auth0_validator.validate_auth0_token") as mock:
            mock.return_value = admin_auth_mock()

            response = client.patch(
                f"/v1/admin/condition/conditions/{code}",
                json={
                    "name": "Updated Condition Name",
                    "description": "Updated description",
                    "trig_colour": "yellow",
                },
                headers={"Authorization": "Bearer mock_token"},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["name"] == "Updated Condition Name"
            assert data["description"] == "Updated description"
            assert data["trig_colour"] == "yellow"

    def test_update_condition_partial(
        self,
        client: TestClient,
        condition_admin_test_data,
        db: Session,
        admin_auth_mock,
    ):
        """Test partial condition update (only some fields)."""
        code = condition_admin_test_data["codes"][0]
        original_name = condition_admin_test_data["condition1"].name

        with patch("api.api.deps.auth0_validator.validate_auth0_token") as mock:
            mock.return_value = admin_auth_mock()

            # Only update description
            response = client.patch(
                f"/v1/admin/condition/conditions/{code}",
                json={"description": "Only description updated"},
                headers={"Authorization": "Bearer mock_token"},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["description"] == "Only description updated"
            # Name should be unchanged
            assert data["name"] == original_name

    def test_update_condition_case_insensitive(
        self,
        client: TestClient,
        condition_admin_test_data,
        db: Session,
        admin_auth_mock,
    ):
        """Test that code lookup is case-insensitive."""
        code = condition_admin_test_data["codes"][0].lower()  # Use lowercase

        with patch("api.api.deps.auth0_validator.validate_auth0_token") as mock:
            mock.return_value = admin_auth_mock()

            response = client.patch(
                f"/v1/admin/condition/conditions/{code}",
                json={"description": "Updated via lowercase"},
                headers={"Authorization": "Bearer mock_token"},
            )

            assert response.status_code == 200

    def test_update_condition_not_found(
        self, client: TestClient, db: Session, admin_auth_mock
    ):
        """Test 404 for non-existent condition."""
        with patch("api.api.deps.auth0_validator.validate_auth0_token") as mock:
            mock.return_value = admin_auth_mock()

            response = client.patch(
                "/v1/admin/condition/conditions/9",
                json={"name": "Test"},
                headers={"Authorization": "Bearer mock_token"},
            )

            assert response.status_code == 404

    def test_update_condition_name_too_long_rejected(
        self,
        client: TestClient,
        condition_admin_test_data,
        db: Session,
        admin_auth_mock,
    ):
        """Test that name > 50 characters is rejected on update."""
        code = condition_admin_test_data["codes"][0]

        with patch("api.api.deps.auth0_validator.validate_auth0_token") as mock:
            mock.return_value = admin_auth_mock()

            response = client.patch(
                f"/v1/admin/condition/conditions/{code}",
                json={"name": "A" * 51},
                headers={"Authorization": "Bearer mock_token"},
            )

            assert response.status_code == 422

    def test_update_condition_sort_order(
        self,
        client: TestClient,
        condition_admin_test_data,
        db: Session,
        admin_auth_mock,
    ):
        """Test updating sort_order."""
        code = condition_admin_test_data["codes"][0]

        with patch("api.api.deps.auth0_validator.validate_auth0_token") as mock:
            mock.return_value = admin_auth_mock()

            response = client.patch(
                f"/v1/admin/condition/conditions/{code}",
                json={"sort_order": 12345},
                headers={"Authorization": "Bearer mock_token"},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["sort_order"] == 12345

    def test_update_condition_all_fields(
        self,
        client: TestClient,
        condition_admin_test_data,
        db: Session,
        admin_auth_mock,
    ):
        """Test updating all fields at once."""
        code = condition_admin_test_data["codes"][0]

        with patch("api.api.deps.auth0_validator.validate_auth0_token") as mock:
            mock.return_value = admin_auth_mock()

            response = client.patch(
                f"/v1/admin/condition/conditions/{code}",
                json={
                    "name": "Fully Updated",
                    "description": "New description",
                    "icon_file": "new_icon.png",
                    "trig_colour": "purple",
                    "log_colour": "cyan",
                    "similar_codes": "XY",
                    "wiki_url": "https://example.com/updated",
                    "sort_order": 999,
                },
                headers={"Authorization": "Bearer mock_token"},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["name"] == "Fully Updated"
            assert data["description"] == "New description"
            assert data["icon_file"] == "new_icon.png"
            assert data["trig_colour"] == "purple"
            assert data["log_colour"] == "cyan"
            assert data["similar_codes"] == "XY"
            assert data["wiki_url"] == "https://example.com/updated"
            assert data["sort_order"] == 999


class TestAdminDeleteCondition:
    """Tests for DELETE /v1/admin/condition/conditions/{code}."""

    def test_delete_condition_requires_admin(
        self,
        client: TestClient,
        condition_admin_test_data,
        db: Session,
        non_admin_auth_mock,
    ):
        """Test that non-admin users cannot delete conditions."""
        code = condition_admin_test_data["codes"][0]

        with patch("api.api.deps.auth0_validator.validate_auth0_token") as mock:
            mock.return_value = non_admin_auth_mock()

            response = client.delete(
                f"/v1/admin/condition/conditions/{code}",
                headers={"Authorization": "Bearer mock_token"},
            )

            assert response.status_code == 403

    def test_delete_condition_success(
        self, client: TestClient, db: Session, admin_auth_mock
    ):
        """Test successful condition deletion."""
        # Create a new condition to delete
        codes = _get_unique_codes(db, count=1)
        delete_code = codes[0]
        new_condition = Condition(
            code=delete_code,
            name="Condition to Delete",
            sort_order=9996,
        )
        db.add(new_condition)
        db.commit()

        with patch("api.api.deps.auth0_validator.validate_auth0_token") as mock:
            mock.return_value = admin_auth_mock()

            response = client.delete(
                f"/v1/admin/condition/conditions/{delete_code}",
                headers={"Authorization": "Bearer mock_token"},
            )

            assert response.status_code == 204

            # Verify deletion
            deleted = db.query(Condition).filter(Condition.code == delete_code).first()
            assert deleted is None

    def test_delete_condition_not_found(
        self, client: TestClient, db: Session, admin_auth_mock
    ):
        """Test 404 for non-existent condition."""
        with patch("api.api.deps.auth0_validator.validate_auth0_token") as mock:
            mock.return_value = admin_auth_mock()

            response = client.delete(
                "/v1/admin/condition/conditions/9",
                headers={"Authorization": "Bearer mock_token"},
            )

            assert response.status_code == 404

    def test_delete_condition_in_use_fails(
        self, client: TestClient, db: Session, admin_auth_mock, admin_user
    ):
        """Test that deleting a condition in use by logs fails."""
        from datetime import date

        from api.models.trig import Trig

        # Create a condition to test with
        codes = _get_unique_codes(db, count=1)
        condition_code = codes[0]
        sort_orders = _get_unique_sort_orders(db, count=1)

        condition = Condition(
            code=condition_code,
            name="Condition In Use",
            sort_order=sort_orders[0],
        )
        db.add(condition)
        db.flush()

        # Find an existing trig to use (or create one if needed)
        trig = db.query(Trig).first()
        if not trig:
            # Skip test if no trigs exist
            db.rollback()
            return

        # Create a log using this condition
        log = TLog(
            trig_id=trig.id,
            user_id=admin_user.id,
            date=date.today(),
            condition=condition_code,
            comment="Test log for condition deletion test",
        )
        db.add(log)
        db.commit()

        try:
            with patch("api.api.deps.auth0_validator.validate_auth0_token") as mock:
                mock.return_value = {
                    "token_type": "auth0",
                    "auth0_user_id": admin_user.auth0_user_id,
                    "sub": admin_user.auth0_user_id,
                    "scope": "api:write api:admin",
                }

                response = client.delete(
                    f"/v1/admin/condition/conditions/{condition_code}",
                    headers={"Authorization": "Bearer mock_token"},
                )

                assert response.status_code == 400
                assert "used by" in response.json()["detail"].lower()
        finally:
            # Clean up the log
            db.delete(log)
            db.commit()


class TestAdminGetConditionUsage:
    """Tests for GET /v1/admin/condition/conditions/{code}/usage."""

    def test_get_condition_usage_requires_admin(
        self,
        client: TestClient,
        condition_admin_test_data,
        db: Session,
        non_admin_auth_mock,
    ):
        """Test that non-admin users cannot get condition usage."""
        code = condition_admin_test_data["codes"][0]

        with patch("api.api.deps.auth0_validator.validate_auth0_token") as mock:
            mock.return_value = non_admin_auth_mock()

            response = client.get(
                f"/v1/admin/condition/conditions/{code}/usage",
                headers={"Authorization": "Bearer mock_token"},
            )

            assert response.status_code == 403

    def test_get_condition_usage_success(
        self,
        client: TestClient,
        condition_admin_test_data,
        db: Session,
        admin_auth_mock,
    ):
        """Test successful condition usage query."""
        code = condition_admin_test_data["codes"][0]

        with patch("api.api.deps.auth0_validator.validate_auth0_token") as mock:
            mock.return_value = admin_auth_mock()

            response = client.get(
                f"/v1/admin/condition/conditions/{code}/usage",
                headers={"Authorization": "Bearer mock_token"},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["code"] == code.upper()
            assert "usage_count" in data
            assert isinstance(data["usage_count"], int)
            assert data["usage_count"] >= 0

    def test_get_condition_usage_not_found(
        self, client: TestClient, db: Session, admin_auth_mock
    ):
        """Test 404 for non-existent condition."""
        with patch("api.api.deps.auth0_validator.validate_auth0_token") as mock:
            mock.return_value = admin_auth_mock()

            response = client.get(
                "/v1/admin/condition/conditions/9/usage",
                headers={"Authorization": "Bearer mock_token"},
            )

            assert response.status_code == 404
