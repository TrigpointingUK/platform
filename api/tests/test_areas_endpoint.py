"""
Tests for the /v1/areas endpoint.

Tests geographic area queries including:
- Finding areas containing a point
- Listing area types
- Getting area by ID
- Getting area boundaries as GeoJSON
"""

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from api.models.area import Area, AreaType


@pytest.fixture
def area_test_data(db):
    """Create test area types and areas with PostGIS boundaries."""
    unique_suffix = uuid.uuid4().hex[:6]

    # Create test area types
    area_type1 = AreaType(
        code=f"TEST_COUNTY_{unique_suffix}",
        name=f"Test County {unique_suffix}",
        description="Test county boundaries",
        source_url="https://example.com/data",
    )
    area_type2 = AreaType(
        code=f"TEST_REGION_{unique_suffix}",
        name=f"Test Region {unique_suffix}",
        description="Test region boundaries",
        source_url="https://example.com/data2",
    )
    db.add(area_type1)
    db.add(area_type2)
    db.flush()

    # Create test areas using raw SQL for PostGIS geometry
    # Area 1: A small square around London (51.5, -0.1)
    db.execute(
        text("""
            INSERT INTO area (area_type_id, code, name, boundary)
            VALUES (
                :area_type_id,
                :code,
                :name,
                ST_GeogFromText('SRID=4326;MULTIPOLYGON(((-0.2 51.4, -0.2 51.6, 0.0 51.6, 0.0 51.4, -0.2 51.4)))')
            )
        """),
        {
            "area_type_id": area_type1.id,
            "code": f"AREA1_{unique_suffix}",
            "name": f"Test Area London {unique_suffix}",
        },
    )

    # Area 2: A square around Manchester (53.5, -2.2)
    db.execute(
        text("""
            INSERT INTO area (area_type_id, code, name, boundary)
            VALUES (
                :area_type_id,
                :code,
                :name,
                ST_GeogFromText('SRID=4326;MULTIPOLYGON(((-2.4 53.3, -2.4 53.7, -2.0 53.7, -2.0 53.3, -2.4 53.3)))')
            )
        """),
        {
            "area_type_id": area_type1.id,
            "code": f"AREA2_{unique_suffix}",
            "name": f"Test Area Manchester {unique_suffix}",
        },
    )

    # Area 3: A larger region covering both (type 2)
    db.execute(
        text("""
            INSERT INTO area (area_type_id, code, name, boundary)
            VALUES (
                :area_type_id,
                :code,
                :name,
                ST_GeogFromText('SRID=4326;MULTIPOLYGON(((-3.0 50.0, -3.0 55.0, 1.0 55.0, 1.0 50.0, -3.0 50.0)))')
            )
        """),
        {
            "area_type_id": area_type2.id,
            "code": f"AREA3_{unique_suffix}",
            "name": f"Test Region England {unique_suffix}",
        },
    )

    db.commit()

    # Fetch the created areas
    area1 = db.query(Area).filter(Area.code == f"AREA1_{unique_suffix}").first()
    area2 = db.query(Area).filter(Area.code == f"AREA2_{unique_suffix}").first()
    area3 = db.query(Area).filter(Area.code == f"AREA3_{unique_suffix}").first()

    return {
        "area_type1": area_type1,
        "area_type2": area_type2,
        "area1": area1,
        "area2": area2,
        "area3": area3,
        "suffix": unique_suffix,
    }


class TestListAreaTypes:
    """Tests for GET /v1/areas/types."""

    def test_list_area_types_returns_data(self, client: TestClient, area_test_data, db):
        """Test that listing area types returns data."""
        response = client.get("/v1/areas/types")

        assert response.status_code == 200
        data = response.json()

        # Should return a list
        assert isinstance(data, list)

        # Find our test area types
        suffix = area_test_data["suffix"]
        our_types = [
            t
            for t in data
            if f"TEST_COUNTY_{suffix}" in t["code"]
            or f"TEST_REGION_{suffix}" in t["code"]
        ]

        # We should have our 2 test types
        assert len(our_types) == 2

    def test_list_area_types_structure(self, client: TestClient, area_test_data, db):
        """Test area type response structure."""
        response = client.get("/v1/areas/types")

        assert response.status_code == 200
        data = response.json()

        # Find our test type
        suffix = area_test_data["suffix"]
        our_type = next((t for t in data if t["code"] == f"TEST_COUNTY_{suffix}"), None)
        assert our_type is not None

        # Check structure
        assert "id" in our_type
        assert "code" in our_type
        assert "name" in our_type


class TestGetAreaById:
    """Tests for GET /v1/areas/{area_id}."""

    def test_get_area_by_id(self, client: TestClient, area_test_data, db):
        """Test fetching an area by ID."""
        area = area_test_data["area1"]
        response = client.get(f"/v1/areas/{area.id}")

        assert response.status_code == 200
        data = response.json()

        assert data["id"] == area.id
        assert data["name"] == area.name
        assert data["code"] == area.code

        # Check nested area_type structure
        assert "area_type" in data
        assert data["area_type"]["id"] == area_test_data["area_type1"].id
        assert data["area_type"]["code"] == area_test_data["area_type1"].code

    def test_get_area_not_found(self, client: TestClient, db):
        """Test 404 for non-existent area."""
        response = client.get("/v1/areas/999999999")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()


class TestGetAreaBoundary:
    """Tests for GET /v1/areas/{area_id}/boundary."""

    def test_get_area_boundary_geojson(self, client: TestClient, area_test_data, db):
        """Test fetching area boundary as GeoJSON."""
        area = area_test_data["area1"]
        response = client.get(f"/v1/areas/{area.id}/boundary")

        assert response.status_code == 200
        data = response.json()

        # Check main fields
        assert data["id"] == area.id
        assert data["name"] == area.name
        assert "boundary" in data

        # Check boundary is valid GeoJSON
        boundary = data["boundary"]
        assert boundary is not None
        assert boundary["type"] in ["Polygon", "MultiPolygon"]
        assert "coordinates" in boundary

    def test_get_area_boundary_not_found(self, client: TestClient, db):
        """Test 404 for non-existent area boundary."""
        response = client.get("/v1/areas/999999999/boundary")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()


class TestAreasContainingPoint:
    """Tests for GET /v1/areas/containing."""

    def test_areas_containing_point_in_london(
        self, client: TestClient, area_test_data, db
    ):
        """Test finding areas containing a point in London."""
        # Point inside our test London area
        response = client.get("/v1/areas/containing?lat=51.5&lon=-0.1")

        assert response.status_code == 200
        data = response.json()

        assert data["lat"] == 51.5
        assert data["lon"] == -0.1
        assert "groups" in data
        assert "total_areas" in data

        # Should find at least the London test area and the England region
        suffix = area_test_data["suffix"]
        found_area_names = []
        for group in data["groups"]:
            for area in group["areas"]:
                found_area_names.append(area["name"])

        # Our test areas should be found
        assert any(f"Test Area London {suffix}" in n for n in found_area_names)
        assert any(f"Test Region England {suffix}" in n for n in found_area_names)

    def test_areas_containing_point_in_manchester(
        self, client: TestClient, area_test_data, db
    ):
        """Test finding areas containing a point in Manchester."""
        # Point inside our test Manchester area
        response = client.get("/v1/areas/containing?lat=53.5&lon=-2.2")

        assert response.status_code == 200
        data = response.json()

        suffix = area_test_data["suffix"]
        found_area_names = []
        for group in data["groups"]:
            for area in group["areas"]:
                found_area_names.append(area["name"])

        # Manchester area and England region should be found
        assert any(f"Test Area Manchester {suffix}" in n for n in found_area_names)
        assert any(f"Test Region England {suffix}" in n for n in found_area_names)

        # London area should NOT be found
        assert not any(f"Test Area London {suffix}" in n for n in found_area_names)

    def test_areas_containing_point_outside_all(
        self, client: TestClient, area_test_data, db
    ):
        """Test finding areas for a point outside our test areas."""
        # Point in Scotland (not in our test areas)
        response = client.get("/v1/areas/containing?lat=56.0&lon=-4.0")

        assert response.status_code == 200
        data = response.json()

        # Should not find our test areas
        suffix = area_test_data["suffix"]
        found_area_names = []
        for group in data["groups"]:
            for area in group["areas"]:
                found_area_names.append(area["name"])

        assert not any(suffix in n for n in found_area_names)

    def test_areas_containing_grouped_by_type(
        self, client: TestClient, area_test_data, db
    ):
        """Test that areas are properly grouped by type."""
        # Point in London - should be in both area types
        response = client.get("/v1/areas/containing?lat=51.5&lon=-0.1")

        assert response.status_code == 200
        data = response.json()

        suffix = area_test_data["suffix"]

        # Find our test groups
        our_groups = [g for g in data["groups"] if suffix in g["area_type"]["code"]]

        # Should have 2 groups (county and region)
        assert len(our_groups) == 2

        # Each group should have the area_type info
        for group in our_groups:
            assert "area_type" in group
            assert "id" in group["area_type"]
            assert "code" in group["area_type"]
            assert "name" in group["area_type"]
            assert "areas" in group

    def test_areas_containing_invalid_lat(self, client: TestClient, db):
        """Test validation for invalid latitude."""
        response = client.get("/v1/areas/containing?lat=91&lon=0")

        assert response.status_code == 422

    def test_areas_containing_invalid_lon(self, client: TestClient, db):
        """Test validation for invalid longitude."""
        response = client.get("/v1/areas/containing?lat=0&lon=181")

        assert response.status_code == 422

    def test_areas_containing_missing_params(self, client: TestClient, db):
        """Test validation when required params are missing."""
        response = client.get("/v1/areas/containing")

        assert response.status_code == 422


class TestAreaResponseStructure:
    """Tests for response structure validation."""

    def test_area_response_structure(self, client: TestClient, area_test_data, db):
        """Test AreaResponse has all expected fields."""
        area = area_test_data["area1"]
        response = client.get(f"/v1/areas/{area.id}")

        assert response.status_code == 200
        data = response.json()

        # Required fields
        assert "id" in data
        assert "name" in data
        assert "area_type" in data

        # Optional fields
        assert "code" in data

        # Nested area_type
        area_type = data["area_type"]
        assert "id" in area_type
        assert "code" in area_type
        assert "name" in area_type

    def test_area_boundary_response_structure(
        self, client: TestClient, area_test_data, db
    ):
        """Test AreaBoundaryResponse has all expected fields."""
        area = area_test_data["area1"]
        response = client.get(f"/v1/areas/{area.id}/boundary")

        assert response.status_code == 200
        data = response.json()

        # Required fields
        assert "id" in data
        assert "name" in data
        assert "area_type" in data
        assert "boundary" in data

        # Boundary should be GeoJSON
        boundary = data["boundary"]
        assert "type" in boundary
        assert "coordinates" in boundary
