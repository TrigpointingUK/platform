"""
Test get_trig_map endpoint.
"""

import uuid
from datetime import date, time
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from api.models.trig import Trig


def create_test_trig(
    db: Session,
    *,
    name: str = "Test Trigpoint",
    waypoint: str | None = None,
    lat: Decimal = Decimal("51.50000"),
    lon: Decimal = Decimal("-0.12500"),
) -> Trig:
    unique_waypoint = waypoint or f"TP{uuid.uuid4().hex[:6]}"[:8]
    trig = Trig(
        waypoint=unique_waypoint,
        name=name,
        status_id=10,
        user_added=0,
        current_use="Passive station",
        historic_use="Primary",
        physical_type="Pillar",
        wgs_lat=lat,
        wgs_long=lon,
        wgs_height=100,
        osgb_eastings=530000,
        osgb_northings=180000,
        osgb_gridref="TQ 30000 80000",
        osgb_height=95,
        fb_number="S1234",
        stn_number="TEST123",
        permission_ind="Y",
        condition="G",
        postcode="SW1A 1",
        county="London",
        town="Westminster",
        needs_attention=0,
        attention_comment="",
        crt_date=date(2023, 1, 1),
        crt_time=time(12, 0, 0),
        crt_user_id=1,
        crt_ip_addr="127.0.0.1",
    )
    db.add(trig)
    db.commit()
    db.refresh(trig)
    return trig


def test_get_trig_map_default_params(client: TestClient, db: Session):
    """Test get_trig_map with default parameters."""
    test_trig = create_test_trig(db)

    # Call the endpoint with default parameters
    response = client.get(f"/v1/trigs/{test_trig.id}/map")

    # Should return a valid PNG image
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"
    assert len(response.content) > 0
    # Verify it's a PNG by checking magic bytes
    assert response.content[:8] == b"\x89PNG\r\n\x1a\n"


def test_get_trig_map_with_custom_dot(client: TestClient, db: Session):
    """Test get_trig_map with custom dot colour and size."""
    test_trig = create_test_trig(
        db,
        name="Test Trigpoint 2",
        lat=Decimal("52.50000"),
        lon=Decimal("-1.12500"),
    )

    # Call with custom dot parameters
    response = client.get(
        f"/v1/trigs/{test_trig.id}/map",
        params={
            "dot_colour": "#ff0000",
            "dot_diameter": 30,
        },
    )

    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"
    assert len(response.content) > 0


def test_get_trig_map_custom_style(client: TestClient, db: Session):
    """Test get_trig_map with custom style parameter."""
    test_trig = create_test_trig(
        db,
        name="Test Trigpoint 3",
        lat=Decimal("53.50000"),
        lon=Decimal("-2.12500"),
    )

    # Call with default style (should work)
    response = client.get(
        f"/v1/trigs/{test_trig.id}/map", params={"style": "stretched53_default"}
    )

    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"
    assert len(response.content) > 0


def test_get_trig_map_not_found(client: TestClient, db: Session):
    """Test get_trig_map with non-existent trig."""
    response = client.get("/v1/trigs/999999/map")

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_get_trig_map_missing_style(client: TestClient, db: Session):
    """Test get_trig_map with non-existent style."""
    test_trig = create_test_trig(
        db,
        name="Test Trigpoint 4",
        lat=Decimal("54.50000"),
        lon=Decimal("-3.12500"),
    )

    # Call with non-existent style
    response = client.get(
        f"/v1/trigs/{test_trig.id}/map", params={"style": "nonexistent_style"}
    )

    assert response.status_code == 404
    assert "style" in response.json()["detail"].lower()
