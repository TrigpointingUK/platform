"""
Tests for the /v1/conditions endpoint.

Tests public condition lookup queries.
"""

import pytest
from fastapi.testclient import TestClient

from api.models.condition import Condition


def _get_unique_sort_orders(db, count: int = 2) -> list[int]:
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


def _get_unique_codes(db, count: int = 3) -> list[str]:
    """Find unique single-letter codes that don't exist in the database."""
    existing = {row[0] for row in db.query(Condition.code).all()}
    # Use letters from end of alphabet to avoid collisions with real data
    available = [chr(i) for i in range(ord("Z"), ord("A") - 1, -1)]
    codes = [c for c in available if c not in existing][:count]
    if len(codes) < count:
        raise ValueError("Not enough available condition codes for testing")
    return codes


@pytest.fixture
def condition_test_data(db):
    """Create test conditions for endpoint testing."""
    sort_orders = _get_unique_sort_orders(db, count=3)
    codes = _get_unique_codes(db, count=3)

    # Create test conditions
    condition1 = Condition(
        code=codes[0],
        name=f"Test Condition {codes[0]}",
        description=f"Description for condition {codes[0]}",
        icon_file=f"c_test_{codes[0].lower()}.png",
        trig_colour="green",
        log_colour="blue",
        similar_codes=codes[1],
        wiki_url=f"https://example.com/condition/{codes[0].lower()}",
        sort_order=sort_orders[0],
    )
    condition2 = Condition(
        code=codes[1],
        name=f"Test Condition {codes[1]}",
        description=f"Description for condition {codes[1]}",
        icon_file=f"c_test_{codes[1].lower()}.png",
        trig_colour="red",
        log_colour="orange",
        similar_codes=codes[0],
        wiki_url=f"https://example.com/condition/{codes[1].lower()}",
        sort_order=sort_orders[1],
    )
    condition3 = Condition(
        code=codes[2],
        name=f"Test Condition {codes[2]}",
        description=None,  # Test nullable fields
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


class TestListConditions:
    """Tests for GET /v1/conditions."""

    def test_list_conditions_returns_data(
        self, client: TestClient, condition_test_data, db
    ):
        """Test that listing conditions returns test data."""
        response = client.get("/v1/conditions")

        assert response.status_code == 200
        data = response.json()

        # Should return a list
        assert isinstance(data, list)

        # Find our test conditions in the response
        codes = condition_test_data["codes"]
        our_conditions = [c for c in data if c["code"] in codes]

        # We should have our 3 test conditions
        assert len(our_conditions) == 3

    def test_list_conditions_structure(
        self, client: TestClient, condition_test_data, db
    ):
        """Test that condition response has correct structure."""
        response = client.get("/v1/conditions")

        assert response.status_code == 200
        data = response.json()

        codes = condition_test_data["codes"]
        condition = next((c for c in data if c["code"] == codes[0]), None)

        assert condition is not None
        # Check all required fields
        assert "code" in condition
        assert "name" in condition
        assert "description" in condition
        assert "icon_file" in condition
        assert "trig_colour" in condition
        assert "log_colour" in condition
        assert "similar_codes" in condition
        assert "wiki_url" in condition
        assert "sort_order" in condition

    def test_list_conditions_ordered_by_sort_order(
        self, client: TestClient, condition_test_data, db
    ):
        """Test that conditions are ordered by sort_order."""
        response = client.get("/v1/conditions")

        assert response.status_code == 200
        data = response.json()

        # Check that sort_orders are in ascending order
        sort_orders = [c["sort_order"] for c in data]
        assert sort_orders == sorted(sort_orders)

    def test_list_conditions_nullable_fields(
        self, client: TestClient, condition_test_data, db
    ):
        """Test that nullable fields are handled correctly."""
        response = client.get("/v1/conditions")

        assert response.status_code == 200
        data = response.json()

        # Find condition3 which has null values
        codes = condition_test_data["codes"]
        condition3 = next((c for c in data if c["code"] == codes[2]), None)

        assert condition3 is not None
        assert condition3["description"] is None
        assert condition3["icon_file"] is None
        assert condition3["trig_colour"] is None
        assert condition3["log_colour"] is None
        assert condition3["similar_codes"] is None
        assert condition3["wiki_url"] is None


class TestGetConditionByCode:
    """Tests for GET /v1/conditions/{code}."""

    def test_get_condition_by_code(self, client: TestClient, condition_test_data, db):
        """Test fetching a specific condition by code."""
        code = condition_test_data["codes"][0]

        response = client.get(f"/v1/conditions/{code}")

        assert response.status_code == 200
        data = response.json()

        assert data["code"] == code
        assert data["name"] == f"Test Condition {code}"
        assert data["description"] == f"Description for condition {code}"
        assert data["icon_file"] == f"c_test_{code.lower()}.png"
        assert data["trig_colour"] == "green"
        assert data["log_colour"] == "blue"

    def test_get_condition_case_insensitive(
        self, client: TestClient, condition_test_data, db
    ):
        """Test that condition lookup is case-insensitive."""
        code = condition_test_data["codes"][0]

        # Try lowercase
        response = client.get(f"/v1/conditions/{code.lower()}")

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == code.upper()

    def test_get_condition_not_found(self, client: TestClient, db):
        """Test 404 for non-existent condition."""
        response = client.get("/v1/conditions/9")  # 9 is unlikely to exist

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()


class TestConditionResponseStructure:
    """Tests for response structure validation."""

    def test_condition_response_structure(
        self, client: TestClient, condition_test_data, db
    ):
        """Test ConditionResponse structure."""
        code = condition_test_data["codes"][0]

        response = client.get(f"/v1/conditions/{code}")

        assert response.status_code == 200
        data = response.json()

        # Required fields
        assert isinstance(data["code"], str)
        assert len(data["code"]) == 1
        assert isinstance(data["name"], str)
        assert isinstance(data["sort_order"], int)

        # Optional fields (can be None or their type)
        assert data["description"] is None or isinstance(data["description"], str)
        assert data["icon_file"] is None or isinstance(data["icon_file"], str)
        assert data["trig_colour"] is None or isinstance(data["trig_colour"], str)
        assert data["log_colour"] is None or isinstance(data["log_colour"], str)
        assert data["similar_codes"] is None or isinstance(data["similar_codes"], str)
        assert data["wiki_url"] is None or isinstance(data["wiki_url"], str)

    def test_condition_code_is_uppercase(
        self, client: TestClient, condition_test_data, db
    ):
        """Test that condition codes are always uppercase."""
        response = client.get("/v1/conditions")

        assert response.status_code == 200
        data = response.json()

        for condition in data:
            assert condition["code"] == condition["code"].upper()
            assert len(condition["code"]) == 1


class TestConditionsNoAuth:
    """Tests to verify endpoints work without authentication."""

    def test_list_conditions_no_auth(self, client: TestClient, condition_test_data, db):
        """Test that listing conditions doesn't require authentication."""
        # No Authorization header
        response = client.get("/v1/conditions")

        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_get_condition_no_auth(self, client: TestClient, condition_test_data, db):
        """Test that getting a condition doesn't require authentication."""
        code = condition_test_data["codes"][0]

        # No Authorization header
        response = client.get(f"/v1/conditions/{code}")

        assert response.status_code == 200
        assert response.json()["code"] == code


class TestConditionFieldValues:
    """Tests for specific field value validation."""

    def test_condition_with_all_colours(
        self, client: TestClient, condition_test_data, db
    ):
        """Test condition with both trig_colour and log_colour set."""
        code = condition_test_data["codes"][0]

        response = client.get(f"/v1/conditions/{code}")

        assert response.status_code == 200
        data = response.json()

        assert data["trig_colour"] == "green"
        assert data["log_colour"] == "blue"

    def test_condition_with_similar_codes(
        self, client: TestClient, condition_test_data, db
    ):
        """Test condition with similar_codes set."""
        code = condition_test_data["codes"][0]
        expected_similar = condition_test_data["codes"][1]

        response = client.get(f"/v1/conditions/{code}")

        assert response.status_code == 200
        data = response.json()

        assert data["similar_codes"] == expected_similar

    def test_condition_with_wiki_url(self, client: TestClient, condition_test_data, db):
        """Test condition with wiki_url set."""
        code = condition_test_data["codes"][0]

        response = client.get(f"/v1/conditions/{code}")

        assert response.status_code == 200
        data = response.json()

        assert data["wiki_url"] is not None
        assert data["wiki_url"].startswith("https://")

    def test_condition_with_icon_file(
        self, client: TestClient, condition_test_data, db
    ):
        """Test condition with icon_file set."""
        code = condition_test_data["codes"][0]

        response = client.get(f"/v1/conditions/{code}")

        assert response.status_code == 200
        data = response.json()

        assert data["icon_file"] is not None
        assert data["icon_file"].endswith(".png")
