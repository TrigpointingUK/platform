"""
Tests for log photo URLs after rotation.
"""

from datetime import datetime

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from api.core.config import settings
from api.models.server import Server
from api.models.tphoto import TPhoto
from api.models.user import TLog, User


def seed_test_data(db: Session) -> tuple[User, TLog, TPhoto]:
    """Create test user, log, and rotated photo."""
    user = User(
        id=401,
        name="testuser",
        firstname="Test",
        surname="User",
        email="test@example.com",
        auth0_user_id="auth0|401",
    )
    tlog = TLog(
        id=4001,
        trig_id=1,
        user_id=401,
        date=datetime(2023, 1, 1).date(),
        time=datetime(2023, 1, 1).time(),
        osgb_eastings=1,
        osgb_northings=1,
        osgb_gridref="AA 00000 00000",
        fb_number="",
        condition="G",
        comment="Test log",
        score=0,
        ip_addr="127.0.0.1",
        source="W",
    )
    # Create a photo with rotated filenames
    photo = TPhoto(
        id=6001,
        tlog_id=4001,
        server_id=settings.PHOTOS_SERVER_ID,
        type="T",
        filename="424/P424363_r1.jpg",  # Rotated filename
        filesize=42953,
        height=738,
        width=415,
        icon_filename="424/I424363_r1.jpg",  # Rotated icon filename
        icon_filesize=2227,
        icon_height=120,
        icon_width=67,
        name="Test Photo",
        text_desc="Test description",
        ip_addr="127.0.0.1",
        public_ind="Y",
        deleted_ind="N",
        source="R",  # R for revised/rotated
        crt_timestamp=datetime.utcnow(),
    )
    db.add(user)
    db.add(tlog)
    db.add(photo)
    db.commit()
    db.refresh(user)
    db.refresh(tlog)
    db.refresh(photo)
    return user, tlog, photo


class TestLogPhotoUrls:
    """Test that log endpoints properly return photo URLs after rotation."""

    def test_get_log_with_rotated_photo_urls(self, client: TestClient, db: Session):
        """Test that GET /logs/{log_id}?include=photos returns proper URLs for rotated photos."""
        user, tlog, photo = seed_test_data(db)

        # Get the server URL for comparison
        server: Server | None = (
            db.query(Server).filter(Server.id == settings.PHOTOS_SERVER_ID).first()
        )
        base_url = str(server.url) if server and server.url else ""

        # Request log with photos included
        resp = client.get(f"{settings.API_V1_STR}/logs/{tlog.id}?include=photos")

        assert resp.status_code == 200
        body = resp.json()

        # Verify photos are included
        assert "photos" in body
        assert len(body["photos"]) == 1

        photo_data = body["photos"][0]

        # Verify photo URLs are not empty
        assert photo_data["photo_url"] != ""
        assert photo_data["icon_url"] != ""

        # Verify URLs contain the rotated filenames
        assert "424/P424363_r1.jpg" in photo_data["photo_url"]
        assert "424/I424363_r1.jpg" in photo_data["icon_url"]

        # Verify full URLs are properly constructed
        expected_photo_url = (
            f"{base_url}424/P424363_r1.jpg"
            if not base_url.endswith("/")
            else f"{base_url}424/P424363_r1.jpg"
        )
        expected_icon_url = (
            f"{base_url}424/I424363_r1.jpg"
            if not base_url.endswith("/")
            else f"{base_url}424/I424363_r1.jpg"
        )

        # The URLs should match the expected format
        assert (
            photo_data["photo_url"] == expected_photo_url
            or photo_data["photo_url"] == f"{base_url.rstrip('/')}/424/P424363_r1.jpg"
        )
        assert (
            photo_data["icon_url"] == expected_icon_url
            or photo_data["icon_url"] == f"{base_url.rstrip('/')}/424/I424363_r1.jpg"
        )

    def test_list_logs_with_rotated_photo_urls(self, client: TestClient, db: Session):
        """Test that GET /logs?include=photos returns proper URLs for rotated photos."""
        user, tlog, photo = seed_test_data(db)

        # Request logs with photos included
        resp = client.get(f"{settings.API_V1_STR}/logs?include=photos")

        assert resp.status_code == 200
        body = resp.json()

        # Find our test log
        test_logs = [item for item in body["items"] if item["id"] == tlog.id]
        assert len(test_logs) == 1

        test_log = test_logs[0]

        # Verify photos are included
        assert "photos" in test_log
        assert len(test_log["photos"]) >= 1

        # Find our test photo
        test_photos = [p for p in test_log["photos"] if p["id"] == photo.id]
        assert len(test_photos) == 1

        photo_data = test_photos[0]

        # Verify photo URLs are not empty
        assert photo_data["photo_url"] != ""
        assert photo_data["icon_url"] != ""

        # Verify URLs contain the rotated filenames
        assert "424/P424363_r1.jpg" in photo_data["photo_url"]
        assert "424/I424363_r1.jpg" in photo_data["icon_url"]

    def test_list_photos_for_log_with_rotated_urls(
        self, client: TestClient, db: Session
    ):
        """Test that GET /logs/{log_id}/photos returns proper URLs for rotated photos."""
        user, tlog, photo = seed_test_data(db)

        # Request photos for the log
        resp = client.get(f"{settings.API_V1_STR}/logs/{tlog.id}/photos")

        assert resp.status_code == 200
        body = resp.json()

        # Find our test photo
        test_photos = [p for p in body["items"] if p["id"] == photo.id]
        assert len(test_photos) == 1

        photo_data = test_photos[0]

        # Verify photo URLs are not empty
        assert photo_data["photo_url"] != ""
        assert photo_data["icon_url"] != ""

        # Verify URLs contain the rotated filenames
        assert "424/P424363_r1.jpg" in photo_data["photo_url"]
        assert "424/I424363_r1.jpg" in photo_data["icon_url"]
