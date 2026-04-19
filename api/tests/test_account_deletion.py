"""
Integration tests for account deletion and anonymisation endpoints.
"""

import uuid
from datetime import date, datetime
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from api.models.tphoto import TPhoto
from api.models.user import TLog, User


def _make_mapped_user(db: Session, make_user):
    suffix = uuid.uuid4().hex[:8]
    user = make_user(
        name=f"acctdel_{suffix}",
        email=f"{suffix}@example.com",
        auth0_user_id=None,
    )
    user.auth0_user_id = f"auth0|{user.id}"
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _add_log(db: Session, user: User, trig) -> TLog:
    log = TLog(
        trig_id=trig.id,
        user_id=user.id,
        comment="Keep me",
        condition="G",
        date=date.today(),
        time=datetime.now().time(),
        osgb_eastings=1,
        osgb_northings=1,
        osgb_gridref="AA 00000 00000",
        fb_number="",
        score=0,
        ip_addr="192.168.1.1",
        source="W",
        status="P",
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return log


def _add_photo(db: Session, log: TLog) -> TPhoto:
    photo = TPhoto(
        tlog_id=log.id,
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
        text_desc="Test",
        ip_addr="127.0.0.1",
        public_ind="Y",
        deleted_ind="N",
        source="W",
        crt_timestamp=datetime.now(),
    )
    db.add(photo)
    db.commit()
    db.refresh(photo)
    return photo


def test_me_summary_unauthenticated(client: TestClient):
    r = client.get("/v1/users/me/account-deletion/summary")
    assert r.status_code == 401


def test_me_summary_ok(client: TestClient, db: Session, make_user, test_trig):
    user = _make_mapped_user(db, make_user)
    _add_log(db, user, test_trig)
    r = client.get(
        "/v1/users/me/account-deletion/summary",
        headers={"Authorization": f"Bearer auth0_user_{user.id}"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["user_id"] == user.id
    assert body["username"] == user.name
    assert body["full_name"] == "Test User"
    assert body["log_count"] >= 1


@patch(
    "api.services.account_deletion_service.email_service.send_contact_email",
    return_value=True,
)
@patch(
    "api.services.account_deletion_service.auth0_service.delete_user",
    return_value=True,
)
@patch("api.services.account_deletion_service.AvatarService.delete", return_value=True)
def test_me_execute_anonymise_keep_photos(
    _mock_avatar,
    _mock_auth0,
    _mock_email,
    client: TestClient,
    db: Session,
    make_user,
    test_trig,
):
    user = _make_mapped_user(db, make_user)
    log = _add_log(db, user, test_trig)

    r = client.post(
        "/v1/users/me/account-deletion",
        headers={"Authorization": f"Bearer auth0_user_{user.id}"},
        json={"mode": "anonymise_keep_photos", "feedback": "Moving abroad"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["user_row_deleted"] is False
    assert data["new_username"].startswith("Deleted-")

    db.expire_all()
    u = db.query(User).filter(User.id == user.id).one()
    assert u.name.startswith("Deleted-")
    assert (u.email or "") == ""
    assert u.auth0_user_id is None
    log2 = db.query(TLog).filter(TLog.id == log.id).one()
    assert log2.ip_addr is None


@patch(
    "api.services.account_deletion_service.email_service.send_contact_email",
    return_value=True,
)
@patch(
    "api.services.account_deletion_service.auth0_service.delete_user",
    return_value=True,
)
@patch(
    "api.services.account_deletion_service.S3Service.delete_photo_and_thumbnail",
    return_value=True,
)
@patch("api.services.account_deletion_service.AvatarService.delete", return_value=True)
def test_me_execute_anonymise_delete_photos(
    _mock_avatar,
    _mock_s3,
    _mock_auth0,
    _mock_email,
    client: TestClient,
    db: Session,
    make_user,
    test_trig,
):
    user = _make_mapped_user(db, make_user)
    log = _add_log(db, user, test_trig)
    _add_photo(db, log)

    r = client.post(
        "/v1/users/me/account-deletion",
        headers={"Authorization": f"Bearer auth0_user_{user.id}"},
        json={"mode": "anonymise_delete_photos"},
    )
    assert r.status_code == 200
    assert r.json()["photos_deleted"] >= 1
    assert db.query(TPhoto).filter(TPhoto.tlog_id == log.id).count() == 0


@patch(
    "api.services.account_deletion_service.email_service.send_contact_email",
    return_value=True,
)
@patch(
    "api.services.account_deletion_service.auth0_service.delete_user",
    return_value=True,
)
@patch(
    "api.services.account_deletion_service.S3Service.delete_photo_and_thumbnail",
    return_value=True,
)
def test_me_execute_purge_all(
    _mock_s3,
    _mock_auth0,
    _mock_email,
    client: TestClient,
    db: Session,
    make_user,
    test_trig,
):
    user = _make_mapped_user(db, make_user)
    log = _add_log(db, user, test_trig)
    _add_photo(db, log)
    user_pk = int(user.id)
    log_pk = int(log.id)

    r = client.post(
        "/v1/users/me/account-deletion",
        headers={"Authorization": f"Bearer auth0_user_{user_pk}"},
        json={"mode": "purge_all"},
    )
    assert r.status_code == 200
    assert r.json()["user_row_deleted"] is True
    assert db.query(User).filter(User.id == user_pk).first() is None
    assert db.query(TLog).filter(TLog.id == log_pk).first() is None


@patch(
    "api.services.account_deletion_service.auth0_service.delete_user",
    return_value=False,
)
def test_me_execute_anonymise_auth0_failure_returns_502(
    _mock_auth0,
    client: TestClient,
    db: Session,
    make_user,
    test_trig,
):
    user = _make_mapped_user(db, make_user)
    _add_log(db, user, test_trig)

    r = client.post(
        "/v1/users/me/account-deletion",
        headers={"Authorization": f"Bearer auth0_user_{user.id}"},
        json={"mode": "anonymise_keep_photos"},
    )
    assert r.status_code == 502
    u = db.query(User).filter(User.id == user.id).one()
    assert not str(u.name).startswith("Deleted-")


def test_admin_summary_not_found(client: TestClient, make_user):
    # Admin token resolves to the first user row; ensure one exists.
    make_user()
    r = client.get(
        "/v1/admin/users/999999999/account-deletion/summary",
        headers={"Authorization": "Bearer auth0_admin"},
    )
    assert r.status_code == 404


def test_admin_summary_ok(client: TestClient, db: Session, make_user, test_trig):
    user = _make_mapped_user(db, make_user)
    _add_log(db, user, test_trig)
    r = client.get(
        f"/v1/admin/users/{user.id}/account-deletion/summary",
        headers={"Authorization": "Bearer auth0_admin"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["user_id"] == user.id
    assert body["full_name"] == "Test User"


@patch(
    "api.services.account_deletion_service.email_service.send_contact_email",
    return_value=True,
)
@patch(
    "api.services.account_deletion_service.auth0_service.delete_user",
    return_value=True,
)
@patch("api.services.account_deletion_service.AvatarService.delete", return_value=True)
def test_admin_execute_purge_target(
    _mock_avatar,
    _mock_auth0,
    _mock_email,
    client: TestClient,
    db: Session,
    make_user,
    test_trig,
):
    victim = _make_mapped_user(db, make_user)
    log = _add_log(db, victim, test_trig)
    victim_id = int(victim.id)
    log_pk = int(log.id)

    r = client.post(
        f"/v1/admin/users/{victim_id}/account-deletion",
        headers={"Authorization": "Bearer auth0_admin"},
        json={"mode": "purge_all", "feedback": "Spam account"},
    )
    assert r.status_code == 200
    assert db.query(User).filter(User.id == victim_id).first() is None
    assert db.query(TLog).filter(TLog.id == log_pk).first() is None


@patch("api.services.archive_service.generate_archive_zip", return_value=b"ZIP")
@patch(
    "api.services.email_service.email_service.send_deletion_backup_email",
    return_value=True,
)
def test_me_deletion_email_backup(
    _mock_send,
    _mock_zip,
    client: TestClient,
    db: Session,
    make_user,
    test_trig,
):
    user = _make_mapped_user(db, make_user)
    _add_log(db, user, test_trig)

    r = client.post(
        "/v1/users/me/account-deletion/email-backup",
        headers={"Authorization": f"Bearer auth0_user_{user.id}"},
    )
    assert r.status_code == 200
