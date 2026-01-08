"""
Tests for admin logs needing attention endpoints.
"""

import uuid
from datetime import date, time

from api.crud.user import create_user
from api.models.trig import Trig
from api.models.user import TLog, User


def _ensure_admin_user(db) -> None:
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


def _create_trig(db) -> Trig:
    # Use an explicit, high trig ID to avoid colliding with other tests that assume
    # small IDs (e.g. trig_id=99 in trigstats tests). Tests share a DB across runs.
    trig_id = 1_000_000 + (int(uuid.uuid4().hex[:8], 16) % 1_000_000_000)
    waypoint_suffix = trig_id % 1_000_000  # fit "TP" + 6 digits (8 chars total)
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
        wgs_lat=0.0,
        wgs_long=0.0,
        wgs_height=0,
        osgb_eastings=0,
        osgb_northings=0,
        osgb_gridref="AA 00000 00000",
        osgb_height=0,
        postcode="AA0 0AA",
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


def test_admin_logs_needs_attention_returns_duplicate_groups(client, db, test_user):
    _ensure_admin_user(db)
    trig = _create_trig(db)

    log_date = date(2025, 12, 13)
    log1: TLog | None = None
    log2: TLog | None = None
    try:
        log1 = TLog(
            trig_id=trig.id,
            user_id=test_user.id,
            comment="First duplicate",
            condition="G",
            date=log_date,
            time=time(9, 0, 0),
            osgb_eastings=1,
            osgb_northings=1,
            osgb_gridref="AA 00000 00000",
            fb_number="",
            score=0,
            ip_addr="127.0.0.1",
            source="W",
        )
        log2 = TLog(
            trig_id=trig.id,
            user_id=test_user.id,
            comment="Second duplicate",
            condition="D",
            date=log_date,
            time=time(10, 0, 0),
            osgb_eastings=1,
            osgb_northings=1,
            osgb_gridref="AA 00000 00000",
            fb_number="",
            score=0,
            ip_addr="127.0.0.1",
            source="W",
        )
        db.add_all([log1, log2])
        db.commit()

        resp = client.get(
            "/v1/admin/logs/needs-attention?skip=0&limit=50",
            headers={"Authorization": "Bearer auth0_admin"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data

        duplicate_items = [i for i in data["items"] if i["issue_type"] == "duplicate"]
        assert duplicate_items, "Expected at least one duplicate group item"

        group = duplicate_items[0]
        assert group["trig_id"] == trig.id
        assert group["user_id"] == test_user.id
        assert group["date"] == str(log_date)
        assert group["duplicate_count"] >= 2
        assert isinstance(group["logs"], list)
        assert len(group["logs"]) >= 2
        assert all("id" in entry for entry in group["logs"])
    finally:
        if log1 is not None and log1.id is not None:
            db.query(TLog).filter(TLog.id == log1.id).delete()
        if log2 is not None and log2.id is not None:
            db.query(TLog).filter(TLog.id == log2.id).delete()
        db.query(Trig).filter(Trig.id == trig.id).delete()
        db.commit()


def test_admin_delete_duplicate_log_prevents_deleting_last_remaining(
    client, db, test_user
):
    _ensure_admin_user(db)
    trig = _create_trig(db)

    log_date = date(2025, 12, 13)
    log1: TLog | None = None
    log2: TLog | None = None
    try:
        log1 = TLog(
            trig_id=trig.id,
            user_id=test_user.id,
            comment="Duplicate one",
            condition="G",
            date=log_date,
            time=time(9, 0, 0),
            osgb_eastings=1,
            osgb_northings=1,
            osgb_gridref="AA 00000 00000",
            fb_number="",
            score=0,
            ip_addr="127.0.0.1",
            source="W",
        )
        log2 = TLog(
            trig_id=trig.id,
            user_id=test_user.id,
            comment="Duplicate two",
            condition="G",
            date=log_date,
            time=time(9, 30, 0),
            osgb_eastings=1,
            osgb_northings=1,
            osgb_gridref="AA 00000 00000",
            fb_number="",
            score=0,
            ip_addr="127.0.0.1",
            source="W",
        )
        db.add_all([log1, log2])
        db.commit()
        db.refresh(log1)
        db.refresh(log2)

        # Delete one of the duplicates: should succeed
        resp1 = client.delete(
            f"/v1/admin/logs/{log1.id}/duplicate",
            headers={"Authorization": "Bearer auth0_admin"},
        )
        assert resp1.status_code == 200

        # Attempt to delete the last remaining one: should be blocked
        resp2 = client.delete(
            f"/v1/admin/logs/{log2.id}/duplicate",
            headers={"Authorization": "Bearer auth0_admin"},
        )
        assert resp2.status_code == 404
    finally:
        if log1 is not None and log1.id is not None:
            db.query(TLog).filter(TLog.id == log1.id).delete()
        if log2 is not None and log2.id is not None:
            db.query(TLog).filter(TLog.id == log2.id).delete()
        db.query(Trig).filter(Trig.id == trig.id).delete()
        db.commit()
