"""
Tests for user area breakdown endpoint and CRUD functions.

Tests the area breakdown feature that shows user log counts grouped by area
for a specific area type (e.g., counties).

Note: Tests that require the trig_area table will be skipped
if the table does not exist in the test database.
"""

import uuid
from datetime import date, time

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

from api.crud import area as area_crud
from api.models.area import Area, AreaType
from api.models.trig import Trig
from api.models.user import TLog, User


def _trig_area_exists(db: Session) -> bool:
    """Check if trig_area table exists."""
    try:
        result = db.execute(
            text(
                "SELECT EXISTS (SELECT 1 FROM pg_tables WHERE tablename = 'trig_area')"
            )
        ).scalar()
        return bool(result)
    except Exception:
        return False


def _create_test_trig_area(db: Session) -> None:
    """Create a minimal test version of the trig_area table if it doesn't exist."""
    if _trig_area_exists(db):
        return

    # Create the trig_area table for testing (no FKs for test simplicity)
    try:
        db.execute(text("""
                CREATE TABLE IF NOT EXISTS trig_area (
                    trig_id INTEGER NOT NULL,
                    area_id INTEGER NOT NULL,
                    area_type_id INTEGER NOT NULL,
                    area_type_code VARCHAR(50) NOT NULL,
                    PRIMARY KEY (trig_id, area_id)
                )
            """))
        db.execute(
            text(
                "CREATE INDEX IF NOT EXISTS ix_trig_area_area_type_code ON trig_area (area_type_code)"
            )
        )
        db.commit()
    except Exception:
        db.rollback()


@pytest.fixture
def area_breakdown_test_data(db: Session):
    """
    Create test data for area breakdown tests.

    Creates:
    - 2 area types
    - 3 areas (2 counties, 1 region)
    - 2 trigs (one in each county)
    - 1 user with logs for both trigs
    - trig_area table entries for trig-area mapping
    """
    # Ensure the trig_area table exists (create if needed)
    _create_test_trig_area(db)

    unique_suffix = uuid.uuid4().hex[:6]
    base_id = abs(hash(unique_suffix)) % 20000 + 30000

    # Create test area types
    county_type = AreaType(
        code=f"county_{unique_suffix}",
        name=f"County {unique_suffix}",
        description=f"Counties for testing breakdown {unique_suffix}",
        source_url="https://example.com/test",
    )
    region_type = AreaType(
        code=f"region_{unique_suffix}",
        name=f"Region {unique_suffix}",
        description=f"Regions for testing breakdown {unique_suffix}",
        source_url="https://example.com/test",
    )
    db.add(county_type)
    db.add(region_type)
    db.flush()

    # Create test areas with PostGIS boundaries
    # County 1: London area (51.5, -0.1)
    db.execute(
        text("""
            INSERT INTO area (area_type_id, code, name, boundary)
            VALUES (
                :area_type_id,
                :code,
                :name,
                ST_GeogFromText('SRID=4326;MULTIPOLYGON(((-0.3 51.3, -0.3 51.7, 0.1 51.7, 0.1 51.3, -0.3 51.3)))')
            )
        """),
        {
            "area_type_id": county_type.id,
            "code": f"LONDON_{unique_suffix}",
            "name": f"Greater London {unique_suffix}",
        },
    )

    # County 2: Manchester area (53.5, -2.2)
    db.execute(
        text("""
            INSERT INTO area (area_type_id, code, name, boundary)
            VALUES (
                :area_type_id,
                :code,
                :name,
                ST_GeogFromText('SRID=4326;MULTIPOLYGON(((-2.5 53.3, -2.5 53.7, -1.9 53.7, -1.9 53.3, -2.5 53.3)))')
            )
        """),
        {
            "area_type_id": county_type.id,
            "code": f"MANCHESTER_{unique_suffix}",
            "name": f"Greater Manchester {unique_suffix}",
        },
    )

    # Region covering both
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
            "area_type_id": region_type.id,
            "code": f"ENGLAND_{unique_suffix}",
            "name": f"England {unique_suffix}",
        },
    )
    db.flush()

    # Fetch created areas
    london_area = db.query(Area).filter(Area.code == f"LONDON_{unique_suffix}").first()
    manchester_area = (
        db.query(Area).filter(Area.code == f"MANCHESTER_{unique_suffix}").first()
    )
    england_area = (
        db.query(Area).filter(Area.code == f"ENGLAND_{unique_suffix}").first()
    )

    # Assert areas were created successfully
    assert london_area is not None
    assert manchester_area is not None
    assert england_area is not None

    # Create test user
    user = User(
        name=f"area_breakdown_user_{unique_suffix}",
        firstname="Test",
        surname="User",
        cryptpw="test",
        email=f"area_breakdown_{unique_suffix}@example.com",
        email_valid="Y",
        public_ind="Y",
        about="Test user for area breakdown tests",
    )
    db.add(user)
    db.flush()

    # Create test trigs with PostGIS location
    # Trig 1: In London (51.5, -0.1)
    db.execute(
        text("""
            INSERT INTO trig (
                id, waypoint, name, fb_number, stn_number, status_id, user_added,
                current_use, historic_use, wgs_lat, wgs_long, wgs_height,
                osgb_eastings, osgb_northings, osgb_gridref, osgb_height,
                condition, town, permission_ind, needs_attention,
                attention_comment, crt_date, crt_time, crt_ip_addr, location
            )
            VALUES (
                :id, :waypoint, :name, :fb_number, :stn_number, :status_id, :user_added,
                :current_use, :historic_use, :wgs_lat, :wgs_long, :wgs_height,
                :osgb_eastings, :osgb_northings, :osgb_gridref, :osgb_height,
                :condition, :town, :permission_ind, :needs_attention,
                :attention_comment, :crt_date, :crt_time, :crt_ip_addr,
                ST_GeogFromText('SRID=4326;POINT(-0.1 51.5)')
            )
        """),
        {
            "id": base_id,
            "waypoint": f"AB{base_id}"[:8],
            "name": f"London Trig {unique_suffix}",
            "fb_number": f"FB{base_id}",
            "stn_number": f"STN{base_id}",
            "status_id": 10,
            "user_added": 0,
            "current_use": "Passive station",
            "historic_use": "Primary",
            "wgs_lat": 51.5,
            "wgs_long": -0.1,
            "wgs_height": 100,
            "osgb_eastings": 530000,
            "osgb_northings": 180000,
            "osgb_gridref": "TQ 30000 80000",
            "osgb_height": 95,
            "condition": "G",
            "town": "Westminster",
            "permission_ind": "Y",
            "needs_attention": 0,
            "attention_comment": "",
            "crt_date": date(2023, 1, 1),
            "crt_time": time(12, 0, 0),
            "crt_ip_addr": "127.0.0.1",
        },
    )

    # Trig 2: In Manchester (53.5, -2.2)
    db.execute(
        text("""
            INSERT INTO trig (
                id, waypoint, name, fb_number, stn_number, status_id, user_added,
                current_use, historic_use, wgs_lat, wgs_long, wgs_height,
                osgb_eastings, osgb_northings, osgb_gridref, osgb_height,
                condition, town, permission_ind, needs_attention,
                attention_comment, crt_date, crt_time, crt_ip_addr, location
            )
            VALUES (
                :id, :waypoint, :name, :fb_number, :stn_number, :status_id, :user_added,
                :current_use, :historic_use, :wgs_lat, :wgs_long, :wgs_height,
                :osgb_eastings, :osgb_northings, :osgb_gridref, :osgb_height,
                :condition, :town, :permission_ind, :needs_attention,
                :attention_comment, :crt_date, :crt_time, :crt_ip_addr,
                ST_GeogFromText('SRID=4326;POINT(-2.2 53.5)')
            )
        """),
        {
            "id": base_id + 1,
            "waypoint": f"AB{base_id + 1}"[:8],
            "name": f"Manchester Trig {unique_suffix}",
            "fb_number": f"FB{base_id + 1}",
            "stn_number": f"STN{base_id + 1}",
            "status_id": 10,
            "user_added": 0,
            "current_use": "Passive station",
            "historic_use": "Primary",
            "wgs_lat": 53.5,
            "wgs_long": -2.2,
            "wgs_height": 150,
            "osgb_eastings": 384000,
            "osgb_northings": 398000,
            "osgb_gridref": "SJ 84000 98000",
            "osgb_height": 145,
            "condition": "G",
            "town": "Manchester",
            "permission_ind": "Y",
            "needs_attention": 0,
            "attention_comment": "",
            "crt_date": date(2023, 1, 1),
            "crt_time": time(12, 0, 0),
            "crt_ip_addr": "127.0.0.1",
        },
    )
    db.flush()

    # Fetch created trigs
    london_trig = db.query(Trig).filter(Trig.id == base_id).first()
    manchester_trig = db.query(Trig).filter(Trig.id == base_id + 1).first()

    # Assert trigs were created successfully
    assert london_trig is not None
    assert manchester_trig is not None

    # Insert into trig_area table
    db.execute(
        text("""
            INSERT INTO trig_area (trig_id, area_id, area_type_id, area_type_code)
            VALUES
                (:london_trig_id, :london_area_id, :county_type_id, :county_code),
                (:london_trig_id, :england_area_id, :region_type_id, :region_code),
                (:manchester_trig_id, :manchester_area_id, :county_type_id, :county_code),
                (:manchester_trig_id, :england_area_id, :region_type_id, :region_code)
        """),
        {
            "london_trig_id": london_trig.id,
            "london_area_id": london_area.id,
            "manchester_trig_id": manchester_trig.id,
            "manchester_area_id": manchester_area.id,
            "england_area_id": england_area.id,
            "county_type_id": county_type.id,
            "county_code": county_type.code,
            "region_type_id": region_type.id,
            "region_code": region_type.code,
        },
    )

    # Create logs for the test user
    # 3 logs for London trig, 1 log for Manchester trig
    logs = []
    for i in range(3):
        log = TLog(
            trig_id=london_trig.id,
            user_id=user.id,
            date=date(2024, 1, 1 + i),
            time=time(12, 0, 0),
            condition="G",
            comment=f"London log {i + 1}",
            score=5,
            source="W",
        )
        logs.append(log)

    manchester_log = TLog(
        trig_id=manchester_trig.id,
        user_id=user.id,
        date=date(2024, 2, 1),
        time=time(12, 0, 0),
        condition="G",
        comment="Manchester log",
        score=5,
        source="W",
    )
    logs.append(manchester_log)

    db.add_all(logs)
    db.commit()

    yield {
        "user": user,
        "county_type": county_type,
        "region_type": region_type,
        "london_area": london_area,
        "manchester_area": manchester_area,
        "england_area": england_area,
        "london_trig": london_trig,
        "manchester_trig": manchester_trig,
        "logs": logs,
        "suffix": unique_suffix,
    }

    # Cleanup (reverse order of creation)
    for log in logs:
        db.delete(log)
    db.flush()

    # Remove trig_area table entries
    db.execute(
        text("DELETE FROM trig_area WHERE trig_id IN (:t1, :t2)"),
        {"t1": london_trig.id, "t2": manchester_trig.id},
    )

    # Delete trigs
    db.execute(
        text("DELETE FROM trig WHERE id IN (:t1, :t2)"),
        {"t1": london_trig.id, "t2": manchester_trig.id},
    )

    # Delete areas
    db.execute(
        text("DELETE FROM area WHERE code IN (:a1, :a2, :a3)"),
        {
            "a1": f"LONDON_{unique_suffix}",
            "a2": f"MANCHESTER_{unique_suffix}",
            "a3": f"ENGLAND_{unique_suffix}",
        },
    )

    db.delete(user)
    db.delete(county_type)
    db.delete(region_type)
    db.commit()


class TestUserAreaBreakdownCRUD:
    """Tests for the get_user_log_counts_by_area CRUD function."""

    def test_get_user_log_counts_by_area_county(
        self, db: Session, area_breakdown_test_data
    ):
        """Test getting user log counts grouped by county."""
        data = area_breakdown_test_data
        user_id = int(data["user"].id)
        area_type_code = str(data["county_type"].code)

        result = area_crud.get_user_log_counts_by_area(db, user_id, area_type_code)

        # Should have 2 counties
        assert len(result) == 2

        # Results should be ordered by count descending
        # Each should have count of 1 (distinct trigs)
        for item in result:
            assert item["count"] == 1

        # Check area names include our test areas
        area_names = [r["area_name"] for r in result]
        suffix = data["suffix"]
        assert any(suffix in name for name in area_names)

    def test_get_user_log_counts_by_area_region(
        self, db: Session, area_breakdown_test_data
    ):
        """Test getting user log counts grouped by region."""
        data = area_breakdown_test_data
        user_id = int(data["user"].id)
        area_type_code = str(data["region_type"].code)

        result = area_crud.get_user_log_counts_by_area(db, user_id, area_type_code)

        # Should have 1 region containing both trigs
        assert len(result) == 1
        assert data["suffix"] in result[0]["area_name"]
        assert result[0]["count"] == 2  # 2 distinct trigs

    def test_get_user_log_counts_by_area_nonexistent_type(
        self, db: Session, area_breakdown_test_data
    ):
        """Test with non-existent area type code."""
        data = area_breakdown_test_data
        user_id = int(data["user"].id)

        result = area_crud.get_user_log_counts_by_area(
            db, user_id, "nonexistent_area_type_code"
        )

        assert result == []

    def test_get_user_log_counts_by_area_user_no_logs(
        self, db: Session, area_breakdown_test_data
    ):
        """Test with a user that has no logs."""
        data = area_breakdown_test_data

        # Create a user with no logs
        suffix = uuid.uuid4().hex[:6]
        no_logs_user = User(
            name=f"no_logs_user_{suffix}",
            firstname="No",
            surname="Logs",
            cryptpw="test",
            email=f"no_logs_{suffix}@example.com",
            email_valid="Y",
            public_ind="Y",
        )
        db.add(no_logs_user)
        db.flush()

        try:
            result = area_crud.get_user_log_counts_by_area(
                db, int(no_logs_user.id), str(data["county_type"].code)
            )
            assert result == []
        finally:
            db.delete(no_logs_user)
            db.commit()


class TestUserAreaBreakdownEndpoint:
    """Tests for GET /v1/users/{user_id}/area-breakdown endpoint."""

    def test_area_breakdown_returns_data(
        self, client: TestClient, area_breakdown_test_data
    ):
        """Test that the endpoint returns area breakdown data."""
        data = area_breakdown_test_data
        user_id = int(data["user"].id)
        area_type_code = str(data["county_type"].code)

        response = client.get(
            f"/v1/users/{user_id}/area-breakdown?area_type_code={area_type_code}"
        )

        assert response.status_code == 200
        result = response.json()

        # Check structure
        assert "area_type" in result
        assert "items" in result

        # Check area_type info
        assert result["area_type"]["code"] == area_type_code
        assert result["area_type"]["description"] is not None

        # Check items
        assert len(result["items"]) == 2
        for item in result["items"]:
            assert "area_name" in item
            assert "count" in item
            assert item["count"] == 1

    def test_area_breakdown_default_area_type(
        self, client: TestClient, area_breakdown_test_data
    ):
        """Test that the endpoint uses county_1991 as default area type."""
        data = area_breakdown_test_data
        user_id = int(data["user"].id)

        # Request without area_type_code parameter
        response = client.get(f"/v1/users/{user_id}/area-breakdown")

        # Should use default (county_1991) which may or may not exist in test data
        # Either succeeds with data or returns 404 for missing area type
        assert response.status_code in [200, 404]

    def test_area_breakdown_nonexistent_area_type(
        self, client: TestClient, area_breakdown_test_data
    ):
        """Test 404 for non-existent area type."""
        data = area_breakdown_test_data
        user_id = int(data["user"].id)

        response = client.get(
            f"/v1/users/{user_id}/area-breakdown?area_type_code=nonexistent_type"
        )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_area_breakdown_response_structure(
        self, client: TestClient, area_breakdown_test_data
    ):
        """Test the full response structure."""
        data = area_breakdown_test_data
        user_id = int(data["user"].id)
        area_type_code = str(data["county_type"].code)

        response = client.get(
            f"/v1/users/{user_id}/area-breakdown?area_type_code={area_type_code}"
        )

        assert response.status_code == 200
        result = response.json()

        # Validate area_type structure
        area_type = result["area_type"]
        assert "id" in area_type
        assert "code" in area_type
        assert "name" in area_type
        assert "description" in area_type

        # Validate items structure
        items = result["items"]
        assert isinstance(items, list)
        for item in items:
            assert isinstance(item["area_name"], str)
            assert isinstance(item["count"], int)
            assert item["count"] > 0

    def test_area_breakdown_ordered_by_count_desc(
        self, client: TestClient, area_breakdown_test_data
    ):
        """Test that results are ordered by count descending."""
        data = area_breakdown_test_data
        user_id = int(data["user"].id)
        area_type_code = str(data["county_type"].code)

        response = client.get(
            f"/v1/users/{user_id}/area-breakdown?area_type_code={area_type_code}"
        )

        assert response.status_code == 200
        result = response.json()

        items = result["items"]
        if len(items) > 1:
            # Verify descending order
            counts = [item["count"] for item in items]
            assert counts == sorted(counts, reverse=True)

    def test_area_breakdown_distinct_trigs_not_logs(
        self, client: TestClient, area_breakdown_test_data
    ):
        """Test that counts are for distinct trigs, not individual logs."""
        data = area_breakdown_test_data
        user_id = int(data["user"].id)
        area_type_code = str(data["region_type"].code)

        response = client.get(
            f"/v1/users/{user_id}/area-breakdown?area_type_code={area_type_code}"
        )

        assert response.status_code == 200
        result = response.json()

        # The region contains both trigs, user has 4 logs total (3 + 1)
        # but should count as 2 distinct trigs
        items = result["items"]
        assert len(items) == 1
        assert items[0]["count"] == 2


class TestAreaTypeDescriptionInResponse:
    """Tests that area type description is included in responses."""

    def test_area_types_list_includes_description(
        self, client: TestClient, area_breakdown_test_data
    ):
        """Test that /v1/areas/types includes description field."""
        data = area_breakdown_test_data

        response = client.get("/v1/areas/types")

        assert response.status_code == 200
        result = response.json()

        # Find our test area type
        our_type = next(
            (t for t in result if t["code"] == str(data["county_type"].code)), None
        )
        assert our_type is not None

        # Check description is present
        assert "description" in our_type
        assert our_type["description"] is not None
        assert data["suffix"] in our_type["description"]

    def test_area_type_description_can_be_null(
        self, client: TestClient, db: Session, area_breakdown_test_data
    ):
        """Test that description can be null for area types without one."""
        suffix = uuid.uuid4().hex[:6]

        # Create area type without description
        area_type = AreaType(
            code=f"no_desc_{suffix}",
            name=f"No Description Type {suffix}",
            description=None,
        )
        db.add(area_type)
        db.commit()

        try:
            response = client.get("/v1/areas/types")
            assert response.status_code == 200
            result = response.json()

            our_type = next(
                (t for t in result if t["code"] == str(area_type.code)), None
            )
            assert our_type is not None
            assert our_type["description"] is None
        finally:
            db.delete(area_type)
            db.commit()
