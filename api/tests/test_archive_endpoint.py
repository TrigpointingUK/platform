"""
Tests for the archive email endpoints (POST /me/archive, GET /me/archives).
"""

from datetime import date, time
from unittest.mock import patch

from api.models.trig import Trig
from api.models.user import TLog, User, UserArchive


def _create_user_with_log(db):
    """Helper: create a user with one published log."""
    from passlib.hash import des_crypt

    user = User(
        name="archivetest",
        firstname="Archive",
        surname="Test",
        email="archivetest@example.com",
        cryptpw=des_crypt.hash("testpassword"),
        email_valid="Y",
        public_ind="Y",
        archive_frequency="N",
        archive_format="C",
        auth0_user_id="auth0|9001",
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    trig = Trig(
        waypoint="TP9001",
        name="Archive Trig",
        fb_number="",
        stn_number="",
        status_id=1,
        user_added=0,
        current_use="Passive station",
        historic_use="Primary",
        condition="G",
        wgs_lat=51.5,
        wgs_long=-0.1,
        osgb_eastings=530000,
        osgb_northings=180000,
        osgb_gridref="TQ 30000 80000",
        osgb_height=100,
        town="London",
        permission_ind="Y",
        needs_attention=0,
        attention_comment="",
        crt_date=date(2020, 1, 1),
        crt_time=time(0, 0, 0),
        crt_user_id=user.id,
        crt_ip_addr="127.0.0.1",
    )
    db.add(trig)
    db.commit()
    db.refresh(trig)

    log = TLog(
        trig_id=trig.id,
        user_id=user.id,
        date=date(2024, 6, 15),
        time=time(14, 30),
        condition="G",
        comment="Found it!",
        score=7,
        ip_addr="127.0.0.1",
        source="W",
        status="P",
    )
    db.add(log)
    db.commit()

    return user


class TestSendArchiveNow:
    """Tests for POST /v1/users/me/archive."""

    @patch("api.services.email_service.email_service.send_archive_email")
    def test_send_archive_success(self, mock_send, client, db):
        mock_send.return_value = True
        user = _create_user_with_log(db)

        response = client.post(
            "/v1/users/me/archive",
            headers={"Authorization": f"Bearer auth0_user_{user.id}"},
        )

        assert response.status_code == 202
        data = response.json()
        assert data["status"] == "sent"
        assert data["log_count"] == 1
        assert data["zip_size_bytes"] > 0
        assert mock_send.called

    @patch("api.services.email_service.email_service.send_archive_email")
    def test_send_archive_creates_record(self, mock_send, client, db):
        mock_send.return_value = True
        user = _create_user_with_log(db)

        client.post(
            "/v1/users/me/archive",
            headers={"Authorization": f"Bearer auth0_user_{user.id}"},
        )

        archive = db.query(UserArchive).filter(UserArchive.user_id == user.id).first()
        assert archive is not None
        assert archive.status == "S"
        assert archive.log_count == 1
        assert archive.file_size_bytes > 0

    @patch("api.services.email_service.email_service.send_archive_email")
    def test_rate_limit_non_admin(self, mock_send, client, db):
        mock_send.return_value = True
        user = _create_user_with_log(db)

        # First request succeeds
        resp1 = client.post(
            "/v1/users/me/archive",
            headers={"Authorization": f"Bearer auth0_user_{user.id}"},
        )
        assert resp1.status_code == 202

        # Second request within 24h should be rate limited
        resp2 = client.post(
            "/v1/users/me/archive",
            headers={"Authorization": f"Bearer auth0_user_{user.id}"},
        )
        assert resp2.status_code == 429

    def test_no_email_address(self, client, db):
        from passlib.hash import des_crypt

        user = User(
            name="noemail",
            firstname="No",
            surname="Email",
            email="",
            cryptpw=des_crypt.hash("testpassword"),
            email_valid="N",
            public_ind="Y",
            auth0_user_id="auth0|9002",
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        response = client.post(
            "/v1/users/me/archive",
            headers={"Authorization": f"Bearer auth0_user_{user.id}"},
        )
        assert response.status_code == 400
        assert "email" in response.json()["detail"].lower()

    @patch("api.services.email_service.email_service.send_archive_email")
    def test_send_failure_records_error(self, mock_send, client, db):
        mock_send.return_value = False
        user = _create_user_with_log(db)

        response = client.post(
            "/v1/users/me/archive",
            headers={"Authorization": f"Bearer auth0_user_{user.id}"},
        )
        assert response.status_code == 500

        archive = db.query(UserArchive).filter(UserArchive.user_id == user.id).first()
        assert archive is not None
        assert archive.status == "F"


class TestListArchives:
    """Tests for GET /v1/users/me/archives."""

    def test_empty_list(self, client, db):
        from passlib.hash import des_crypt

        user = User(
            name="emptyarchive",
            firstname="Empty",
            surname="Archive",
            email="empty@example.com",
            cryptpw=des_crypt.hash("testpassword"),
            email_valid="Y",
            public_ind="Y",
            auth0_user_id="auth0|9003",
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        response = client.get(
            "/v1/users/me/archives",
            headers={"Authorization": f"Bearer auth0_user_{user.id}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["pagination"]["total"] == 0

    @patch("api.services.email_service.email_service.send_archive_email")
    def test_list_after_send(self, mock_send, client, db):
        mock_send.return_value = True
        user = _create_user_with_log(db)

        # Send one archive
        client.post(
            "/v1/users/me/archive",
            headers={"Authorization": f"Bearer auth0_user_{user.id}"},
        )

        # List archives
        response = client.get(
            "/v1/users/me/archives",
            headers={"Authorization": f"Bearer auth0_user_{user.id}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["pagination"]["total"] == 1
        assert len(data["items"]) == 1
        assert data["items"][0]["status"] == "S"
        assert data["items"][0]["log_count"] == 1
