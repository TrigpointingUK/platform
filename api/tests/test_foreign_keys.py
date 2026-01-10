"""
Tests for database-enforced foreign key behaviour.

These tests rely on SQLAlchemy Base.metadata.create_all() creating FK constraints
from model definitions (tests do not run Alembic migrations).
"""

from datetime import date, time
from decimal import Decimal

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from api.models.attr import Attr, AttrSource
from api.models.tphoto import TPhoto
from api.models.trig import Trig
from api.models.trigstats import TrigStats
from api.models.user import TLog, TPhotoVote, User


def _create_user(db: Session) -> User:
    import uuid

    suffix = uuid.uuid4().hex[:8]
    u = User(
        name=f"fk_test_user_{suffix}",
        email=f"fk_test_user_{suffix}@example.invalid",
        cryptpw="",
        email_valid="Y",
        public_ind="Y",
        crt_date=date(2023, 1, 1),
        crt_time=time(0, 0, 0),
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


def _create_trig(db: Session) -> Trig:
    import uuid

    suffix = uuid.uuid4().hex[:6]
    t = Trig(
        waypoint=f"TP{suffix}"[:8],
        name="FK Test Trig",
        status_id=10,
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
    db.add(t)
    db.commit()
    db.refresh(t)
    return t


def test_on_delete_set_null_tlog_trig_id(db: Session):
    u = _create_user(db)
    trig = _create_trig(db)

    log = TLog(trig_id=trig.id, user_id=u.id)
    db.add(log)
    db.commit()
    db.refresh(log)

    db.delete(trig)
    db.commit()
    db.refresh(log)

    assert log.trig_id is None


def test_on_delete_set_null_tlog_user_id(db: Session):
    u = _create_user(db)
    trig = _create_trig(db)

    log = TLog(trig_id=trig.id, user_id=u.id)
    db.add(log)
    db.commit()
    db.refresh(log)

    db.delete(u)
    db.commit()
    db.refresh(log)

    assert log.user_id is None


def test_on_delete_set_null_tphoto_and_vote(db: Session):
    u = _create_user(db)
    trig = _create_trig(db)

    log = TLog(trig_id=trig.id, user_id=u.id)
    db.add(log)
    db.commit()
    db.refresh(log)

    photo = TPhoto(
        tlog_id=log.id,
        server_id=1,
        type="T",
        filename="000/P_test.jpg",
        filesize=1,
        height=1,
        width=1,
        icon_filename="000/I_test.jpg",
        icon_filesize=1,
        icon_height=1,
        icon_width=1,
        name="FK Photo",
        text_desc="",
        ip_addr="127.0.0.1",
        public_ind="Y",
        deleted_ind="N",
        source="W",
    )
    db.add(photo)
    db.commit()
    db.refresh(photo)

    vote = TPhotoVote(tphoto_id=photo.id, user_id=u.id, score=1)
    db.add(vote)
    db.commit()
    db.refresh(vote)

    # Delete log -> tphoto.tlog_id set NULL (but photo remains)
    db.delete(log)
    db.commit()
    db.refresh(photo)
    assert photo.tlog_id is None

    # Delete photo -> vote.tphoto_id set NULL (vote remains)
    db.delete(photo)
    db.commit()
    db.refresh(vote)
    assert vote.tphoto_id is None

    # Delete user -> vote.user_id set NULL
    db.delete(u)
    db.commit()
    db.refresh(vote)
    assert vote.user_id is None


def test_on_delete_restrict_attrsource(db: Session):
    src = AttrSource(name="FK Source", descr="", url="", sort_order=1)
    db.add(src)
    db.commit()
    db.refresh(src)

    a = Attr(
        attrsource_id=src.id,
        name="a",
        description="d",
        mandatory=0,
        multivalued=0,
        grouped=0,
        sort_order=1,
    )
    db.add(a)
    db.commit()

    with pytest.raises(IntegrityError):
        db.delete(src)
        db.commit()


def test_on_delete_cascade_trigstats(db: Session):
    trig = _create_trig(db)
    stats = TrigStats(
        id=trig.id,
        logged_first=None,
        logged_last=None,
        logged_count=0,
        found_last=None,
        found_count=0,
        photo_count=0,
        score_mean=Decimal("0.00"),
        score_baysian=Decimal("0.00"),
    )
    db.add(stats)
    db.commit()

    db.delete(trig)
    db.commit()

    assert db.query(TrigStats).filter(TrigStats.id == trig.id).first() is None
