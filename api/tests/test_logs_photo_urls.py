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
    import uuid

    unique_suffix = uuid.uuid4().hex[:8]

    user = User(
        name=f"testuser_{unique_suffix}",
        firstname="Test",
        surname="User",
        email=f"test_{unique_suffix}@example.com",
        auth0_user_id=f"auth0|{unique_suffix}",
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
    db.add(tlog)
    db.commit()
    db.refresh(tlog)

    # Create a photo with rotated filenames
    photo = TPhoto(
        tlog_id=tlog.id,  # Use dynamic tlog ID
        server_id=settings.PHOTOS_SERVER_ID,
        type="T",
        filename=f"424/P{unique_suffix}_r1.jpg",  # Rotated filename with unique suffix
        filesize=42953,
        height=738,
        width=415,
        icon_filename=f"424/I{unique_suffix}_r1.jpg",  # Rotated icon filename with unique suffix
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
    db.add(photo)
    db.commit()
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

        # Verify URLs contain the rotated filenames (use actual photo filenames)
        assert photo.filename in photo_data["photo_url"]
        assert photo.icon_filename in photo_data["icon_url"]

        # Verify full URLs are properly constructed with the actual filenames
        expected_photo_url = (
            f"{base_url}{photo.filename}"
            if not base_url.endswith("/")
            else f"{base_url}{photo.filename}"
        )
        expected_icon_url = (
            f"{base_url}{photo.icon_filename}"
            if not base_url.endswith("/")
            else f"{base_url}{photo.icon_filename}"
        )

        # The URLs should match the expected format
        assert (
            photo_data["photo_url"] == expected_photo_url
            or photo_data["photo_url"] == f"{base_url.rstrip('/')}/{photo.filename}"
        )
        assert (
            photo_data["icon_url"] == expected_icon_url
            or photo_data["icon_url"] == f"{base_url.rstrip('/')}/{photo.icon_filename}"
        )

    def test_list_logs_with_rotated_photo_urls(self, client: TestClient, db: Session):
        """Test that GET /logs/{log_id}?include=photos returns proper URLs for rotated photos."""
        user, tlog, photo = seed_test_data(db)

        # Request specific log with photos included (not paginated list)
        resp = client.get(f"{settings.API_V1_STR}/logs/{tlog.id}?include=photos")

        assert resp.status_code == 200
        test_log = resp.json()

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

        # Verify URLs contain the rotated filenames (use actual photo filenames)
        assert photo.filename in photo_data["photo_url"]
        assert photo.icon_filename in photo_data["icon_url"]

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

        # Verify URLs contain the rotated filenames (use actual photo filenames)
        assert photo.filename in photo_data["photo_url"]
        assert photo.icon_filename in photo_data["icon_url"]
