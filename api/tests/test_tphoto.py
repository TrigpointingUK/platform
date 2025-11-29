"""
Tests for tphoto endpoints.
"""

from datetime import datetime

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from api.core.config import settings
from api.models.tphoto import TPhoto
from api.models.user import TLog, User


def seed_user_and_tlog(db: Session) -> tuple[User, TLog]:
    import uuid

    unique_name = f"photouser_{uuid.uuid4().hex[:6]}"
    user = User(
        name=unique_name,
        firstname="Photo",
        surname="User",
        email=f"{unique_name}@example.com",
        cryptpw="test",
        about="",
        email_valid="Y",
        public_ind="Y",
        auth0_user_id=f"auth0|{uuid.uuid4().hex[:8]}",
    )
    tlog = TLog(
        trig_id=1,
        user_id=None,  # Will set after user is saved
        date=datetime(2023, 1, 1).date(),
        time=datetime(2023, 1, 1).time(),
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
    db.add(user)
    db.commit()
    db.refresh(user)
    user.auth0_user_id = f"auth0|{user.id}"  # type: ignore
    db.commit()
    db.refresh(user)
    tlog.user_id = user.id
    db.add(tlog)
    db.commit()
    db.refresh(tlog)
    return user, tlog


def create_sample_photo(db: Session, tlog_id: int) -> TPhoto:
    photo = TPhoto(
        tlog_id=tlog_id,
        server_id=1,
        type="T",
        filename="000/P00001.jpg",
        filesize=100,
        height=100,
        width=100,
        icon_filename="000/I00001.jpg",
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


def test_get_photo(client: TestClient, db: Session):
    _, tlog = seed_user_and_tlog(db)
    photo = create_sample_photo(db, tlog_id=int(tlog.id))

    resp = client.get(f"{settings.API_V1_STR}/photos/{photo.id}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["id"] == photo.id
    assert body["caption"] == "Test Photo"


def test_update_photo(client: TestClient, db: Session):
    user, tlog = seed_user_and_tlog(db)
    photo = create_sample_photo(db, tlog_id=int(tlog.id))

    headers = {"Authorization": f"Bearer auth0_user_{user.id}"}
    resp = client.patch(
        f"{settings.API_V1_STR}/photos/{photo.id}",
        json={"caption": "New Name", "license": "N", "type": "F"},
        headers=headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["caption"] == "New Name"
    assert body["license"] == "N"
    assert body["type"] == "F"


def test_delete_photo_soft(client: TestClient, db: Session):
    user, tlog = seed_user_and_tlog(db)
    photo = create_sample_photo(db, tlog_id=int(tlog.id))

    headers = {"Authorization": f"Bearer auth0_user_{user.id}"}
    resp = client.delete(f"{settings.API_V1_STR}/photos/{photo.id}", headers=headers)
    assert resp.status_code == 204

    # subsequent get should 404 due to soft delete
    resp2 = client.get(f"{settings.API_V1_STR}/photos/{photo.id}")
    assert resp2.status_code == 404


# removed user photo count endpoint tests; evaluation tests retained upstream
