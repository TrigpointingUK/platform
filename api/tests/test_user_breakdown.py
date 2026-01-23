"""
Integration tests for user profile breakdown endpoint.

Tests the by_type breakdown that groups trigpoints by category and type.
"""

import uuid
from datetime import date, time
from decimal import Decimal

import pytest
from sqlalchemy import func
from sqlalchemy.orm import Session

from api.models.trig import Trig
from api.models.trig_type import TrigCategory, TrigType
from api.models.user import TLog, User


@pytest.fixture
def seed_user_with_logs_and_types(db: Session):
    """
    Seed user, trig types, trigs, and logs for testing user breakdown.

    Uses unique IDs based on UUID to avoid conflicts with parallel tests.
    """
    # Generate unique base ID to avoid conflicts
    base_id = abs(hash(uuid.uuid4().hex[:8])) % 20000 + 10000

    # Get unique sort_order values to avoid conflicts
    max_cat_order = db.query(
        func.coalesce(func.max(TrigCategory.sort_order), 0)
    ).scalar()
    cat_sort_order = max_cat_order + 1

    # Create test user
    unique_name = f"breakdown_test_{base_id}"
    user = User(
        name=unique_name,
        firstname="Test",
        surname="User",
        cryptpw="test",
        email=f"{unique_name}@example.com",
        email_valid="Y",
        public_ind="Y",
        about="Test user for breakdown tests",
    )
    db.add(user)
    db.flush()

    # Create category
    pillar_category = TrigCategory(
        code=f"BKDN_PILLAR_{base_id}",
        name="Pillar",
        description="Trig pillars",
        sort_order=cat_sort_order,
    )
    db.add(pillar_category)
    db.flush()

    # Create types
    pillar_type = TrigType(
        category_id=pillar_category.id,
        code=f"BKDN_PILLAR_{base_id}",
        name="Pillar",
        description="Standard pillar",
        sort_order=1,
    )
    hotine_type = TrigType(
        category_id=pillar_category.id,
        code=f"BKDN_HOTINE_{base_id}",
        name="Hotine Pillar",
        description="Hotine style pillar",
        sort_order=2,
    )
    db.add_all([pillar_type, hotine_type])
    db.flush()

    # Create trigs with types
    trigs = []
    for i, (name, type_obj) in enumerate(
        [
            ("Breakdown Trig 1", pillar_type),
            ("Breakdown Trig 2", hotine_type),
        ]
    ):
        trig = Trig(
            waypoint=f"B{base_id + i}"[:8],
            name=name,
            fb_number=f"FB{base_id + i}",
            stn_number=f"STN{base_id + i}",
            status_id=10,
            user_added=0,
            type_id=type_obj.id,
            current_use="Passive station",
            historic_use="Primary",
            wgs_lat=Decimal("51.5") + Decimal(str(i * 0.01)),
            wgs_long=Decimal("-0.1") + Decimal(str(i * 0.01)),
            wgs_height=100,
            osgb_eastings=530000 + i * 1000,
            osgb_northings=180000 + i * 1000,
            osgb_gridref=f"TQ {30000 + i * 1000} 80000",
            osgb_height=95,
            condition="G",
            county="London",
            town="Westminster",
            permission_ind="Y",
            needs_attention=0,
            attention_comment="",
            crt_date=date(2023, 1, 1),
            crt_time=time(12, 0, 0),
            crt_ip_addr="127.0.0.1",
        )
        trigs.append(trig)
    db.add_all(trigs)
    db.flush()

    # Create logs for the test user
    logs = []
    for i, trig in enumerate(trigs):
        log = TLog(
            trig_id=trig.id,
            user_id=user.id,
            date=date(2024, 1, 1 + i),
            time=time(12, 0, 0),
            condition="G",
            comment=f"Test log {i + 1}",
            score=5,
            source="W",
        )
        logs.append(log)
    db.add_all(logs)
    db.commit()

    yield {
        "user": user,
        "category": pillar_category,
        "pillar_type": pillar_type,
        "hotine_type": hotine_type,
        "trigs": trigs,
        "logs": logs,
    }

    # Cleanup (in reverse order of creation due to FK constraints)
    for log in logs:
        db.delete(log)
    for trig in trigs:
        db.delete(trig)
    db.delete(pillar_type)
    db.delete(hotine_type)
    db.delete(pillar_category)
    db.delete(user)
    db.commit()


def test_user_breakdown_by_type_returns_grouped_data(
    client, db, seed_user_with_logs_and_types
):
    """Test that user breakdown by_type returns data grouped by category."""
    data = seed_user_with_logs_and_types
    user_id = data["user"].id

    response = client.get(f"/v1/users/{user_id}?include=breakdown")
    assert response.status_code == 200

    result = response.json()
    assert "breakdown" in result
    assert "by_type" in result["breakdown"]

    by_type = result["breakdown"]["by_type"]
    assert isinstance(by_type, list)

    # Find our test category (it has a unique code)
    cat_code = data["category"].code
    test_cat = next((c for c in by_type if c["category_code"] == cat_code), None)
    assert test_cat is not None, f"Category {cat_code} not found in {by_type}"
    assert test_cat["category_name"] == "Pillar"
    assert len(test_cat["types"]) == 2

    # Check types are present with correct counts
    type_map = {t["type_code"]: t for t in test_cat["types"]}
    assert data["pillar_type"].code in type_map
    assert data["hotine_type"].code in type_map

    # Each type should have count of 1
    for type_data in test_cat["types"]:
        assert type_data["count"] == 1
