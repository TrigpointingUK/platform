"""
Tests for the /v1/areas/by-type/{type_id} endpoint.

Tests listing areas by type with alphabetical and distance-based sorting.
"""

import pytest
from fastapi.testclient import TestClient


class TestListAreasByType:
    """Tests for list_areas_by_type endpoint."""

    def test_returns_404_for_invalid_type(self, client: TestClient):
        """Returns 404 for non-existent area type ID."""
        response = client.get("/v1/areas/by-type/999999")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_returns_areas_for_existing_type(self, client: TestClient, db):
        """Returns areas for an existing area type (using real data)."""
        from api.crud.area import list_area_types

        area_types = list_area_types(db)
        if not area_types:
            pytest.skip("No area types in test database")

        area_type = area_types[0]
        response = client.get(f"/v1/areas/by-type/{area_type.id}")

        assert response.status_code == 200
        areas = response.json()
        assert isinstance(areas, list)
        # Verify response structure
        if len(areas) > 0:
            assert "id" in areas[0]
            assert "name" in areas[0]
            assert "area_type" in areas[0]

    def test_distance_sorting_parameter_accepted(self, client: TestClient, db):
        """Distance sorting parameter is accepted even without test data."""
        from api.crud.area import list_area_types

        area_types = list_area_types(db)
        if not area_types:
            pytest.skip("No area types in test database")

        area_type = area_types[0]
        # This should not error even though centroids may be null
        response = client.get(
            f"/v1/areas/by-type/{area_type.id}?order=distance&lat=51.5&lon=-0.15"
        )

        assert response.status_code == 200
