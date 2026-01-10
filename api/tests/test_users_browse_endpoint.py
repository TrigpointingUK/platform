"""
Tests for the /v1/users/browse endpoint providing cursor-based listings.
"""

import uuid
from datetime import date, time
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from api.core.config import settings
from api.models.tphoto import TPhoto
from api.models.trig import Trig
from api.models.user import TLog, User
from api.services.user_stats import refresh_user_activity_summary


def _create_user(db: Session, name: str, joined: date) -> User:
    user = User(
        name=name,
        email=f"{name}@example.com",
        public_ind="Y",
        cryptpw="x",
        crt_date=joined,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _ensure_trig(db: Session, trig_id: int) -> None:
    if db.query(Trig).filter(Trig.id == trig_id).first() is not None:
        return

    db.add(
        Trig(
            id=trig_id,
            waypoint=f"TP{trig_id:06d}"[:8],
            name=f"Users Browse Trig {trig_id}",
            status_id=1,
            user_added=0,
            current_use="Passive station",
            historic_use="Primary",
            physical_type="Pillar",
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
            county="London",
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


def _add_log(
    db: Session,
    user: User,
    trig_id: int,
    *,
    log_date: date = date(2024, 1, 1),
) -> TLog:
    _ensure_trig(db, trig_id)
    log = TLog(
        trig_id=trig_id,
        user_id=user.id,
        date=log_date,
        time=time(12, 0),
        condition="G",
        osgb_eastings=0,
        osgb_northings=0,
        osgb_gridref="AA 00000 00000",
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return log


def _add_photo(db: Session, log: TLog, name: str) -> None:
    photo = TPhoto(
        tlog_id=log.id,
        server_id=1,
        type="T",
        filename=f"{name}.jpg",
        filesize=1,
        height=10,
        width=10,
        icon_filename=f"{name}_thumb.jpg",
        icon_filesize=1,
        icon_height=5,
        icon_width=5,
        name=name,
        text_desc="",
        ip_addr="127.0.0.1",
        public_ind="Y",
        deleted_ind="N",
        source="W",
    )
    db.add(photo)
    db.commit()


def test_users_browse_orders_by_trigs(client: TestClient, db: Session) -> None:
    prefix = f"prolific_{uuid.uuid4().hex[:6]}"
    prolific = _create_user(db, f"{prefix}_prolific", date(2020, 1, 1))
    steady = _create_user(db, f"{prefix}_steady", date(2021, 1, 1))
    for trig in range(1, 5):
        _add_log(db, prolific, trig)
    _add_log(db, steady, 10)

    refresh_user_activity_summary(db)

    response = client.get(f"{settings.API_V1_STR}/users/browse?limit=5&q={prefix}")
    assert response.status_code == 200, response.json()
    payload = response.json()
    assert [item["id"] for item in payload["items"]] == [
        prolific.id,
        steady.id,
    ]
    assert payload["applied_filters"]["sort"] == "trigs"
    assert payload["applied_filters"]["direction"] == "desc"
    assert payload["total"] == 2


def test_users_browse_filters_by_query(client: TestClient, db: Session) -> None:
    prefix = f"filter_{uuid.uuid4().hex[:6]}"
    target = _create_user(db, f"{prefix}_AliceWonder", date(2019, 6, 1))
    _add_log(db, target, 1)
    _create_user(db, f"{prefix}_BobBuilder", date(2018, 6, 1))

    refresh_user_activity_summary(db)

    response = client.get(
        f"{settings.API_V1_STR}/users/browse?q={f'{prefix}_alice'.lower()}"
    )
    assert response.status_code == 200, response.json()
    payload = response.json()
    assert len(payload["items"]) == 1
    assert payload["items"][0]["name"] == f"{prefix}_AliceWonder"
    assert payload["total"] == 1


def test_users_browse_sorts_by_photos(client: TestClient, db: Session) -> None:
    prefix = f"photos_{uuid.uuid4().hex[:6]}"
    shutterbug = _create_user(db, f"{prefix}_shutterbug", date(2022, 4, 1))
    casual = _create_user(db, f"{prefix}_casual", date(2024, 4, 1))

    shutter_log = _add_log(db, shutterbug, 1)
    for idx in range(2):
        _add_photo(db, shutter_log, f"shot-{idx}")

    casual_log = _add_log(db, casual, 2)
    _add_photo(db, casual_log, "single")

    refresh_user_activity_summary(db)

    response = client.get(
        f"{settings.API_V1_STR}/users/browse?sort=photos&direction=asc&q={prefix}"
    )
    assert response.status_code == 200, response.json()
    payload = response.json()
    assert [item["name"] for item in payload["items"]] == [
        f"{prefix}_casual",
        f"{prefix}_shutterbug",
    ]
    assert payload["items"][0]["stats"]["total_photos"] == 1
    assert payload["items"][1]["stats"]["total_photos"] == 2


def test_users_browse_sorts_by_logs(client: TestClient, db: Session) -> None:
    prefix = f"logs_{uuid.uuid4().hex[:6]}"
    prolific = _create_user(db, f"{prefix}_prolific", date(2020, 5, 1))
    steady = _create_user(db, f"{prefix}_steady", date(2020, 5, 1))
    for trig in range(1, 5):
        _add_log(db, prolific, trig)
    _add_log(db, steady, 99)

    refresh_user_activity_summary(db)

    response = client.get(
        f"{settings.API_V1_STR}/users/browse?sort=logs&direction=desc&q={prefix}"
    )
    assert response.status_code == 200, response.json()
    payload = response.json()
    assert [item["id"] for item in payload["items"]] == [
        prolific.id,
        steady.id,
    ]
    assert payload["items"][0]["stats"]["total_logs"] == 4
    assert payload["items"][1]["stats"]["total_logs"] == 1


def test_users_browse_paginates_with_cursor(client: TestClient, db: Session) -> None:
    prefix = f"cursor_{uuid.uuid4().hex[:6]}"
    first = _create_user(db, f"{prefix}_first", date(2017, 1, 1))
    second = _create_user(db, f"{prefix}_second", date(2016, 1, 1))
    _add_log(db, first, 1)
    _add_log(db, second, 2)

    refresh_user_activity_summary(db)

    first_page = client.get(
        f"{settings.API_V1_STR}/users/browse?limit=1&sort=joined&q={prefix}"
    )
    assert first_page.status_code == 200, first_page.json()
    first_payload = first_page.json()
    assert first_payload["next_cursor"]
    assert len(first_payload["items"]) == 1

    next_cursor = first_payload["next_cursor"]
    second_page = client.get(
        f"{settings.API_V1_STR}/users/browse?limit=1&sort=joined&cursor={next_cursor}&q={prefix}"
    )
    assert second_page.status_code == 200, second_page.json()
    second_payload = second_page.json()
    assert len(second_payload["items"]) == 1
    assert second_payload["items"][0]["id"] != first_payload["items"][0]["id"]


def test_users_browse_excludes_zero_activity_users(
    client: TestClient, db: Session
) -> None:
    prefix = f"inactive_{uuid.uuid4().hex[:6]}"
    inactive = _create_user(db, f"{prefix}_idle", date(2020, 5, 1))
    active = _create_user(db, f"{prefix}_active", date(2020, 5, 1))
    _add_log(db, active, 42)

    refresh_user_activity_summary(db)

    response = client.get(f"{settings.API_V1_STR}/users/browse?q={prefix}")
    assert response.status_code == 200, response.json()
    payload = response.json()
    ids = [item["id"] for item in payload["items"]]
    assert ids == [active.id]
    assert inactive.id not in ids
    assert payload["total"] == 1
