"""
Tests for user log-timeline endpoint.

This endpoint provides lightweight timeline data for animated map visualisation.
"""

import uuid
from datetime import date, time

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from api.core.config import settings
from api.models.condition import Condition
from api.models.user import TLog, User


@pytest.fixture
def test_conditions(db: Session):
    """Create test condition records with log_colour values."""
    conditions = [
        Condition(
            code="G",
            name="Good",
            description="Trigpoint in good condition",
            log_colour="green",
            trig_colour="green",
            sort_order=10,
        ),
        Condition(
            code="S",
            name="Slightly damaged",
            description="Trigpoint slightly damaged",
            log_colour="yellow",
            trig_colour="yellow",
            sort_order=20,
        ),
        Condition(
            code="D",
            name="Damaged",
            description="Trigpoint damaged",
            log_colour="yellow",
            trig_colour="yellow",
            sort_order=30,
        ),
        Condition(
            code="X",
            name="Destroyed",
            description="Trigpoint destroyed",
            log_colour="red",
            trig_colour="red",
            sort_order=40,
        ),
        Condition(
            code="N",
            name="Not found",
            description="Could not find trigpoint",
            log_colour=None,  # No colour - uncertain
            trig_colour=None,
            sort_order=50,
        ),
    ]
    for c in conditions:
        # Check if condition already exists
        existing = db.query(Condition).filter(Condition.code == c.code).first()
        if not existing:
            db.add(c)
    db.commit()
    return conditions


def test_get_log_timeline_user_not_found(client: TestClient, db: Session):
    """Test getting timeline for non-existent user returns 404."""
    response = client.get(f"{settings.API_V1_STR}/users/99999/log-timeline")
    assert response.status_code == 404
    assert response.json()["detail"] == "User not found"


def test_get_log_timeline_empty(client: TestClient, db: Session):
    """Test getting timeline for user with no logs returns empty array."""
    unique_name = f"emptyuser_{uuid.uuid4().hex[:8]}"
    user = User(
        name=unique_name,
        firstname="Empty",
        surname="User",
        email=f"{unique_name}@example.com",
        cryptpw="$1$test$hash",
        email_valid="Y",
        public_ind="Y",
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    response = client.get(f"{settings.API_V1_STR}/users/{user.id}/log-timeline")
    assert response.status_code == 200
    data = response.json()
    assert data == []


def test_get_log_timeline_success(
    client: TestClient, db: Session, make_trig, test_conditions
):
    """Test getting timeline returns sorted logs with correct colours."""
    unique_name = f"timelineuser_{uuid.uuid4().hex[:8]}"
    user = User(
        name=unique_name,
        firstname="Timeline",
        surname="User",
        email=f"{unique_name}@example.com",
        cryptpw="$1$test$hash",
        email_valid="Y",
        public_ind="Y",
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # Create trigs with different coordinates
    trig1 = make_trig(wgs_lat=51.5074, wgs_long=-0.1278)
    trig2 = make_trig(wgs_lat=54.9783, wgs_long=-1.6178)
    trig3 = make_trig(wgs_lat=53.4808, wgs_long=-2.2426)

    # Create logs with different dates and conditions
    logs = [
        TLog(
            user_id=user.id,
            trig_id=trig1.id,
            date=date(2023, 1, 15),
            time=time(10, 0, 0),
            condition="G",  # green
            osgb_eastings=0,
            osgb_northings=0,
            osgb_gridref="TQ 00000 00000",
        ),
        TLog(
            user_id=user.id,
            trig_id=trig2.id,
            date=date(2023, 2, 20),
            time=time(11, 0, 0),
            condition="S",  # yellow
            osgb_eastings=0,
            osgb_northings=0,
            osgb_gridref="NZ 00000 00000",
        ),
        TLog(
            user_id=user.id,
            trig_id=trig3.id,
            date=date(2023, 3, 25),
            time=time(12, 0, 0),
            condition="X",  # red
            osgb_eastings=0,
            osgb_northings=0,
            osgb_gridref="SJ 00000 00000",
        ),
    ]
    db.add_all(logs)
    db.commit()

    response = client.get(f"{settings.API_V1_STR}/users/{user.id}/log-timeline")
    assert response.status_code == 200
    data = response.json()

    # Should have 3 logs
    assert len(data) == 3

    # Should be sorted by date ascending
    assert data[0]["date"] == "2023-01-15"
    assert data[1]["date"] == "2023-02-20"
    assert data[2]["date"] == "2023-03-25"

    # Check coordinates
    assert data[0]["lat"] == pytest.approx(51.5074, rel=1e-4)
    assert data[0]["lon"] == pytest.approx(-0.1278, rel=1e-4)

    # Check colours
    assert data[0]["colour"] == "green"
    assert data[1]["colour"] == "yellow"
    assert data[2]["colour"] == "red"


def test_get_log_timeline_null_condition_is_grey(
    client: TestClient, db: Session, make_trig, test_conditions
):
    """Test that logs with null/unknown conditions get grey colour."""
    unique_name = f"greyuser_{uuid.uuid4().hex[:8]}"
    user = User(
        name=unique_name,
        firstname="Grey",
        surname="User",
        email=f"{unique_name}@example.com",
        cryptpw="$1$test$hash",
        email_valid="Y",
        public_ind="Y",
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    trig = make_trig(wgs_lat=51.0, wgs_long=-1.0)

    # Create log with N condition (no log_colour)
    log = TLog(
        user_id=user.id,
        trig_id=trig.id,
        date=date(2023, 5, 1),
        time=time(10, 0, 0),
        condition="N",  # Not found - no log_colour
        osgb_eastings=0,
        osgb_northings=0,
        osgb_gridref="TQ 00000 00000",
    )
    db.add(log)
    db.commit()

    response = client.get(f"{settings.API_V1_STR}/users/{user.id}/log-timeline")
    assert response.status_code == 200
    data = response.json()

    assert len(data) == 1
    assert data[0]["colour"] == "grey"


def test_get_log_timeline_multiple_logs_same_date(
    client: TestClient, db: Session, make_trig, test_conditions
):
    """Test that multiple logs on the same date are returned in order."""
    unique_name = f"samedateuser_{uuid.uuid4().hex[:8]}"
    user = User(
        name=unique_name,
        firstname="SameDate",
        surname="User",
        email=f"{unique_name}@example.com",
        cryptpw="$1$test$hash",
        email_valid="Y",
        public_ind="Y",
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # Create trigs with different coordinates
    trig1 = make_trig(wgs_lat=51.5, wgs_long=-0.1)
    trig2 = make_trig(wgs_lat=52.5, wgs_long=-1.1)

    # Create multiple logs on the same date
    logs = [
        TLog(
            user_id=user.id,
            trig_id=trig1.id,
            date=date(2023, 6, 15),
            time=time(10, 0, 0),
            condition="G",
            osgb_eastings=0,
            osgb_northings=0,
            osgb_gridref="TQ 00000 00000",
        ),
        TLog(
            user_id=user.id,
            trig_id=trig2.id,
            date=date(2023, 6, 15),
            time=time(14, 0, 0),
            condition="S",
            osgb_eastings=0,
            osgb_northings=0,
            osgb_gridref="SK 00000 00000",
        ),
    ]
    db.add_all(logs)
    db.commit()

    response = client.get(f"{settings.API_V1_STR}/users/{user.id}/log-timeline")
    assert response.status_code == 200
    data = response.json()

    # Should have 2 logs, both on the same date
    assert len(data) == 2
    assert data[0]["date"] == "2023-06-15"
    assert data[1]["date"] == "2023-06-15"
    # Both should have valid colours
    assert data[0]["colour"] in ["green", "yellow", "red", "grey"]
    assert data[1]["colour"] in ["green", "yellow", "red", "grey"]


def test_get_log_timeline_handles_null_date(
    client: TestClient, db: Session, make_trig, test_conditions
):
    """Test that logs with null dates are included with null date field."""
    unique_name = f"nulldateuser_{uuid.uuid4().hex[:8]}"
    user = User(
        name=unique_name,
        firstname="NullDate",
        surname="User",
        email=f"{unique_name}@example.com",
        cryptpw="$1$test$hash",
        email_valid="Y",
        public_ind="Y",
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    trig = make_trig(wgs_lat=52.0, wgs_long=-1.0)

    log = TLog(
        user_id=user.id,
        trig_id=trig.id,
        date=None,  # No date
        time=None,
        condition="G",
        osgb_eastings=0,
        osgb_northings=0,
        osgb_gridref="TQ 00000 00000",
    )
    db.add(log)
    db.commit()

    response = client.get(f"{settings.API_V1_STR}/users/{user.id}/log-timeline")
    assert response.status_code == 200
    data = response.json()

    assert len(data) == 1
    assert data[0]["date"] is None
    assert data[0]["colour"] == "green"
