"""
Test edge cases in get_trig_map endpoint.
"""

from datetime import date, time
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from api.models.trig import Trig


def test_get_trig_map_invalid_dot_colour(client: TestClient, db: Session):
    """Test get_trig_map with invalid dot_colour (triggers fallback)."""
    # Create a test trig
    test_trig = Trig(
        id=100,
        waypoint="TP0100",
        name="Test Trigpoint 100",
        status_id=10,
        user_added=0,
        current_use="Passive station",
        historic_use="Primary",
        physical_type="Pillar",
        wgs_lat=Decimal("51.50000"),
        wgs_long=Decimal("-0.12500"),
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
    db.add(test_trig)
    db.commit()
    db.refresh(test_trig)

    # Call with invalid dot_colour (too short hex) - should trigger fallback to (0, 0, 170, 255)
    response = client.get(
        f"/v1/trigs/{test_trig.id}/map",
        params={
            "dot_colour": "#abc",  # Only 3 hex digits, not 6
        },
    )

    # Should still return a valid PNG image
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"
    assert len(response.content) > 0


def test_get_trig_map_extreme_dot_sizes(client: TestClient, db: Session):
    """Test get_trig_map with extreme dot sizes (boundary values)."""
    test_trig = Trig(
        id=101,
        waypoint="TP0101",
        name="Test Trigpoint 101",
        status_id=10,
        user_added=0,
        current_use="Passive station",
        historic_use="Primary",
        physical_type="Pillar",
        wgs_lat=Decimal("51.50000"),
        wgs_long=Decimal("-0.12500"),
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
    db.add(test_trig)
    db.commit()
    db.refresh(test_trig)

    # Test minimum dot size (1 pixel)
    response = client.get(
        f"/v1/trigs/{test_trig.id}/map",
        params={"dot_diameter": 1},
    )

    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"

    # Test maximum dot size (100 pixels)
    response = client.get(
        f"/v1/trigs/{test_trig.id}/map",
        params={"dot_diameter": 100},
    )

    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"
