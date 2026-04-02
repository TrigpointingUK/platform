"""
Tests for the /v1/areas/by-type/{type_id} endpoint.

Tests listing areas by type with alphabetical and distance-based sorting.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from api.models.area import Area, AreaType


@pytest.fixture
def test_area_type(db: Session) -> AreaType:
    """Create a test area type."""
    area_type = AreaType(
        code="test_county",
        name="Test County",
        description="Area type for testing",
    )
    db.add(area_type)
    db.commit()
    db.refresh(area_type)
    return area_type


@pytest.fixture
def test_areas(db: Session, test_area_type: AreaType) -> list[Area]:
    """Create test areas belonging to the test area type."""
    areas = []
    for name, lat, lon in [
        ("Alpha County", 51.5, -0.15),
        ("Beta County", 52.0, -1.0),
        ("Gamma County", 53.0, -2.0),
    ]:
        area = Area(
            area_type_id=test_area_type.id,
            code=name.lower().replace(" ", "_"),
            name=name,
            boundary="SRID=4326;MULTIPOLYGON(((-1 50, 1 50, 1 52, -1 52, -1 50)))",
            center_lat=lat,
            center_lon=lon,
        )
        db.add(area)
        areas.append(area)
    db.commit()
    for area in areas:
        db.refresh(area)
    return areas


class TestListAreasByType:
    """Tests for list_areas_by_type endpoint."""

    def test_returns_404_for_invalid_type(self, client: TestClient):
        """Returns 404 for non-existent area type ID."""
        response = client.get("/v1/areas/by-type/999999")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_returns_areas_for_existing_type(
        self, client: TestClient, test_area_type, test_areas
    ):
        """Returns areas for an existing area type."""
        response = client.get(f"/v1/areas/by-type/{test_area_type.id}")

        assert response.status_code == 200
        areas = response.json()
        assert isinstance(areas, list)
        assert len(areas) == 3
        assert "id" in areas[0]
        assert "name" in areas[0]
        assert "area_type" in areas[0]

    def test_distance_sorting_parameter_accepted(
        self, client: TestClient, test_area_type, test_areas
    ):
        """Distance sorting parameter is accepted with test data."""
        response = client.get(
            f"/v1/areas/by-type/{test_area_type.id}?order=distance&lat=51.5&lon=-0.15"
        )

        assert response.status_code == 200
