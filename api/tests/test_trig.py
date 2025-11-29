"""
Tests for trig endpoints.
"""

from datetime import date, time
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from api.core.config import settings
from api.models.attr import Attr, AttrSet, AttrSetAttrVal, AttrSource, AttrVal
from api.models.trig import Trig
from api.models.trigstats import TrigStats


def test_get_trig_success_minimal(client: TestClient, db: Session):
    """Test getting a trig by ID - success case."""
    # Create a test trig
    test_trig = Trig(
        waypoint="TP0001",
        name="Test Trigpoint",
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

    # Test the endpoint
    response = client.get(f"{settings.API_V1_STR}/trigs/{test_trig.id}")
    assert response.status_code == 200

    data = response.json()
    assert data["id"] == test_trig.id
    assert data["waypoint"] == "TP0001"
    assert data["name"] == "Test Trigpoint"
    assert data["wgs_lat"] == "51.50000"
    assert "county" not in data  # county is in details only now
    # minimal fields present
    assert set(
        [
            "id",
            "waypoint",
            "name",
            "status_name",
            "physical_type",
            "condition",
            "wgs_lat",
            "wgs_long",
            "osgb_gridref",
        ]
    ).issubset(data.keys())


def test_get_trig_with_details_include(client: TestClient, db: Session):
    import uuid

    waypoint = f"TP{uuid.uuid4().hex[:6]}"[:8]  # Ensure max 8 chars

    test_trig = Trig(
        waypoint=waypoint,
        name="Include Trig",
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
        fb_number="S1235",
        stn_number="TEST124",
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

    response = client.get(f"{settings.API_V1_STR}/trigs/{test_trig.id}?include=details")
    assert response.status_code == 200
    data = response.json()
    assert "details" in data and isinstance(data["details"], dict)
    assert data["details"]["postcode"] == "SW1A 1"
    assert data["details"]["county"] == "London"


def test_get_trig_not_found(client: TestClient, db: Session):
    """Test getting a trig by ID - not found case."""
    response = client.get(f"{settings.API_V1_STR}/trigs/99999")
    assert response.status_code == 404
    assert response.json()["detail"] == "Trigpoint not found"


def test_get_trig_by_waypoint_success_minimal(client: TestClient, db: Session):
    """Test getting a trig by waypoint - success case."""
    # Create a test trig
    import uuid

    waypoint = f"TP{uuid.uuid4().hex[:6]}"[:8]  # Ensure max 8 chars
    test_trig = Trig(
        waypoint=waypoint,
        name="Another Trigpoint",
        status_id=10,
        user_added=0,
        current_use="Passive station",
        historic_use="Primary",
        physical_type="Pillar",
        wgs_lat=Decimal("52.50000"),
        wgs_long=Decimal("-1.12500"),
        wgs_height=150,
        osgb_eastings=440000,
        osgb_northings=290000,
        osgb_gridref="SP 40000 90000",
        osgb_height=145,
        fb_number="S5678",
        stn_number="TEST456",
        permission_ind="Y",
        condition="G",
        postcode="B1 1AA",
        county="West Midlands",
        town="Birmingham",
        needs_attention=0,
        attention_comment="",
        crt_date=date(2023, 1, 2),
        crt_time=time(14, 30, 0),
        crt_user_id=2,
        crt_ip_addr="192.168.1.1",
    )
    db.add(test_trig)
    db.commit()

    db.refresh(test_trig)

    # Test the endpoint
    response = client.get(f"{settings.API_V1_STR}/trigs/waypoint/{test_trig.waypoint}")
    assert response.status_code == 200

    data = response.json()
    assert data["waypoint"] == test_trig.waypoint
    assert data["name"] == "Another Trigpoint"
    assert "county" not in data


def test_get_trig_by_waypoint_not_found(client: TestClient, db: Session):
    """Test getting a trig by waypoint - not found case."""
    response = client.get(f"{settings.API_V1_STR}/trigs/waypoint/NONEXISTENT")
    assert response.status_code == 404
    assert response.json()["detail"] == "Trigpoint not found"


def test_search_trigs_by_name(client: TestClient, db: Session):
    """Test searching trigs by name."""
    # Create test trigs
    trig1 = Trig(
        waypoint="TP0001",
        name="Ben Nevis",
        status_id=10,
        user_added=0,
        current_use="Passive station",
        historic_use="Primary",
        physical_type="Pillar",
        wgs_lat=Decimal("56.79000"),
        wgs_long=Decimal("-5.00000"),
        wgs_height=1345,
        osgb_eastings=216000,
        osgb_northings=771000,
        osgb_gridref="NN 16000 71000",
        osgb_height=1344,
        fb_number="S9999",
        stn_number="BENNEVIS",
        permission_ind="Y",
        condition="G",
        postcode="PH15 4",
        county="Highland",
        town="Fort William",
        needs_attention=0,
        attention_comment="",
        crt_date=date(2023, 1, 3),
        crt_time=time(9, 0, 0),
        crt_user_id=1,
        crt_ip_addr="10.0.0.1",
    )

    trig2 = Trig(
        waypoint="TP0001",
        name="Ben More",
        status_id=10,
        user_added=0,
        current_use="Passive station",
        historic_use="Primary",
        physical_type="Pillar",
        wgs_lat=Decimal("56.42000"),
        wgs_long=Decimal("-6.02000"),
        wgs_height=966,
        osgb_eastings=165000,
        osgb_northings=732000,
        osgb_gridref="NM 65000 32000",
        osgb_height=965,
        fb_number="S8888",
        stn_number="BENMORE",
        permission_ind="Y",
        condition="G",
        postcode="PA75 6",
        county="Argyll and Bute",
        town="Craignure",
        needs_attention=0,
        attention_comment="",
        crt_date=date(2023, 1, 4),
        crt_time=time(11, 45, 0),
        crt_user_id=2,
        crt_ip_addr="172.16.0.1",
    )

    db.add_all([trig1, trig2])
    db.commit()

    # Test search
    response = client.get(f"{settings.API_V1_STR}/trigs?name=Ben&limit=10&skip=0")
    assert response.status_code == 200

    data = response.json()
    assert "items" in data
    names = [t["name"] for t in data["items"]]
    assert "Ben Nevis" in names
    assert "Ben More" in names


def test_get_trig_count(client: TestClient, db: Session):
    """Test getting total trig count."""
    # The test database should start empty, but let's add one record
    test_trig = Trig(
        waypoint="TP0001",
        name="Count Test",
        status_id=10,
        user_added=0,
        current_use="Passive station",
        historic_use="Primary",
        physical_type="Pillar",
        wgs_lat=Decimal("50.00000"),
        wgs_long=Decimal("-5.00000"),
        wgs_height=200,
        osgb_eastings=200000,
        osgb_northings=100000,
        osgb_gridref="SW 00000 00000",
        osgb_height=195,
        fb_number="S0000",
        stn_number="COUNT",
        permission_ind="Y",
        condition="G",
        postcode="TR1 1",
        county="Cornwall",
        town="Truro",
        needs_attention=0,
        attention_comment="",
        crt_date=date(2023, 1, 5),
        crt_time=time(16, 20, 0),
        crt_user_id=1,
        crt_ip_addr="203.0.113.1",
    )
    db.add(test_trig)
    db.commit()

    db.refresh(test_trig)

    # Removed stats count endpoint; emulate count via listing
    response = client.get(f"{settings.API_V1_STR}/trigs?limit=1&skip=0")
    assert response.status_code == 200
    body = response.json()
    assert "pagination" in body and body["pagination"]["total"] >= 1


def test_get_trig_details_endpoint(client: TestClient, db: Session):
    import uuid

    waypoint = f"TP{uuid.uuid4().hex[:6]}"[:8]  # Ensure max 8 chars

    trig = Trig(
        waypoint=waypoint,
        name="Details Trig",
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
        fb_number="S7777",
        stn_number="DET123",
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

    response = client.get(f"{settings.API_V1_STR}/trigs/{trig.id}?include=details")
    assert response.status_code == 200
    data = response.json()
    assert data["details"]["postcode"] == "SW1A 1"
    assert data["details"]["county"] == "London"
    assert data["details"]["stn_number"] == "DET123"


def test_get_trig_stats_endpoint_and_include(client: TestClient, db: Session):
    import uuid

    waypoint = f"TP{uuid.uuid4().hex[:6]}"[:8]  # Ensure max 8 chars

    trig = Trig(
        waypoint=waypoint,
        name="Stats Trig",
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
        fb_number="S7778",
        stn_number="STATS1",
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

    stats = TrigStats(
        id=trig.id,  # TrigStats.id is actually the trig_id
        logged_first=date(2020, 1, 1),
        logged_last=date(2025, 1, 1),
        logged_count=5,
        found_last=date(2025, 1, 1),
        found_count=4,
        photo_count=3,
        score_mean=Decimal("6.50"),
        score_baysian=Decimal("6.40"),
        area_osgb_height=0,
    )
    db.add(stats)
    db.commit()
    db.refresh(stats)

    # include stats with base
    resp_inc = client.get(
        f"{settings.API_V1_STR}/trigs/{trig.id}?include=stats,details"
    )
    assert resp_inc.status_code == 200
    data = resp_inc.json()
    assert "stats" in data and data["stats"]["logged_count"] == 5
    assert "details" in data and data["details"]["county"] == "London"


def test_get_trig_attrs_include(client: TestClient, db: Session):
    """Test getting a trig with attrs include parameter."""
    # Create a test trig
    trig = Trig(
        waypoint="TP0001",
        name="Attrs Trig",
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
        fb_number="S8888",
        stn_number="ATTR1",
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

    # Create attribute source
    attr_source = AttrSource(
        name="Test Source",
        url="https://example.com",
        sort_order=1,
    )
    db.add(attr_source)
    db.commit()

    db.refresh(attr_source)

    # Create attributes
    attr1 = Attr(
        attrsource_id=attr_source.id,
        name="Column 1",
        description="Test column 1",
        mandatory=1,
        multivalued=0,
        grouped=0,
        sort_order=1,
    )
    attr2 = Attr(
        attrsource_id=attr_source.id,
        name="Column 2",
        description="Test column 2",
        mandatory=1,
        multivalued=0,
        grouped=0,
        sort_order=2,
    )
    db.add(attr1)
    db.add(attr2)
    db.commit()

    db.refresh(attr1)
    db.refresh(attr2)

    # Create attribute set
    attrset = AttrSet(
        trig_id=trig.id,
        attrsource_id=attr_source.id,
        sort_order=1,
    )
    db.add(attrset)
    db.commit()

    db.refresh(attrset)

    # Create attribute values
    attrval1 = AttrVal(
        attr_id=attr1.id,
        value_string="Value 1",
    )
    attrval2 = AttrVal(
        attr_id=attr2.id,
        value_string="Value 2",
    )
    db.add(attrval1)
    db.add(attrval2)
    db.commit()

    db.refresh(attrval1)
    db.refresh(attrval2)

    # Create junction records
    junction1 = AttrSetAttrVal(attrset_id=attrset.id, attrval_id=attrval1.id)
    junction2 = AttrSetAttrVal(attrset_id=attrset.id, attrval_id=attrval2.id)
    db.add(junction1)
    db.add(junction2)
    db.commit()

    # Test with include=attrs
    response = client.get(f"{settings.API_V1_STR}/trigs/{trig.id}?include=attrs")
    assert response.status_code == 200
    data = response.json()

    # Verify attrs structure
    assert "attrs" in data
    assert isinstance(data["attrs"], list)
    assert len(data["attrs"]) == 1

    # Verify source info
    source_data = data["attrs"][0]
    assert source_data["source"]["id"] == attr_source.id
    assert source_data["source"]["name"] == "Test Source"
    assert source_data["source"]["url"] == "https://example.com"

    # Verify attr_names
    assert "attr_names" in source_data
    assert source_data["attr_names"][str(attr1.id)] == "Column 1"
    assert source_data["attr_names"][str(attr2.id)] == "Column 2"

    # Verify attribute sets
    assert "attribute_sets" in source_data
    assert len(source_data["attribute_sets"]) == 1
    assert source_data["attribute_sets"][0]["values"][str(attr1.id)] == "Value 1"
    assert source_data["attribute_sets"][0]["values"][str(attr2.id)] == "Value 2"
