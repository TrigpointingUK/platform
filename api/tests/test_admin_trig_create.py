"""
Tests for admin trigpoint creation functionality.

Tests cover:
- CRUD functions: get_next_waypoint, create_trig_admin
- API endpoint: POST /v1/admin/trigs
"""

import uuid
from datetime import date, time
from decimal import Decimal
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from api.crud import trig as trig_crud
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
def non_admin_user(db: Session):
    """Create a non-admin user for testing."""
    unique_name = f"user_{uuid.uuid4().hex[:8]}"
    user = create_user(
        db=db,
        username=unique_name,
        email=f"{unique_name}@example.com",
        auth0_user_id=f"auth0|{unique_name}",
    )
    return user


@pytest.fixture
def existing_trigs(db: Session, test_user):
    """Create existing trigs with known waypoints for testing waypoint generation."""
    trigs = []
    for waypoint in ["TP99990", "TP99991", "TP99992"]:
        trig = Trig(
            waypoint=waypoint,
            name=f"Test Trig {waypoint}",
            fb_number="FB001",
            stn_number="STN001",
            status_id=1,
            user_added=0,
            current_use="none",
            historic_use="none",
            condition="G",
            wgs_lat=Decimal("51.50000"),
            wgs_long=Decimal("-0.12000"),
            wgs_height=0,
            osgb_eastings=530000,
            osgb_northings=180000,
            osgb_gridref="TQ 30000 80000",
            osgb_height=0,
            county="",
            town="",
            permission_ind="Y",
            needs_attention=0,
            attention_comment="",
            crt_date=date(2023, 1, 1),
            crt_time=time(0, 0, 0),
            crt_user_id=test_user.id,
            crt_ip_addr="127.0.0.1",
        )
        db.add(trig)
        trigs.append(trig)
    db.commit()
    for trig in trigs:
        db.refresh(trig)
    return trigs


@pytest.fixture
def valid_trig_data():
    """Valid data for creating a trigpoint."""
    return {
        "name": "New Test Trigpoint",
        "fb_number": "FB12345",
        "stn_number": "STN12345",
        "stn_number_active": "",
        "stn_number_passive": "",
        "stn_number_osgb36": "",
        "status_id": 1,
        "type_id": None,
        "current_use": "none",
        "historic_use": "none",
        "condition": "U",
        "wgs_lat": "51.50000",
        "wgs_long": "-0.12000",
        "wgs_height": 100,
        "osgb_eastings": 530000,
        "osgb_northings": 180000,
        "osgb_gridref": "TQ 30000 80000",
        "osgb_height": 100,
        "legal_message": None,
        "admin_comment": "Created for testing purposes",
    }


# ============================================================================
# CRUD Tests: get_next_waypoint
# ============================================================================


class TestGetNextWaypoint:
    """Tests for the get_next_waypoint CRUD function."""

    def test_returns_waypoint_starting_with_tp(self, db: Session):
        """Test that waypoint starts with 'TP'."""
        waypoint = trig_crud.get_next_waypoint(db)
        assert waypoint.startswith("TP")

    def test_returns_valid_format(self, db: Session):
        """Test that waypoint is in valid format (TP followed by digits)."""
        waypoint = trig_crud.get_next_waypoint(db)
        assert waypoint.startswith("TP")
        assert waypoint[2:].isdigit()

    def test_increments_from_existing_waypoints(self, db: Session, existing_trigs):
        """Test that next waypoint is incremented from max existing waypoint."""
        waypoint = trig_crud.get_next_waypoint(db)
        # existing_trigs has TP99990, TP99991, TP99992
        # So next should be TP99993
        assert waypoint == "TP99993"

    def test_returns_default_when_no_tp_waypoints(self, db: Session):
        """Test that returns default starting point when no TP waypoints exist."""
        # Delete all TP waypoints for this test
        db.query(Trig).filter(Trig.waypoint.like("TP%")).delete(
            synchronize_session=False
        )
        db.commit()

        waypoint = trig_crud.get_next_waypoint(db)
        # Should return default starting point
        assert waypoint == "TP100000"


# ============================================================================
# CRUD Tests: create_trig_admin
# ============================================================================


class TestCreateTrigAdmin:
    """Tests for the create_trig_admin CRUD function."""

    def test_creates_trig_with_correct_fields(self, db: Session, admin_user):
        """Test that create_trig_admin creates a trig with all correct fields."""
        waypoint = f"TP{uuid.uuid4().hex[:6]}"
        trig_data = {
            "name": "Test Creation Trig",
            "fb_number": "FB999",
            "stn_number": "STN999",
            "stn_number_active": "ACT999",
            "stn_number_passive": "PAS999",
            "stn_number_osgb36": "OSGB999",
            "status_id": 1,
            "type_id": None,
            "current_use": "Passive station",
            "historic_use": "Primary",
            "condition": "G",
            "wgs_lat": Decimal("52.00000"),
            "wgs_long": Decimal("-1.00000"),
            "wgs_height": 150,
            "osgb_eastings": 450000,
            "osgb_northings": 250000,
            "osgb_gridref": "SP 50000 50000",
            "osgb_height": 150,
            "postcode": None,
            "attention_comment": "Test comment",
            "legal_message": "<p>Test legal message</p>",
        }

        trig = trig_crud.create_trig_admin(
            db,
            waypoint=waypoint,
            admin_user_id=admin_user.id,
            admin_ip_addr="192.168.1.1",
            trig_data=trig_data,
        )

        assert trig.id is not None
        # Waypoint is always derived from ID (TP + ID padded to 4 digits)
        assert trig.waypoint == f"TP{trig.id:04d}"
        assert trig.name == "Test Creation Trig"
        assert trig.fb_number == "FB999"
        assert trig.stn_number == "STN999"
        assert trig.status_id == 1
        assert trig.condition == "G"
        assert trig.wgs_lat == Decimal("52.00000")
        assert trig.wgs_long == Decimal("-1.00000")
        assert trig.legal_message == "<p>Test legal message</p>"

    def test_sets_user_added_to_zero(self, db: Session, admin_user):
        """Test that user_added is set to 0 for admin-created trigs."""
        waypoint = f"TP{uuid.uuid4().hex[:6]}"
        trig_data = {
            "name": "User Added Test",
            "status_id": 1,
            "wgs_lat": Decimal("51.50000"),
            "wgs_long": Decimal("-0.12000"),
            "osgb_eastings": 530000,
            "osgb_northings": 180000,
        }

        trig = trig_crud.create_trig_admin(
            db,
            waypoint=waypoint,
            admin_user_id=admin_user.id,
            admin_ip_addr="127.0.0.1",
            trig_data=trig_data,
        )

        assert trig.user_added == 0

    def test_sets_audit_fields(self, db: Session, admin_user):
        """Test that creation and admin audit fields are set."""
        waypoint = f"TP{uuid.uuid4().hex[:6]}"
        trig_data = {
            "name": "Audit Fields Test",
            "status_id": 1,
            "wgs_lat": Decimal("51.50000"),
            "wgs_long": Decimal("-0.12000"),
            "osgb_eastings": 530000,
            "osgb_northings": 180000,
        }

        trig = trig_crud.create_trig_admin(
            db,
            waypoint=waypoint,
            admin_user_id=admin_user.id,
            admin_ip_addr="10.0.0.1",
            trig_data=trig_data,
        )

        # Creation audit fields
        assert trig.crt_date == date.today()
        assert trig.crt_time is not None
        assert trig.crt_user_id == admin_user.id
        assert trig.crt_ip_addr == "10.0.0.1"

        # Admin tracking fields
        assert trig.admin_user_id == admin_user.id
        assert trig.admin_timestamp is not None
        assert trig.admin_ip_addr == "10.0.0.1"

    def test_sets_county_and_town_to_empty(self, db: Session, admin_user):
        """Test that county and town are set to empty strings (deprecated fields)."""
        waypoint = f"TP{uuid.uuid4().hex[:6]}"
        trig_data = {
            "name": "Deprecated Fields Test",
            "status_id": 1,
            "wgs_lat": Decimal("51.50000"),
            "wgs_long": Decimal("-0.12000"),
            "osgb_eastings": 530000,
            "osgb_northings": 180000,
        }

        trig = trig_crud.create_trig_admin(
            db,
            waypoint=waypoint,
            admin_user_id=admin_user.id,
            admin_ip_addr="127.0.0.1",
            trig_data=trig_data,
        )

        assert trig.county == ""
        assert trig.town == ""


# ============================================================================
# API Endpoint Tests: POST /v1/admin/trigs
# ============================================================================


class TestCreateTrigAdminEndpoint:
    """Tests for the POST /v1/admin/trigs endpoint."""

    def test_create_trig_success(self, db: Session, admin_user, valid_trig_data):
        """Test successful trigpoint creation with admin scope."""
        with patch("api.api.deps.auth0_validator.validate_auth0_token") as mock:
            mock.return_value = {
                "token_type": "auth0",
                "auth0_user_id": admin_user.auth0_user_id,
                "sub": admin_user.auth0_user_id,
                "scope": "api:write api:admin",
            }

            response = client.post(
                "/v1/admin/trigs",
                json=valid_trig_data,
                headers={"Authorization": "Bearer mock_token"},
            )

            assert response.status_code == 201
            data = response.json()
            assert data["name"] == valid_trig_data["name"]
            assert data["waypoint"].startswith("TP")
            assert data["condition"] == "U"
            assert data["id"] is not None

    def test_create_trig_returns_auto_generated_waypoint(
        self, db: Session, admin_user, valid_trig_data
    ):
        """Test that the created trig has an auto-generated waypoint."""
        with patch("api.api.deps.auth0_validator.validate_auth0_token") as mock:
            mock.return_value = {
                "token_type": "auth0",
                "auth0_user_id": admin_user.auth0_user_id,
                "sub": admin_user.auth0_user_id,
                "scope": "api:write api:admin",
            }

            response = client.post(
                "/v1/admin/trigs",
                json=valid_trig_data,
                headers={"Authorization": "Bearer mock_token"},
            )

            assert response.status_code == 201
            data = response.json()
            assert data["waypoint"].startswith("TP")
            assert len(data["waypoint"]) <= 8

    def test_create_trig_without_admin_scope_returns_403(
        self, db: Session, non_admin_user, valid_trig_data
    ):
        """Test that creating a trig without api:admin scope returns 403."""
        with patch("api.api.deps.auth0_validator.validate_auth0_token") as mock:
            mock.return_value = {
                "token_type": "auth0",
                "auth0_user_id": non_admin_user.auth0_user_id,
                "sub": non_admin_user.auth0_user_id,
                "scope": "api:write",  # Missing api:admin
            }

            response = client.post(
                "/v1/admin/trigs",
                json=valid_trig_data,
                headers={"Authorization": "Bearer mock_token"},
            )

            assert response.status_code == 403

    def test_create_trig_without_auth_returns_401(self, valid_trig_data):
        """Test that creating a trig without authentication returns 401."""
        response = client.post("/v1/admin/trigs", json=valid_trig_data)
        assert response.status_code == 401

    def test_create_trig_with_invalid_type_id_returns_400(
        self, db: Session, admin_user, valid_trig_data
    ):
        """Test that creating a trig with invalid type_id returns 400."""
        with patch("api.api.deps.auth0_validator.validate_auth0_token") as mock:
            mock.return_value = {
                "token_type": "auth0",
                "auth0_user_id": admin_user.auth0_user_id,
                "sub": admin_user.auth0_user_id,
                "scope": "api:write api:admin",
            }

            invalid_data = valid_trig_data.copy()
            invalid_data["type_id"] = 99999  # Non-existent type_id

            response = client.post(
                "/v1/admin/trigs",
                json=invalid_data,
                headers={"Authorization": "Bearer mock_token"},
            )

            assert response.status_code == 400
            assert "Invalid type_id" in response.json()["detail"]

    def test_create_trig_missing_required_field_returns_422(
        self, db: Session, admin_user
    ):
        """Test that creating a trig with missing required field returns 422."""
        with patch("api.api.deps.auth0_validator.validate_auth0_token") as mock:
            mock.return_value = {
                "token_type": "auth0",
                "auth0_user_id": admin_user.auth0_user_id,
                "sub": admin_user.auth0_user_id,
                "scope": "api:write api:admin",
            }

            # Missing 'name' field
            invalid_data = {
                "status_id": 1,
                "wgs_lat": "51.50000",
                "wgs_long": "-0.12000",
                "osgb_eastings": 530000,
                "osgb_northings": 180000,
                "admin_comment": "Test",
            }

            response = client.post(
                "/v1/admin/trigs",
                json=invalid_data,
                headers={"Authorization": "Bearer mock_token"},
            )

            assert response.status_code == 422

    def test_create_trig_sets_needs_attention_to_zero(
        self, db: Session, admin_user, valid_trig_data
    ):
        """Test that newly created trig has needs_attention set to 0."""
        with patch("api.api.deps.auth0_validator.validate_auth0_token") as mock:
            mock.return_value = {
                "token_type": "auth0",
                "auth0_user_id": admin_user.auth0_user_id,
                "sub": admin_user.auth0_user_id,
                "scope": "api:write api:admin",
            }

            response = client.post(
                "/v1/admin/trigs",
                json=valid_trig_data,
                headers={"Authorization": "Bearer mock_token"},
            )

            assert response.status_code == 201
            data = response.json()
            assert data["needs_attention"] == 0

    def test_create_trig_includes_admin_comment_in_attention_comment(
        self, db: Session, admin_user, valid_trig_data
    ):
        """Test that admin_comment is included in attention_comment history."""
        with patch("api.api.deps.auth0_validator.validate_auth0_token") as mock:
            mock.return_value = {
                "token_type": "auth0",
                "auth0_user_id": admin_user.auth0_user_id,
                "sub": admin_user.auth0_user_id,
                "scope": "api:write api:admin",
            }

            response = client.post(
                "/v1/admin/trigs",
                json=valid_trig_data,
                headers={"Authorization": "Bearer mock_token"},
            )

            assert response.status_code == 201
            data = response.json()
            assert "CREATED" in data["attention_comment"]
            assert valid_trig_data["admin_comment"] in data["attention_comment"]
            assert admin_user.name in data["attention_comment"]

    def test_create_trig_with_legal_message(
        self, db: Session, admin_user, valid_trig_data
    ):
        """Test that legal_message is saved correctly."""
        with patch("api.api.deps.auth0_validator.validate_auth0_token") as mock:
            mock.return_value = {
                "token_type": "auth0",
                "auth0_user_id": admin_user.auth0_user_id,
                "sub": admin_user.auth0_user_id,
                "scope": "api:write api:admin",
            }

            data_with_legal = valid_trig_data.copy()
            data_with_legal["legal_message"] = "<p>Access restricted</p>"

            response = client.post(
                "/v1/admin/trigs",
                json=data_with_legal,
                headers={"Authorization": "Bearer mock_token"},
            )

            assert response.status_code == 201
            data = response.json()
            assert data["legal_message"] == "<p>Access restricted</p>"

    def test_create_multiple_trigs_get_unique_waypoints(
        self, db: Session, admin_user, valid_trig_data
    ):
        """Test that multiple created trigs get unique waypoints."""
        with patch("api.api.deps.auth0_validator.validate_auth0_token") as mock:
            mock.return_value = {
                "token_type": "auth0",
                "auth0_user_id": admin_user.auth0_user_id,
                "sub": admin_user.auth0_user_id,
                "scope": "api:write api:admin",
            }

            waypoints = []
            for i in range(3):
                data = valid_trig_data.copy()
                data["name"] = f"Test Trig {i}"

                response = client.post(
                    "/v1/admin/trigs",
                    json=data,
                    headers={"Authorization": "Bearer mock_token"},
                )

                assert response.status_code == 201
                waypoints.append(response.json()["waypoint"])

            # All waypoints should be unique
            assert len(waypoints) == len(set(waypoints))

    def test_created_trig_is_retrievable(
        self, db: Session, admin_user, valid_trig_data
    ):
        """Test that the created trig can be retrieved from the database."""
        with patch("api.api.deps.auth0_validator.validate_auth0_token") as mock:
            mock.return_value = {
                "token_type": "auth0",
                "auth0_user_id": admin_user.auth0_user_id,
                "sub": admin_user.auth0_user_id,
                "scope": "api:write api:admin",
            }

            response = client.post(
                "/v1/admin/trigs",
                json=valid_trig_data,
                headers={"Authorization": "Bearer mock_token"},
            )

            assert response.status_code == 201
            trig_id = response.json()["id"]

            # Verify the trig exists in the database
            trig = trig_crud.get_trig_by_id(db, trig_id)
            assert trig is not None
            assert trig.name == valid_trig_data["name"]
