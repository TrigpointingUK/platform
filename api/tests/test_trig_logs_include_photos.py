"""
Tests for include=photos on /v1/trigs/{trig_id}/logs endpoint.
"""

from datetime import UTC, date, datetime, time
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from api.core.config import settings
from api.models.tphoto import TPhoto
from api.models.trig import Trig
from api.models.user import TLog, User


def _ensure_trig(db: Session, trig_id: int) -> None:
    if db.query(Trig).filter(Trig.id == trig_id).first() is not None:
        return

    waypoint = f"TP{trig_id:06d}"[:8]
    db.add(
        Trig(
            id=trig_id,
            waypoint=waypoint,
            name=f"Test Trig {trig_id}",
            status_id=10,
            user_added=0,
            current_use="Passive station",
            historic_use="Primary",
            condition="G",
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
            postcode=None,
            town="Westminster",
            needs_attention=0,
            attention_comment="",
            crt_date=date(2023, 1, 1),
            crt_time=time(12, 0, 0),
            crt_user_id=None,
            crt_ip_addr="127.0.0.1",
        )
    )
    db.commit()


def _create_user(db: Session, suffix: str) -> User:
    user = User(
        name=f"photo_logs_user_{suffix}",
        email=f"photo_logs_user_{suffix}@example.invalid",
        public_ind="Y",
        cryptpw="x",
        crt_date=datetime(2024, 1, 1).date(),
        crt_time=datetime(2024, 1, 1).time(),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def seed_tlog(db: Session, trig_id: int, user_id: int) -> TLog:
    """Create a TLog without hardcoded ID."""
    tlog = TLog(
        trig_id=trig_id,
        user_id=user_id,
        date=datetime(2024, 1, 2).date(),
        time=datetime(2024, 1, 2).time(),
        osgb_eastings=1,
        osgb_northings=1,
        osgb_gridref="AA 00000 00000",
        fb_number="",
        condition="G",
        comment="",
        score=0,
        ip_addr="127.0.0.1",
        source="W",
    )
    db.add(tlog)
    db.commit()
    db.refresh(tlog)
    return tlog


def create_photo(db: Session, tlog_id: int) -> TPhoto:
    """Create a TPhoto without hardcoded ID."""
    import uuid

    unique_suffix = uuid.uuid4().hex[:8]

    photo = TPhoto(
        tlog_id=tlog_id,
        server_id=1,
        type="T",
        filename=f"000/P{unique_suffix}.jpg",
        filesize=100,
        height=100,
        width=100,
        icon_filename=f"000/I{unique_suffix}.jpg",
        icon_filesize=10,
        icon_height=10,
        icon_width=10,
        name="Test Photo",
        text_desc="A test",
        ip_addr="127.0.0.1",
        public_ind="Y",
        deleted_ind="N",
        source="W",
        crt_timestamp=datetime.now(UTC),
    )
    db.add(photo)
    db.commit()
    db.refresh(photo)
    return photo


def test_trig_logs_include_photos(client: TestClient, db: Session):
    import uuid

    trig_id = 3_000_000 + int(uuid.uuid4().hex[:6], 16) % 100_000
    _ensure_trig(db, trig_id=trig_id)
    user = _create_user(db, suffix=str(trig_id))
    tlog = seed_tlog(db, trig_id=trig_id, user_id=int(user.id))
    photo1 = create_photo(db, tlog_id=int(tlog.id))
    photo2 = create_photo(db, tlog_id=int(tlog.id))

    resp = client.get(f"{settings.API_V1_STR}/trigs/{trig_id}/logs?include=photos")
    assert resp.status_code == 200
    body = resp.json()
    assert "items" in body and isinstance(body["items"], list)
    assert len(body["items"]) >= 1
    found = None
    for item in body["items"]:
        if item["id"] == tlog.id:
            found = item
            break
    assert found is not None
    assert "photos" in found and isinstance(found["photos"], list)
    ids = {p["id"] for p in found["photos"]}
    # Check for our specific dynamic photo IDs
    assert photo1.id in ids
    assert photo2.id in ids


def test_trig_logs_photos_use_aliased_keys(client: TestClient, db: Session):
    """Test that photos embedded in trig logs use 'caption'/'license' keys."""
    import uuid

    trig_id = 3_200_000 + int(uuid.uuid4().hex[:6], 16) % 100_000
    _ensure_trig(db, trig_id=trig_id)
    user = _create_user(db, suffix=str(trig_id))
    tlog = seed_tlog(db, trig_id=trig_id, user_id=int(user.id))
    photo = create_photo(db, tlog_id=int(tlog.id))

    resp = client.get(f"{settings.API_V1_STR}/trigs/{trig_id}/logs?include=photos")
    assert resp.status_code == 200
    body = resp.json()

    found = None
    for item in body["items"]:
        if item["id"] == tlog.id:
            found = item
            break
    assert found is not None
    assert len(found["photos"]) >= 1

    photo_item = next(p for p in found["photos"] if p["id"] == photo.id)
    assert "caption" in photo_item, "Expected 'caption' key in embedded photo"
    assert "license" in photo_item, "Expected 'license' key in embedded photo"
    assert "name" not in photo_item, "'name' should be aliased to 'caption'"
    assert "public_ind" not in photo_item, "'public_ind' should be aliased to 'license'"


def test_trig_logs_unknown_include(client: TestClient, db: Session):
    import uuid

    trig_id = 3_100_000 + int(uuid.uuid4().hex[:6], 16) % 100_000
    _ensure_trig(db, trig_id=trig_id)
    user = _create_user(db, suffix=str(trig_id))
    seed_tlog(db, trig_id=trig_id, user_id=int(user.id))

    resp = client.get(f"{settings.API_V1_STR}/trigs/{trig_id}/logs?include=bogus")
    assert resp.status_code == 400
