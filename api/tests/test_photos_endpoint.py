"""
Tests for photo endpoint edge cases.

Tests photo evaluation, rotation, and authorization scenarios.
"""

import io
import uuid
from datetime import date, time
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from api.models.server import Server
from api.models.tphoto import TPhoto
from api.models.trig import Trig
from api.models.user import TLog, User


def create_test_image(width: int = 100, height: int = 100, color: str = "red") -> bytes:
    """Create a valid JPEG image for testing."""
    img = Image.new("RGB", (width, height), color=color)
    buffer = io.BytesIO()
    img.save(buffer, format="JPEG", quality=85)
    buffer.seek(0)
    return buffer.getvalue()


@pytest.fixture
def photo_test_data(db):
    """Create test data for photo endpoint tests."""
    unique_suffix = uuid.uuid4().hex[:6]

    # Create test user (owner)
    owner = User(
        name=f"PhotoOwner_{unique_suffix}",
        firstname="Photo",
        surname="Owner",
        email=f"photo_owner_{unique_suffix}@example.invalid",
        cryptpw="",
        email_valid="Y",
        public_ind="Y",
    )
    db.add(owner)
    db.flush()

    # Create another user (not owner)
    other_user = User(
        name=f"PhotoOther_{unique_suffix}",
        firstname="Other",
        surname="User",
        email=f"photo_other_{unique_suffix}@example.invalid",
        cryptpw="",
        email_valid="Y",
        public_ind="Y",
    )
    db.add(other_user)
    db.flush()

    # Create test trig
    trig = Trig(
        waypoint=f"PH{unique_suffix[:4]}",
        name=f"PhotoTestTrig_{unique_suffix}",
        fb_number=f"PHFB{unique_suffix[:3]}",
        stn_number="STN001",
        status_id=1,
        user_added=0,
        current_use="Passive station",
        historic_use="Primary",
        condition="G",
        wgs_lat=51.5,
        wgs_long=-0.1,
        wgs_height=100,
        osgb_eastings=530000,
        osgb_northings=180000,
        osgb_gridref="TQ 30000 80000",
        osgb_height=100,
        county="TestCounty",
        town="TestTown",
        permission_ind="Y",
        needs_attention=0,
        attention_comment="",
        crt_date=date(2023, 1, 1),
        crt_time=time(0, 0, 0),
        crt_ip_addr="127.0.0.1",
    )
    db.add(trig)
    db.flush()

    # Create test log
    log = TLog(
        trig_id=trig.id,
        user_id=owner.id,
        date=date(2023, 12, 15),
        time=time(14, 30, 0),
        osgb_eastings=530000,
        osgb_northings=180000,
        osgb_gridref="TQ 30000 80000",
        fb_number="",
        condition="G",
        comment=f"Test log for photo tests {unique_suffix}",
        score=7,
        ip_addr="127.0.0.1",
        source="W",
    )
    db.add(log)
    db.flush()

    # Ensure server exists
    server = db.query(Server).filter(Server.id == 1).first()
    if not server:
        server = Server(
            id=1,
            url="https://example.invalid/photos/",
            path="/photos/",
            name="Test Server",
        )
        db.add(server)
        db.flush()

    # Create test photo
    photo = TPhoto(
        tlog_id=log.id,
        server_id=1,
        type="T",
        filename=f"test_{unique_suffix}.jpg",
        filesize=10000,
        height=600,
        width=800,
        icon_filename=f"test_{unique_suffix}_thumb.jpg",
        icon_filesize=1000,
        icon_height=75,
        icon_width=100,
        name=f"Test Photo {unique_suffix}",
        text_desc="Test photo description",
        ip_addr="127.0.0.1",
        public_ind="Y",
        deleted_ind="N",
        source="W",
    )
    db.add(photo)

    db.commit()

    return {
        "owner": owner,
        "other_user": other_user,
        "trig": trig,
        "log": log,
        "photo": photo,
        "server": server,
        "suffix": unique_suffix,
    }


class TestGetPhoto:
    """Tests for GET /v1/photos/{photo_id}."""

    def test_get_photo_returns_data(self, client: TestClient, photo_test_data, db):
        """Test fetching a photo by ID."""
        photo = photo_test_data["photo"]

        response = client.get(f"/v1/photos/{photo.id}")

        assert response.status_code == 200
        data = response.json()

        assert data["id"] == photo.id
        assert data["log_id"] == photo.tlog_id
        assert data["type"] == "T"
        assert data["caption"] == photo.name

    def test_get_photo_not_found(self, client: TestClient, db):
        """Test 404 for non-existent photo."""
        response = client.get("/v1/photos/999999999")

        assert response.status_code == 404

    def test_get_photo_includes_urls(self, client: TestClient, photo_test_data, db):
        """Test that photo response includes URLs."""
        photo = photo_test_data["photo"]

        response = client.get(f"/v1/photos/{photo.id}")

        assert response.status_code == 200
        data = response.json()

        assert "photo_url" in data
        assert "icon_url" in data
        assert photo.filename in data["photo_url"]
        assert photo.icon_filename in data["icon_url"]


class TestListPhotos:
    """Tests for GET /v1/photos."""

    def test_list_photos(self, client: TestClient, photo_test_data, db):
        """Test listing photos."""
        response = client.get("/v1/photos")

        assert response.status_code == 200
        data = response.json()

        assert "items" in data
        assert "pagination" in data
        assert "links" in data

    def test_list_photos_by_log_id(self, client: TestClient, photo_test_data, db):
        """Test filtering photos by log_id."""
        log = photo_test_data["log"]
        photo = photo_test_data["photo"]

        response = client.get(f"/v1/photos?log_id={log.id}")

        assert response.status_code == 200
        data = response.json()

        # Should find our test photo
        photo_ids = [p["id"] for p in data["items"]]
        assert photo.id in photo_ids

    def test_list_photos_pagination(self, client: TestClient, db):
        """Test photo list pagination."""
        response = client.get("/v1/photos?skip=0&limit=5")

        assert response.status_code == 200
        data = response.json()

        assert len(data["items"]) <= 5
        assert data["pagination"]["limit"] == 5


class TestUpdatePhoto:
    """Tests for PATCH /v1/photos/{photo_id}."""

    def test_update_photo_as_owner(self, client: TestClient, photo_test_data, db):
        """Test updating photo as owner."""
        owner = photo_test_data["owner"]
        photo = photo_test_data["photo"]

        response = client.patch(
            f"/v1/photos/{photo.id}",
            json={"caption": "Updated Caption"},
            headers={"Authorization": f"Bearer auth0_user_{owner.id}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["caption"] == "Updated Caption"

    def test_update_photo_not_owner_denied(
        self, client: TestClient, photo_test_data, db
    ):
        """Test that non-owner cannot update photo."""
        other_user = photo_test_data["other_user"]
        photo = photo_test_data["photo"]

        response = client.patch(
            f"/v1/photos/{photo.id}",
            json={"caption": "Unauthorized Update"},
            headers={"Authorization": f"Bearer auth0_user_{other_user.id}"},
        )

        assert response.status_code == 403

    def test_update_photo_as_admin(self, client: TestClient, photo_test_data, db):
        """Test that admin can update any photo."""
        photo = photo_test_data["photo"]

        response = client.patch(
            f"/v1/photos/{photo.id}",
            json={"caption": "Admin Updated"},
            headers={"Authorization": "Bearer auth0_admin"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["caption"] == "Admin Updated"

    def test_update_photo_not_found(self, client: TestClient, photo_test_data, db):
        """Test 404 when updating non-existent photo."""
        owner = photo_test_data["owner"]

        response = client.patch(
            "/v1/photos/999999999",
            json={"caption": "Does Not Exist"},
            headers={"Authorization": f"Bearer auth0_user_{owner.id}"},
        )

        assert response.status_code == 404

    def test_update_photo_unauthenticated(
        self, client: TestClient, photo_test_data, db
    ):
        """Test that unauthenticated update is rejected."""
        photo = photo_test_data["photo"]

        response = client.patch(
            f"/v1/photos/{photo.id}",
            json={"caption": "No Auth"},
        )

        assert response.status_code == 401


class TestDeletePhoto:
    """Tests for DELETE /v1/photos/{photo_id}."""

    def test_delete_photo_as_owner(self, client: TestClient, photo_test_data, db):
        """Test deleting photo as owner."""
        owner = photo_test_data["owner"]
        photo = photo_test_data["photo"]
        photo_id = photo.id

        response = client.delete(
            f"/v1/photos/{photo_id}",
            headers={"Authorization": f"Bearer auth0_user_{owner.id}"},
        )

        assert response.status_code == 204

        # Verify soft delete
        db.refresh(photo)
        assert photo.deleted_ind == "Y"

    def test_delete_photo_not_owner_denied(
        self, client: TestClient, photo_test_data, db
    ):
        """Test that non-owner cannot delete photo."""
        other_user = photo_test_data["other_user"]
        photo = photo_test_data["photo"]

        response = client.delete(
            f"/v1/photos/{photo.id}",
            headers={"Authorization": f"Bearer auth0_user_{other_user.id}"},
        )

        assert response.status_code == 403

    def test_delete_photo_as_admin(self, client: TestClient, db):
        """Test that admin can delete any photo."""
        # Create a fresh photo for this test
        unique_suffix = uuid.uuid4().hex[:6]

        user = User(
            name=f"AdminDeleteTest_{unique_suffix}",
            firstname="Admin",
            surname="Delete",
            email=f"admin_delete_{unique_suffix}@example.invalid",
            cryptpw="",
            email_valid="Y",
            public_ind="Y",
        )
        db.add(user)
        db.flush()

        log = TLog(
            trig_id=1,
            user_id=user.id,
            date=date(2023, 12, 15),
            time=time(14, 30, 0),
            osgb_eastings=530000,
            osgb_northings=180000,
            osgb_gridref="TQ 30000 80000",
            fb_number="",
            condition="G",
            comment="Admin delete test",
            score=7,
            ip_addr="127.0.0.1",
            source="W",
        )
        db.add(log)
        db.flush()

        photo = TPhoto(
            tlog_id=log.id,
            server_id=1,
            type="T",
            filename=f"admin_delete_{unique_suffix}.jpg",
            filesize=10000,
            height=600,
            width=800,
            icon_filename=f"admin_delete_{unique_suffix}_thumb.jpg",
            icon_filesize=1000,
            icon_height=75,
            icon_width=100,
            name="Admin Delete Test",
            text_desc="Test",
            ip_addr="127.0.0.1",
            public_ind="Y",
            deleted_ind="N",
            source="W",
        )
        db.add(photo)
        db.commit()

        response = client.delete(
            f"/v1/photos/{photo.id}",
            headers={"Authorization": "Bearer auth0_admin"},
        )

        assert response.status_code == 204

    def test_delete_photo_not_found(self, client: TestClient, photo_test_data, db):
        """Test 404 when deleting non-existent photo."""
        owner = photo_test_data["owner"]

        response = client.delete(
            "/v1/photos/999999999",
            headers={"Authorization": f"Bearer auth0_user_{owner.id}"},
        )

        assert response.status_code == 404

    def test_delete_photo_unauthenticated(
        self, client: TestClient, photo_test_data, db
    ):
        """Test that unauthenticated delete is rejected."""
        photo = photo_test_data["photo"]

        response = client.delete(f"/v1/photos/{photo.id}")

        assert response.status_code == 401


class TestEvaluatePhoto:
    """Tests for GET /v1/photos/{photo_id}/evaluate."""

    @patch("api.api.v1.endpoints.photos.requests.get")
    @patch("api.api.v1.endpoints.photos.RekognitionService")
    def test_evaluate_photo_success(
        self,
        mock_rekognition_class,
        mock_requests_get,
        client: TestClient,
        photo_test_data,
        db,
    ):
        """Test successful photo evaluation."""
        photo = photo_test_data["photo"]

        # Create mock image bytes
        test_image_bytes = create_test_image(800, 600)

        # Mock HTTP requests for photo and icon
        mock_response = MagicMock()
        mock_response.content = test_image_bytes
        mock_response.raise_for_status = MagicMock()
        mock_requests_get.return_value = mock_response

        # Mock Rekognition service
        mock_rekognition = MagicMock()
        mock_rekognition.analyse_orientation.return_value = {
            "suggested_rotation": 0,
            "confidence": 0.95,
        }
        mock_rekognition.moderate_content.return_value = {
            "is_safe": True,
            "labels": [],
        }
        mock_rekognition_class.return_value = mock_rekognition

        response = client.get(f"/v1/photos/{photo.id}/evaluate")

        assert response.status_code == 200
        data = response.json()

        assert data["photo_id"] == photo.id
        assert "photo_accessible" in data
        assert "icon_accessible" in data
        assert "errors" in data

    def test_evaluate_photo_not_found(self, client: TestClient, db):
        """Test 404 for evaluating non-existent photo."""
        response = client.get("/v1/photos/999999999/evaluate")

        assert response.status_code == 404

    @patch("api.api.v1.endpoints.photos.requests.get")
    def test_evaluate_photo_download_failure(
        self, mock_requests_get, client: TestClient, photo_test_data, db
    ):
        """Test evaluation when photo download fails."""
        import requests

        photo = photo_test_data["photo"]

        # Mock HTTP request failure
        mock_requests_get.side_effect = requests.exceptions.RequestException(
            "Connection failed"
        )

        response = client.get(f"/v1/photos/{photo.id}/evaluate")

        assert response.status_code == 200
        data = response.json()

        # Should report download failure
        assert data["photo_accessible"] is False
        assert len(data["errors"]) > 0
        assert any("download failed" in err.lower() for err in data["errors"])


class TestRotatePhoto:
    """Tests for POST /v1/photos/{photo_id}/rotate."""

    @patch("api.api.v1.endpoints.photos.requests.get")
    @patch("api.api.v1.endpoints.photos.S3Service")
    def test_rotate_photo_success(
        self, mock_s3_class, mock_requests_get, client: TestClient, photo_test_data, db
    ):
        """Test successful photo rotation."""
        photo = photo_test_data["photo"]

        # Create mock image bytes
        test_image_bytes = create_test_image(800, 600)

        # Mock HTTP request for downloading photo
        mock_response = MagicMock()
        mock_response.content = test_image_bytes
        mock_response.raise_for_status = MagicMock()
        mock_requests_get.return_value = mock_response

        # Mock S3 service
        mock_s3 = MagicMock()
        mock_s3.generate_revision_filename.side_effect = lambda f: "rev_" + f
        mock_s3.upload_photo_and_thumbnail_with_keys.return_value = (
            "rev_photo.jpg",
            "rev_thumb.jpg",
        )
        mock_s3_class.return_value = mock_s3

        response = client.post(
            f"/v1/photos/{photo.id}/rotate",
            json={"angle": 90},
        )

        assert response.status_code == 200
        data = response.json()

        assert data["id"] == photo.id
        assert "photo_url" in data
        assert "icon_url" in data

    def test_rotate_photo_not_found(self, client: TestClient, db):
        """Test 404 when rotating non-existent photo."""
        response = client.post(
            "/v1/photos/999999999/rotate",
            json={"angle": 90},
        )

        assert response.status_code == 404

    def test_rotate_photo_invalid_angle(self, client: TestClient, photo_test_data, db):
        """Test validation for invalid rotation angle."""
        photo = photo_test_data["photo"]

        response = client.post(
            f"/v1/photos/{photo.id}/rotate",
            json={"angle": 45},  # Invalid - must be 90, 180, or 270
        )

        # Should return validation error
        assert response.status_code == 422

    @patch("api.api.v1.endpoints.photos.requests.get")
    def test_rotate_photo_download_failure(
        self, mock_requests_get, client: TestClient, photo_test_data, db
    ):
        """Test rotation when photo download fails."""
        import requests

        photo = photo_test_data["photo"]

        # Mock HTTP request failure
        mock_requests_get.side_effect = requests.exceptions.RequestException(
            "Connection failed"
        )

        response = client.post(
            f"/v1/photos/{photo.id}/rotate",
            json={"angle": 90},
        )

        assert response.status_code == 500
        assert "download" in response.json()["detail"].lower()


class TestPhotoResponseStructure:
    """Tests for response structure validation."""

    def test_photo_response_structure(self, client: TestClient, photo_test_data, db):
        """Test TPhotoResponse has all expected fields."""
        photo = photo_test_data["photo"]

        response = client.get(f"/v1/photos/{photo.id}")

        assert response.status_code == 200
        data = response.json()

        expected_fields = [
            "id",
            "log_id",
            "user_id",
            "type",
            "filesize",
            "height",
            "width",
            "icon_filesize",
            "icon_height",
            "icon_width",
            "caption",
            "text_desc",
            "license",
            "photo_url",
            "icon_url",
        ]

        for field in expected_fields:
            assert field in data, f"Missing field: {field}"

    def test_photo_list_response_structure(self, client: TestClient, db):
        """Test photo list response has pagination structure."""
        response = client.get("/v1/photos")

        assert response.status_code == 200
        data = response.json()

        assert "items" in data
        assert "pagination" in data
        assert "links" in data

        pagination = data["pagination"]
        assert "total" in pagination
        assert "limit" in pagination
        assert "offset" in pagination
        assert "has_more" in pagination

        links = data["links"]
        assert "self" in links
        assert "next" in links
        assert "prev" in links

    @patch("api.api.v1.endpoints.photos.requests.get")
    @patch("api.api.v1.endpoints.photos.RekognitionService")
    def test_evaluation_response_structure(
        self,
        mock_rekognition_class,
        mock_requests_get,
        client: TestClient,
        photo_test_data,
        db,
    ):
        """Test TPhotoEvaluationResponse has all expected fields."""
        photo = photo_test_data["photo"]

        # Create mock image bytes
        test_image_bytes = create_test_image(800, 600)

        # Mock HTTP requests
        mock_response = MagicMock()
        mock_response.content = test_image_bytes
        mock_response.raise_for_status = MagicMock()
        mock_requests_get.return_value = mock_response

        # Mock Rekognition service
        mock_rekognition = MagicMock()
        mock_rekognition.analyse_orientation.return_value = None
        mock_rekognition.moderate_content.return_value = None
        mock_rekognition_class.return_value = mock_rekognition

        response = client.get(f"/v1/photos/{photo.id}/evaluate")

        assert response.status_code == 200
        data = response.json()

        required_fields = [
            "photo_id",
            "photo_accessible",
            "icon_accessible",
            "photo_dimension_match",
            "icon_dimension_match",
            "errors",
        ]

        for field in required_fields:
            assert field in data, f"Missing field: {field}"
