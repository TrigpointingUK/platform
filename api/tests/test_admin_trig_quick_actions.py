"""
Tests for admin trig quick actions from log detail page.

Tests cover:
- POST /v1/admin/trigs/{trig_id}/move-to-log/{log_id}
- POST /v1/admin/trigs/{trig_id}/set-condition-from-log/{log_id}
"""

import uuid
from datetime import date, time
from decimal import Decimal
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from api.crud.user import create_user
from api.main import app
from api.models.trig import Trig
from api.models.user import TLog

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
def test_trig(db: Session, test_user):
    """Create a test trig for testing."""
    trig = Trig(
        waypoint=f"TP{uuid.uuid4().hex[:5].upper()}",
        name="Test Trigpoint",
        fb_number="FB001",
        stn_number="STN001",
        status_id=1,
        user_added=0,
        current_use="none",
        historic_use="none",
        condition="G",  # Good condition
        wgs_lat=Decimal("51.50000"),
        wgs_long=Decimal("-0.12000"),
        wgs_height=Decimal("50.0"),
        osgb_eastings=Decimal("530000.0000"),
        osgb_northings=Decimal("180000.0000"),
        osgb_gridref="TQ 30000 80000",
        osgb_height=Decimal("48.5"),
        town="London",
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


@pytest.fixture
def test_log_with_location(db: Session, test_trig, test_user):
    """Create a test log with location data."""
    log = TLog(
        trig_id=test_trig.id,
        user_id=test_user.id,
        date=date(2024, 1, 15),
        time=time(14, 30, 0),
        osgb_eastings=530100,  # Different from trig
        osgb_northings=180100,  # Different from trig
        osgb_gridref="TQ 30100 80100",
        fb_number="FB001",
        condition="D",  # Destroyed condition (different from trig)
        comment="Test log with new location",
        score=8,
        ip_addr="127.0.0.1",
        source="W",
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return log


@pytest.fixture
def test_log_without_location(db: Session, test_trig, test_user):
    """Create a test log without location data."""
    log = TLog(
        trig_id=test_trig.id,
        user_id=test_user.id,
        date=date(2024, 1, 16),
        time=time(10, 0, 0),
        osgb_eastings=None,
        osgb_northings=None,
        osgb_gridref=None,
        fb_number="FB001",
        condition="P",
        comment="Test log without location",
        score=7,
        ip_addr="127.0.0.1",
        source="W",
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return log


@pytest.fixture
def test_log_without_condition(db: Session, test_trig, test_user):
    """Create a test log without condition."""
    log = TLog(
        trig_id=test_trig.id,
        user_id=test_user.id,
        date=date(2024, 1, 17),
        time=time(11, 0, 0),
        osgb_eastings=530200,
        osgb_northings=180200,
        osgb_gridref="TQ 30200 80200",
        fb_number="FB001",
        condition=None,  # No condition
        comment="Test log without condition",
        score=6,
        ip_addr="127.0.0.1",
        source="W",
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return log


# ============================================================================
# Move Trig to Log Location Tests
# ============================================================================


class TestMoveTrigToLogLocation:
    """Tests for the move trig to log location endpoint."""

    def test_move_trig_to_log_location_success(
        self, db: Session, test_trig, test_log_with_location, admin_user
    ):
        """Test successfully moving a trig to a log's location."""
        with patch("api.api.deps.auth0_validator.validate_auth0_token") as mock:
            mock.return_value = {
                "token_type": "auth0",
                "auth0_user_id": admin_user.auth0_user_id,
                "sub": admin_user.auth0_user_id,
                "scope": "api:write api:admin",
            }

            response = client.post(
                f"/v1/admin/trigs/{test_trig.id}/move-to-log/{test_log_with_location.id}",
                headers={"Authorization": "Bearer mock_token"},
            )

            assert response.status_code == 200
            data = response.json()

            # Check location was updated
            assert data["osgb_eastings"] == 530100
            assert data["osgb_northings"] == 180100
            assert data["osgb_gridref"] == "TQ 30100 80100"

            # Check condition was set to 'M' (Moved)
            assert data["condition"] == "M"

            # Check attention_comment was updated
            assert "MOVED" in data["attention_comment"]
            assert f"log #{test_log_with_location.id}" in data["attention_comment"]

            # Check needs_attention was NOT changed
            assert data["needs_attention"] == 0

    def test_move_trig_to_log_location_not_found_trig(self, db: Session, admin_user):
        """Test moving a non-existent trig."""
        with patch("api.api.deps.auth0_validator.validate_auth0_token") as mock:
            mock.return_value = {
                "token_type": "auth0",
                "auth0_user_id": admin_user.auth0_user_id,
                "sub": admin_user.auth0_user_id,
                "scope": "api:write api:admin",
            }

            response = client.post(
                "/v1/admin/trigs/999999/move-to-log/1",
                headers={"Authorization": "Bearer mock_token"},
            )

            assert response.status_code == 404
            assert "Trigpoint not found" in response.json()["detail"]

    def test_move_trig_to_log_location_not_found_log(
        self, db: Session, test_trig, admin_user
    ):
        """Test moving to a non-existent log."""
        with patch("api.api.deps.auth0_validator.validate_auth0_token") as mock:
            mock.return_value = {
                "token_type": "auth0",
                "auth0_user_id": admin_user.auth0_user_id,
                "sub": admin_user.auth0_user_id,
                "scope": "api:write api:admin",
            }

            response = client.post(
                f"/v1/admin/trigs/{test_trig.id}/move-to-log/999999",
                headers={"Authorization": "Bearer mock_token"},
            )

            assert response.status_code == 404
            assert "Log not found" in response.json()["detail"]

    def test_move_trig_to_log_wrong_trig(
        self, db: Session, test_trig, test_user, admin_user
    ):
        """Test moving with a log that belongs to a different trig."""
        # Create another trig
        other_trig = Trig(
            waypoint=f"TP{uuid.uuid4().hex[:5].upper()}",
            name="Other Trigpoint",
            fb_number="FB002",
            stn_number="STN002",
            status_id=1,
            user_added=0,
            current_use="none",
            historic_use="none",
            condition="G",
            wgs_lat=Decimal("52.00000"),
            wgs_long=Decimal("-1.00000"),
            osgb_eastings=Decimal("450000.0000"),
            osgb_northings=Decimal("250000.0000"),
            osgb_gridref="SP 50000 50000",
            town="Birmingham",
            permission_ind="Y",
            needs_attention=0,
            attention_comment="",
            crt_date=date(2023, 1, 1),
            crt_time=time(0, 0, 0),
            crt_user_id=test_user.id,
            crt_ip_addr="127.0.0.1",
        )
        db.add(other_trig)
        db.commit()
        db.refresh(other_trig)

        # Create a log for the other trig
        other_log = TLog(
            trig_id=other_trig.id,
            user_id=test_user.id,
            date=date(2024, 1, 20),
            osgb_eastings=450100,
            osgb_northings=250100,
            osgb_gridref="SP 50100 50100",
            condition="G",
            score=5,
            source="W",
        )
        db.add(other_log)
        db.commit()
        db.refresh(other_log)

        with patch("api.api.deps.auth0_validator.validate_auth0_token") as mock:
            mock.return_value = {
                "token_type": "auth0",
                "auth0_user_id": admin_user.auth0_user_id,
                "sub": admin_user.auth0_user_id,
                "scope": "api:write api:admin",
            }

            # Try to move test_trig using other_log (which belongs to other_trig)
            response = client.post(
                f"/v1/admin/trigs/{test_trig.id}/move-to-log/{other_log.id}",
                headers={"Authorization": "Bearer mock_token"},
            )

            assert response.status_code == 400
            assert "does not belong to trig" in response.json()["detail"]

    def test_move_trig_to_log_no_location(
        self, db: Session, test_trig, test_log_without_location, admin_user
    ):
        """Test moving with a log that has no location data."""
        with patch("api.api.deps.auth0_validator.validate_auth0_token") as mock:
            mock.return_value = {
                "token_type": "auth0",
                "auth0_user_id": admin_user.auth0_user_id,
                "sub": admin_user.auth0_user_id,
                "scope": "api:write api:admin",
            }

            response = client.post(
                f"/v1/admin/trigs/{test_trig.id}/move-to-log/{test_log_without_location.id}",
                headers={"Authorization": "Bearer mock_token"},
            )

            assert response.status_code == 400
            assert "does not have location coordinates" in response.json()["detail"]


# ============================================================================
# Set Trig Condition from Log Tests
# ============================================================================


class TestSetTrigConditionFromLog:
    """Tests for the set trig condition from log endpoint."""

    def test_set_condition_success(
        self, db: Session, test_trig, test_log_with_location, admin_user
    ):
        """Test successfully setting a trig's condition from a log."""
        with patch("api.api.deps.auth0_validator.validate_auth0_token") as mock:
            mock.return_value = {
                "token_type": "auth0",
                "auth0_user_id": admin_user.auth0_user_id,
                "sub": admin_user.auth0_user_id,
                "scope": "api:write api:admin",
            }

            # Trig starts with 'G', log has 'D'
            assert test_trig.condition == "G"
            assert test_log_with_location.condition == "D"

            response = client.post(
                f"/v1/admin/trigs/{test_trig.id}/set-condition-from-log/{test_log_with_location.id}",
                headers={"Authorization": "Bearer mock_token"},
            )

            assert response.status_code == 200
            data = response.json()

            # Check condition was updated
            assert data["condition"] == "D"

            # Check attention_comment was updated
            assert "CONDITION" in data["attention_comment"]
            assert "'G' -> 'D'" in data["attention_comment"]
            assert f"log #{test_log_with_location.id}" in data["attention_comment"]

            # Check needs_attention was NOT changed
            assert data["needs_attention"] == 0

    def test_set_condition_not_found_trig(self, db: Session, admin_user):
        """Test setting condition for a non-existent trig."""
        with patch("api.api.deps.auth0_validator.validate_auth0_token") as mock:
            mock.return_value = {
                "token_type": "auth0",
                "auth0_user_id": admin_user.auth0_user_id,
                "sub": admin_user.auth0_user_id,
                "scope": "api:write api:admin",
            }

            response = client.post(
                "/v1/admin/trigs/999999/set-condition-from-log/1",
                headers={"Authorization": "Bearer mock_token"},
            )

            assert response.status_code == 404
            assert "Trigpoint not found" in response.json()["detail"]

    def test_set_condition_not_found_log(self, db: Session, test_trig, admin_user):
        """Test setting condition from a non-existent log."""
        with patch("api.api.deps.auth0_validator.validate_auth0_token") as mock:
            mock.return_value = {
                "token_type": "auth0",
                "auth0_user_id": admin_user.auth0_user_id,
                "sub": admin_user.auth0_user_id,
                "scope": "api:write api:admin",
            }

            response = client.post(
                f"/v1/admin/trigs/{test_trig.id}/set-condition-from-log/999999",
                headers={"Authorization": "Bearer mock_token"},
            )

            assert response.status_code == 404
            assert "Log not found" in response.json()["detail"]

    def test_set_condition_wrong_trig(
        self, db: Session, test_trig, test_user, admin_user
    ):
        """Test setting condition with a log that belongs to a different trig."""
        # Create another trig
        other_trig = Trig(
            waypoint=f"TP{uuid.uuid4().hex[:5].upper()}",
            name="Other Trigpoint 2",
            fb_number="FB003",
            stn_number="STN003",
            status_id=1,
            user_added=0,
            current_use="none",
            historic_use="none",
            condition="G",
            wgs_lat=Decimal("52.50000"),
            wgs_long=Decimal("-1.50000"),
            osgb_eastings=Decimal("440000.0000"),
            osgb_northings=Decimal("260000.0000"),
            osgb_gridref="SP 40000 60000",
            town="Coventry",
            permission_ind="Y",
            needs_attention=0,
            attention_comment="",
            crt_date=date(2023, 1, 1),
            crt_time=time(0, 0, 0),
            crt_user_id=test_user.id,
            crt_ip_addr="127.0.0.1",
        )
        db.add(other_trig)
        db.commit()
        db.refresh(other_trig)

        # Create a log for the other trig
        other_log = TLog(
            trig_id=other_trig.id,
            user_id=test_user.id,
            date=date(2024, 1, 21),
            condition="P",
            score=4,
            source="W",
        )
        db.add(other_log)
        db.commit()
        db.refresh(other_log)

        with patch("api.api.deps.auth0_validator.validate_auth0_token") as mock:
            mock.return_value = {
                "token_type": "auth0",
                "auth0_user_id": admin_user.auth0_user_id,
                "sub": admin_user.auth0_user_id,
                "scope": "api:write api:admin",
            }

            # Try to set test_trig condition using other_log
            response = client.post(
                f"/v1/admin/trigs/{test_trig.id}/set-condition-from-log/{other_log.id}",
                headers={"Authorization": "Bearer mock_token"},
            )

            assert response.status_code == 400
            assert "does not belong to trig" in response.json()["detail"]

    def test_set_condition_log_no_condition(
        self, db: Session, test_trig, test_log_without_condition, admin_user
    ):
        """Test setting condition from a log that has no condition."""
        with patch("api.api.deps.auth0_validator.validate_auth0_token") as mock:
            mock.return_value = {
                "token_type": "auth0",
                "auth0_user_id": admin_user.auth0_user_id,
                "sub": admin_user.auth0_user_id,
                "scope": "api:write api:admin",
            }

            response = client.post(
                f"/v1/admin/trigs/{test_trig.id}/set-condition-from-log/{test_log_without_condition.id}",
                headers={"Authorization": "Bearer mock_token"},
            )

            assert response.status_code == 400
            assert "does not have a condition set" in response.json()["detail"]
