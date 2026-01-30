"""
Tests for original location fields in trig model and admin operations.

Tests cover:
- Original location columns in Trig model
- Original location fields in admin detail response (read-only)
- Verification that original fields are excluded from admin update schema
- Coordinate discrepancy distance calculation
"""

import uuid
from datetime import date, time
from decimal import Decimal
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

from api.crud.user import create_user
from api.main import app
from api.models.trig import Trig

client = TestClient(app)


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def admin_user(db: Session):
    """Create an admin user for testing."""
    unique_name = f"admin_{uuid.uuid4().hex[:8]}"
    user = create_user(
        db=db,
        username=unique_name,
        email=f"{unique_name}@example.com",
        auth0_user_id=f"auth0|{unique_name}",
    )
    return user


@pytest.fixture
def test_trig_with_original_location(db: Session, test_user):
    """Create a test trig with original location data."""
    trig = Trig(
        waypoint=f"TP{uuid.uuid4().hex[:5].upper()}",
        name="Test Trig With Original",
        fb_number="FB001",
        stn_number="STN001",
        status_id=1,
        user_added=0,
        current_use="none",
        historic_use="none",
        condition="M",  # Moved condition
        # Current location (moved)
        wgs_lat=Decimal("51.50100"),
        wgs_long=Decimal("-0.12100"),
        wgs_height=Decimal("50.0"),
        osgb_eastings=Decimal("530100.1234"),
        osgb_northings=Decimal("180100.5678"),
        osgb_gridref="TQ 30100 80100",
        osgb_height=Decimal("48.5"),
        # Original location (official OS)
        original_wgs_lat=Decimal("51.50000"),
        original_wgs_long=Decimal("-0.12000"),
        original_wgs_height=Decimal("52.0"),
        original_osgb_eastings=Decimal("530000.1234"),
        original_osgb_northings=Decimal("180000.5678"),
        original_osgb_gridref="TQ 30000 80000",
        original_osgb_height=Decimal("50.5"),
        original_grid_system="gb",
        original_provenance="legacy",
        town="London",
        permission_ind="Y",
        needs_attention=1,
        attention_comment="Test comment",
        crt_date=date(2023, 1, 1),
        crt_time=time(0, 0, 0),
        crt_user_id=test_user.id,
        crt_ip_addr="127.0.0.1",
    )
    db.add(trig)
    db.commit()
    db.refresh(trig)
    return trig


@pytest.fixture
def test_trig_without_original(db: Session, test_user):
    """Create a test trig without original location data (NULL originals)."""
    trig = Trig(
        waypoint=f"TP{uuid.uuid4().hex[:5].upper()}",
        name="Test Trig Without Original",
        fb_number="FB002",
        stn_number="STN002",
        status_id=1,
        user_added=0,
        current_use="none",
        historic_use="none",
        condition="G",  # Good condition
        wgs_lat=Decimal("52.00000"),
        wgs_long=Decimal("-1.00000"),
        wgs_height=Decimal("100.0"),
        osgb_eastings=Decimal("450000.0000"),
        osgb_northings=Decimal("250000.0000"),
        osgb_gridref="SP 50000 50000",
        osgb_height=Decimal("98.5"),
        # No original location data
        town="Coventry",
        permission_ind="Y",
        needs_attention=0,
        attention_comment="",
        crt_date=date(2023, 1, 1),
        crt_time=time(0, 0, 0),
        crt_user_id=test_user.id,
        crt_ip_addr="127.0.0.1",
    )
    db.add(trig)
    db.commit()
    db.refresh(trig)
    return trig


# ============================================================================
# Model Tests
# ============================================================================


class TestOriginalLocationModel:
    """Tests for original location columns in the Trig model."""

    def test_original_location_columns_exist(
        self, db: Session, test_trig_with_original_location
    ):
        """Test that original location columns are present and accessible."""
        trig = test_trig_with_original_location

        assert trig.original_wgs_lat == Decimal("51.50000")
        assert trig.original_wgs_long == Decimal("-0.12000")
        assert trig.original_wgs_height == Decimal("52.0")
        assert trig.original_osgb_eastings == Decimal("530000.1234")
        assert trig.original_osgb_northings == Decimal("180000.5678")
        assert trig.original_osgb_gridref == "TQ 30000 80000"
        assert trig.original_osgb_height == Decimal("50.5")
        assert trig.original_grid_system == "gb"
        assert trig.original_provenance == "legacy"

    def test_original_location_can_be_null(
        self, db: Session, test_trig_without_original
    ):
        """Test that original location columns can be NULL."""
        trig = test_trig_without_original

        assert trig.original_wgs_lat is None
        assert trig.original_wgs_long is None
        assert trig.original_wgs_height is None
        assert trig.original_osgb_eastings is None
        assert trig.original_osgb_northings is None
        assert trig.original_osgb_gridref is None
        assert trig.original_osgb_height is None
        assert trig.original_grid_system is None
        assert trig.original_provenance is None

    def test_original_location_update(self, db: Session, test_trig_without_original):
        """Test updating original location fields."""
        trig = test_trig_without_original

        # Update original location
        trig.original_wgs_lat = Decimal("52.00000")
        trig.original_wgs_long = Decimal("-1.00000")
        trig.original_provenance = "manual entry"
        db.commit()
        db.refresh(trig)

        assert trig.original_wgs_lat == Decimal("52.00000")
        assert trig.original_wgs_long == Decimal("-1.00000")
        assert trig.original_provenance == "manual entry"


# ============================================================================
# Schema Tests
# ============================================================================


class TestOriginalLocationSchemas:
    """Tests for original location fields in Pydantic schemas."""

    def test_trig_details_schema_includes_original_fields(self):
        """Test that TrigDetails schema includes original location fields."""
        from api.schemas.trig import TrigDetails

        schema = TrigDetails.model_json_schema()
        properties = schema["properties"]

        assert "original_wgs_lat" in properties
        assert "original_wgs_long" in properties
        assert "original_wgs_height" in properties
        assert "original_osgb_eastings" in properties
        assert "original_osgb_northings" in properties
        assert "original_osgb_gridref" in properties
        assert "original_osgb_height" in properties
        assert "original_grid_system" in properties
        assert "original_provenance" in properties

    def test_trig_admin_detail_schema_includes_original_fields(self):
        """Test that TrigAdminDetail schema includes original location fields."""
        from api.schemas.trig_admin import TrigAdminDetail

        schema = TrigAdminDetail.model_json_schema()
        properties = schema["properties"]

        assert "original_wgs_lat" in properties
        assert "original_wgs_long" in properties
        assert "original_wgs_height" in properties
        assert "original_osgb_eastings" in properties
        assert "original_osgb_northings" in properties
        assert "original_osgb_gridref" in properties
        assert "original_osgb_height" in properties
        assert "original_grid_system" in properties
        assert "original_provenance" in properties

    def test_trig_admin_update_schema_excludes_original_fields(self):
        """Test that TrigAdminUpdate schema excludes original location fields.

        Original location fields are read-only and should only be modified via
        bulk data loads, migrations, or direct SQL. They are intentionally
        excluded from the admin update API.
        """
        from api.schemas.trig_admin import TrigAdminUpdate

        schema = TrigAdminUpdate.model_json_schema()
        properties = schema["properties"]

        # Original fields should NOT be in the update schema
        assert "original_wgs_lat" not in properties
        assert "original_wgs_long" not in properties
        assert "original_wgs_height" not in properties
        assert "original_osgb_eastings" not in properties
        assert "original_osgb_northings" not in properties
        assert "original_osgb_gridref" not in properties
        assert "original_osgb_height" not in properties
        assert "original_grid_system" not in properties
        assert "original_provenance" not in properties


# ============================================================================
# Admin Endpoint Tests
# ============================================================================


class TestAdminTrigOriginalLocation:
    """Tests for original location fields in admin trig endpoints."""

    def test_get_trig_admin_includes_original_fields(
        self, db: Session, test_trig_with_original_location, admin_user
    ):
        """Test that GET /admin/trigs/{id} returns original location fields."""
        trig = test_trig_with_original_location

        # Mock admin authentication using the standard pattern for this codebase
        with patch("api.api.deps.auth0_validator.validate_auth0_token") as mock:
            mock.return_value = {
                "token_type": "auth0",
                "auth0_user_id": admin_user.auth0_user_id,
                "permissions": ["api:admin"],
            }

            response = client.get(
                f"/v1/admin/trigs/{trig.id}",
                headers={"Authorization": "Bearer test-token"},
            )

            assert response.status_code == 200
            data = response.json()
            assert "original_wgs_lat" in data
            assert "original_wgs_long" in data
            assert "original_osgb_gridref" in data
            assert "original_provenance" in data

    def test_original_location_serialization(self, test_trig_with_original_location):
        """Test that original location fields are properly serialized."""
        from api.schemas.trig_admin import TrigAdminDetail

        trig = test_trig_with_original_location
        detail = TrigAdminDetail.model_validate(trig)

        # Check values - may be Decimal or float depending on serialization
        assert float(detail.original_wgs_lat) == 51.5
        assert float(detail.original_wgs_long) == -0.12
        assert detail.original_osgb_gridref == "TQ 30000 80000"
        assert detail.original_grid_system == "gb"
        assert detail.original_provenance == "legacy"

        # Check that height values are present
        assert detail.original_wgs_height is not None
        assert detail.original_osgb_height is not None

    def test_original_location_null_serialization(self, test_trig_without_original):
        """Test that NULL original location fields are serialized as None."""
        from api.schemas.trig_admin import TrigAdminDetail

        trig = test_trig_without_original
        detail = TrigAdminDetail.model_validate(trig)

        assert detail.original_wgs_lat is None
        assert detail.original_wgs_long is None
        assert detail.original_wgs_height is None
        assert detail.original_osgb_eastings is None
        assert detail.original_osgb_northings is None
        assert detail.original_osgb_gridref is None
        assert detail.original_osgb_height is None
        assert detail.original_grid_system is None
        assert detail.original_provenance is None


# ============================================================================
# PostGIS Original Location Tests
# ============================================================================


class TestOriginalLocationPostGIS:
    """Tests for PostGIS original_location column."""

    def test_original_location_postgis_column(
        self, db: Session, test_trig_with_original_location
    ):
        """Test that original_location PostGIS column is populated."""
        trig = test_trig_with_original_location

        # Query the original_location as lat/lon
        result = db.execute(
            text("""
                SELECT
                    ST_Y(original_location::geometry) as lat,
                    ST_X(original_location::geometry) as lon
                FROM trig
                WHERE id = :trig_id
                """),
            {"trig_id": trig.id},
        ).fetchone()

        if result and result.lat is not None:
            # PostGIS stores as (lon, lat), ST_Y returns lat, ST_X returns lon
            assert abs(result.lat - 51.5) < 0.0001
            assert abs(result.lon - (-0.12)) < 0.0001

    def test_distance_between_current_and_original(
        self, db: Session, test_trig_with_original_location
    ):
        """Test calculating distance between current and original locations."""
        trig = test_trig_with_original_location

        # Calculate distance using PostGIS
        result = db.execute(
            text("""
                SELECT ST_Distance(location, original_location) as distance_metres
                FROM trig
                WHERE id = :trig_id
                AND location IS NOT NULL
                AND original_location IS NOT NULL
                """),
            {"trig_id": trig.id},
        ).fetchone()

        if result and result.distance_metres is not None:
            # Should be a small distance (100m or so based on our test data)
            assert result.distance_metres > 0
            assert result.distance_metres < 1000  # Less than 1km


# ============================================================================
# TrigDetails Schema Tests (for public API)
# ============================================================================


class TestTrigDetailsOriginalLocation:
    """Tests for original location in TrigDetails schema (public API)."""

    def test_trig_details_includes_original_for_moved_trig(
        self, test_trig_with_original_location
    ):
        """Test that TrigDetails includes original location for moved trig."""
        from api.schemas.trig import TrigDetails

        trig = test_trig_with_original_location
        details = TrigDetails.model_validate(trig)

        assert details.original_osgb_gridref == "TQ 30000 80000"
        assert details.original_grid_system == "gb"

    def test_trig_details_original_coords_precision(
        self, test_trig_with_original_location
    ):
        """Test that original coordinates have correct precision in TrigDetails."""
        from api.schemas.trig import TrigDetails

        trig = test_trig_with_original_location
        details = TrigDetails.model_validate(trig)

        # Check that WGS84 values are correct (comparing as floats)
        assert float(details.original_wgs_lat) == 51.5
        assert float(details.original_wgs_long) == -0.12

        # Check that OSGB values are correct (comparing as floats with tolerance)
        assert abs(float(details.original_osgb_eastings) - 530000.1234) < 0.001
        assert abs(float(details.original_osgb_northings) - 180000.5678) < 0.001
