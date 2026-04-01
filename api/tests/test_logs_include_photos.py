"""
Tests for include=photos on logs endpoints.
"""

from datetime import UTC, datetime

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from api.core.config import settings
from api.models.tphoto import TPhoto
from api.models.user import TLog


def _seed_tlog(db: Session, trig_id: int, user_id: int) -> TLog:
    """Create a tlog entry for the given trig and user."""
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


def _create_sample_photo(db: Session, tlog_id: int) -> TPhoto:
    """Create a sample photo attached to the given tlog."""
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


def test_list_logs_include_photos(
    client: TestClient, db: Session, test_trig, test_user
):
    tlog = _seed_tlog(db, trig_id=int(test_trig.id), user_id=int(test_user.id))
    photo1 = _create_sample_photo(db, tlog_id=int(tlog.id))
    photo2 = _create_sample_photo(db, tlog_id=int(tlog.id))

    resp = client.get(
        f"{settings.API_V1_STR}/logs?user_id={test_user.id}&include=photos&limit=10&skip=0"
    )
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
    body = resp.json()
    assert "items" in body, f"Response missing 'items': {body}"
    assert (
        len(body["items"]) >= 1
    ), f"Expected at least 1 item, got {len(body['items'])}"
    our_log = next((item for item in body["items"] if item["id"] == tlog.id), None)
    assert (
        our_log is not None
    ), f"Log {tlog.id} not found in {[i['id'] for i in body['items']]}"
    assert "photos" in our_log, f"Response missing 'photos': {our_log.keys()}"
    assert isinstance(our_log["photos"], list)
    assert (
        len(our_log["photos"]) >= 2
    ), f"Expected 2+ photos, got {len(our_log['photos'])}: {our_log['photos']}"
    assert "trig_lat" in our_log
    assert "trig_lon" in our_log
    photo_ids = {p["id"] for p in our_log["photos"]}
    assert photo1.id in photo_ids, f"Photo {photo1.id} not in {photo_ids}"
    assert photo2.id in photo_ids, f"Photo {photo2.id} not in {photo_ids}"


def test_get_log_include_photos(client: TestClient, db: Session, test_trig, test_user):
    tlog = _seed_tlog(db, trig_id=int(test_trig.id), user_id=int(test_user.id))
    photo1 = _create_sample_photo(db, tlog_id=int(tlog.id))
    photo2 = _create_sample_photo(db, tlog_id=int(tlog.id))

    resp = client.get(f"{settings.API_V1_STR}/logs/{tlog.id}?include=photos")
    assert resp.status_code == 200
    body = resp.json()
    assert body["id"] == tlog.id
    assert "photos" in body
    assert isinstance(body["photos"], list)
    photo_ids = {p["id"] for p in body["photos"]}
    assert photo1.id in photo_ids, f"Photo {photo1.id} not in {photo_ids}"
    assert photo2.id in photo_ids, f"Photo {photo2.id} not in {photo_ids}"


def test_list_logs_unknown_include(
    client: TestClient, db: Session, test_trig, test_user
):
    _seed_tlog(db, trig_id=int(test_trig.id), user_id=int(test_user.id))
    resp = client.get(f"{settings.API_V1_STR}/logs?include=bogus")
    assert resp.status_code == 400


def test_get_log_unknown_include(client: TestClient, db: Session, test_trig, test_user):
    tlog = _seed_tlog(db, trig_id=int(test_trig.id), user_id=int(test_user.id))
    resp = client.get(f"{settings.API_V1_STR}/logs/{tlog.id}?include=bogus")
    assert resp.status_code == 400
