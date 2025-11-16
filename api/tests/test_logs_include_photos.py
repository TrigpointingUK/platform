"""
Tests for include=photos on logs endpoints.
"""

from datetime import datetime

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from api.core.config import settings
from api.models.tphoto import TPhoto
from api.models.user import TLog, User


def seed_user_and_tlog(db: Session) -> tuple[User, TLog]:
    import uuid

    unique_suffix = uuid.uuid4().hex[:8]

    user = User(
        name=f"logphotouser_{unique_suffix}",
        firstname="Log",
        surname="PhotoUser",
        email=f"lp_{unique_suffix}@example.com",
        cryptpw="test",  # Required field
        about="",  # Required field
        email_valid="Y",  # Required field
        public_ind="Y",  # Required field
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    tlog = TLog(
        trig_id=1,
        user_id=user.id,  # Use dynamic user ID
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
    return user, tlog


def create_sample_photo(db: Session, tlog_id: int) -> TPhoto:
    """Create a sample photo (without hardcoded ID)."""
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


def test_list_logs_include_photos(client: TestClient, db: Session):
    user, tlog = seed_user_and_tlog(db)
    photo1 = create_sample_photo(db, tlog_id=int(tlog.id))
    photo2 = create_sample_photo(db, tlog_id=int(tlog.id))

    resp = client.get(
        f"{settings.API_V1_STR}/logs?user_id={user.id}&include=photos&limit=10&skip=0"
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "items" in body
    assert len(body["items"]) >= 1
    first = body["items"][0]
    assert "photos" in first
    assert isinstance(first["photos"], list)
    assert len(first["photos"]) >= 2
    # Check for our specific photo IDs (use dynamic IDs)
    photo_ids = {p["id"] for p in first["photos"]}
    assert photo1.id in photo_ids
    assert photo2.id in photo_ids


def test_get_log_include_photos(client: TestClient, db: Session):
    _, tlog = seed_user_and_tlog(db)
    photo1 = create_sample_photo(db, tlog_id=int(tlog.id))
    photo2 = create_sample_photo(db, tlog_id=int(tlog.id))

    resp = client.get(f"{settings.API_V1_STR}/logs/{tlog.id}?include=photos")
    assert resp.status_code == 200
    body = resp.json()
    assert body["id"] == tlog.id
    assert "photos" in body
    assert isinstance(body["photos"], list)
    # Check for our specific photo IDs (use dynamic IDs)
    photo_ids = {p["id"] for p in body["photos"]}
    assert photo1.id in photo_ids
    assert photo2.id in photo_ids


def test_list_logs_unknown_include(client: TestClient, db: Session):
    seed_user_and_tlog(db)
    resp = client.get(f"{settings.API_V1_STR}/logs?include=bogus")
    assert resp.status_code == 400


def test_get_log_unknown_include(client: TestClient, db: Session):
    _, tlog = seed_user_and_tlog(db)
    resp = client.get(f"{settings.API_V1_STR}/logs/{tlog.id}?include=bogus")
    assert resp.status_code == 400
