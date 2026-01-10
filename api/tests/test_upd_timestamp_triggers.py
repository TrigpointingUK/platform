"""
Tests for database-managed upd_timestamp behaviour.

These rely on the test DB bootstrap installing the same triggers/defaults as the
Alembic migration (see api/tests/conftest.py).
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, time
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from api.core.config import settings
from api.crud.user import create_user
from api.models.trig import Trig
from api.models.user import TLog, User


def _ensure_admin_user(db: Session) -> None:
    """Ensure the mocked auth0_admin token maps to a real DB user."""
    existing = db.query(User).filter(User.auth0_user_id == "auth0|admin").first()
    if existing:
        return
    suffix = uuid.uuid4().hex[:8]
    create_user(
        db=db,
        username=f"admin_{suffix}",
        email=f"admin_{suffix}@example.com",
        auth0_user_id="auth0|admin",
    )


def _create_trig(db: Session) -> Trig:
    trig_id = 2_000_000 + (int(uuid.uuid4().hex[:8], 16) % 1_000_000_000)
    waypoint_suffix = trig_id % 1_000_000
    trig = Trig(
        id=trig_id,
        waypoint=f"TP{waypoint_suffix:06d}",
        name=f"Test trig {trig_id}",
        fb_number="FB1",
        stn_number="STN1",
        status_id=1,
        user_added=0,
        current_use="none",
        historic_use="none",
        physical_type="Pillar",
        condition="G",
        wgs_lat=Decimal("51.50000"),
        wgs_long=Decimal("-0.12500"),
        wgs_height=100,
        osgb_eastings=530000,
        osgb_northings=180000,
        osgb_gridref="TQ 30000 80000",
        osgb_height=95,
        postcode=None,
        county="Testshire",
        town="Testville",
        permission_ind="Y",
        needs_attention=0,
        attention_comment="",
        crt_date=date.today(),
        crt_time=time(0, 0, 0),
        crt_user_id=None,
        crt_ip_addr="127.0.0.1",
    )
    db.add(trig)
    db.commit()
    db.refresh(trig)
    return trig


def test_tlog_upd_timestamp_updates_on_update(client: TestClient, db: Session):
    suffix = uuid.uuid4().hex[:8]
    user = create_user(
        db=db,
        username=f"user_{suffix}",
        email=f"user_{suffix}@example.com",
        auth0_user_id=f"auth0|{1_000_000 + int(suffix, 16) % 100_000}",
    )
    trig = _create_trig(db)

    log = TLog(
        trig_id=trig.id,
        user_id=user.id,
        date=date(2025, 1, 1),
        time=time(12, 0, 0),
        condition="G",
        comment="Initial",
        fb_number="",
        score=0,
        ip_addr="127.0.0.1",
        source="W",
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    before = log.upd_timestamp
    assert before is not None

    resp = client.patch(
        f"{settings.API_V1_STR}/logs/{int(log.id)}",
        json={"comment": "Updated"},
        headers={"Authorization": f"Bearer auth0_user_{int(user.id)}"},
    )
    assert resp.status_code == 200

    db.refresh(log)
    after = log.upd_timestamp
    assert after is not None
    assert after > before

    # Stored as naive UTC in the database (timestamp without time zone).
    assert abs((datetime.utcnow() - after).total_seconds()) < 30


def test_user_upd_timestamp_updates_on_me_patch(client: TestClient, db: Session):
    suffix = uuid.uuid4().hex[:8]
    user = create_user(
        db=db,
        username=f"me_{suffix}",
        email=f"me_{suffix}@example.com",
        auth0_user_id=f"auth0|{1_500_000 + int(suffix, 16) % 100_000}",
    )

    db.refresh(user)
    before = user.upd_timestamp
    assert before is not None

    resp = client.patch(
        f"{settings.API_V1_STR}/users/me",
        json={"firstname": "Updated"},
        headers={"Authorization": f"Bearer auth0_user_{int(user.id)}"},
    )
    assert resp.status_code == 200

    db.refresh(user)
    after = user.upd_timestamp
    assert after is not None
    assert after > before
    assert abs((datetime.utcnow() - after).total_seconds()) < 30


def test_trig_upd_timestamp_updates_on_admin_patch(client: TestClient, db: Session):
    _ensure_admin_user(db)
    trig = _create_trig(db)
    before = trig.upd_timestamp
    assert before is not None

    payload = {
        "name": trig.name,
        "fb_number": trig.fb_number,
        "stn_number": trig.stn_number,
        "stn_number_active": trig.stn_number_active or "",
        "stn_number_passive": trig.stn_number_passive or "",
        "stn_number_osgb36": trig.stn_number_osgb36 or "",
        "status_id": int(trig.status_id),
        "current_use": trig.current_use,
        "historic_use": trig.historic_use,
        "physical_type": trig.physical_type,
        "condition": trig.condition,
        "wgs_lat": str(trig.wgs_lat),
        "wgs_long": str(trig.wgs_long),
        "wgs_height": int(trig.wgs_height),
        "osgb_eastings": int(trig.osgb_eastings),
        "osgb_northings": int(trig.osgb_northings),
        "osgb_gridref": trig.osgb_gridref,
        "osgb_height": int(trig.osgb_height),
        "action": "revisit",
        "admin_comment": "Test update",
    }

    resp = client.patch(
        f"{settings.API_V1_STR}/admin/trigs/{int(trig.id)}",
        json=payload,
        headers={"Authorization": "Bearer auth0_admin"},
    )
    assert resp.status_code == 200

    db.refresh(trig)
    after = trig.upd_timestamp
    assert after is not None
    assert after > before
    assert abs((datetime.utcnow() - after).total_seconds()) < 30
