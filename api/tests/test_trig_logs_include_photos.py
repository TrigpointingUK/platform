"""
Tests for include=photos on /v1/trigs/{trig_id}/logs endpoint.
"""

from datetime import datetime

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from api.core.config import settings
from api.models.tphoto import TPhoto
from api.models.user import TLog


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
        crt_timestamp=datetime.utcnow(),
    )
    db.add(photo)
    db.commit()
    db.refresh(photo)
    return photo


def test_trig_logs_include_photos(client: TestClient, db: Session):
    trig_id = 555
    tlog = seed_tlog(db, trig_id=trig_id, user_id=1010)
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


def test_trig_logs_unknown_include(client: TestClient, db: Session):
    trig_id = 556
    seed_tlog(db, trig_id=trig_id, user_id=1011)

    resp = client.get(f"{settings.API_V1_STR}/trigs/{trig_id}/logs?include=bogus")
    assert resp.status_code == 400
