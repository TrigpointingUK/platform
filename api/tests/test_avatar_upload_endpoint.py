"""
Tests for the POST /v1/users/me/avatar endpoint.

Verifies image upload validation, processing, S3 upload, Auth0 sync, and
cache-busting version parameter in the returned URL.
"""

import io
import uuid
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from api.core.config import settings
from api.models.user import User


def _make_jpeg(width: int = 300, height: int = 300) -> bytes:
    img = Image.new("RGB", (width, height), color=(128, 128, 128))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    buf.seek(0)
    return buf.getvalue()


def _make_png(width: int = 300, height: int = 300) -> bytes:
    img = Image.new("RGBA", (width, height), color=(128, 128, 128, 255))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf.getvalue()


@pytest.fixture
def avatar_user(make_user):
    """User with an auth0_user_id for avatar tests."""
    return make_user(auth0_user_id=f"auth0|avatar_{uuid.uuid4().hex[:8]}")


def _auth_header(user: User) -> dict:
    return {"Authorization": f"Bearer auth0_user_{user.id}"}


class TestAvatarUploadEndpoint:
    """Tests for POST /v1/users/me/avatar."""

    @patch("api.services.avatar_service.AvatarService")
    @patch("api.services.auth0_service.auth0_service")
    def test_upload_success_returns_versioned_url(
        self, mock_auth0, mock_avatar_cls, client: TestClient, avatar_user
    ):
        mock_svc = MagicMock()
        mock_avatar_cls.return_value = mock_svc
        mock_svc.validate_image.return_value = (True, "Image is valid")
        mock_svc.process_image.return_value = b"processed"
        mock_svc.upload.return_value = (
            "https://trigpointinguk-avatars.s3.amazonaws.com/U00001.jpg"
        )
        mock_auth0.update_user_picture.return_value = True

        jpeg = _make_jpeg()
        response = client.post(
            f"{settings.API_V1_STR}/users/me/avatar",
            headers=_auth_header(avatar_user),
            files={"file": ("avatar.jpg", jpeg, "image/jpeg")},
        )

        assert response.status_code == 200
        data = response.json()
        assert "avatar_url" in data
        assert "?v=" in data["avatar_url"]
        assert data["avatar_url"].startswith(
            "https://trigpointinguk-avatars.s3.amazonaws.com/"
        )

    @patch("api.services.avatar_service.AvatarService")
    @patch("api.services.auth0_service.auth0_service")
    def test_upload_calls_auth0_update(
        self, mock_auth0, mock_avatar_cls, client: TestClient, avatar_user
    ):
        """Auth0 picture field should be updated with the versioned URL."""
        mock_svc = MagicMock()
        mock_avatar_cls.return_value = mock_svc
        mock_svc.validate_image.return_value = (True, "Image is valid")
        mock_svc.process_image.return_value = b"processed"
        mock_svc.upload.return_value = (
            "https://trigpointinguk-avatars.s3.amazonaws.com/U00001.jpg"
        )
        mock_auth0.update_user_picture.return_value = True

        response = client.post(
            f"{settings.API_V1_STR}/users/me/avatar",
            headers=_auth_header(avatar_user),
            files={"file": ("avatar.jpg", _make_jpeg(), "image/jpeg")},
        )

        assert response.status_code == 200
        mock_auth0.update_user_picture.assert_called_once()
        call_args = mock_auth0.update_user_picture.call_args
        assert call_args[0][0] == avatar_user.auth0_user_id
        assert "?v=" in call_args[0][1]

    @patch("api.services.avatar_service.AvatarService")
    def test_upload_rejects_invalid_image(
        self, mock_avatar_cls, client: TestClient, avatar_user
    ):
        mock_svc = MagicMock()
        mock_avatar_cls.return_value = mock_svc
        mock_svc.validate_image.return_value = (False, "Only JPEG, PNG, and WebP")

        response = client.post(
            f"{settings.API_V1_STR}/users/me/avatar",
            headers=_auth_header(avatar_user),
            files={"file": ("bad.bmp", b"\x00" * 200, "image/bmp")},
        )

        assert response.status_code == 400
        assert "JPEG" in response.json()["detail"]

    @patch("api.services.avatar_service.AvatarService")
    def test_upload_rejects_empty_file(
        self, mock_avatar_cls, client: TestClient, avatar_user
    ):
        response = client.post(
            f"{settings.API_V1_STR}/users/me/avatar",
            headers=_auth_header(avatar_user),
            files={"file": ("empty.jpg", b"", "image/jpeg")},
        )

        assert response.status_code == 400
        assert "empty" in response.json()["detail"].lower()

    @patch("api.services.avatar_service.AvatarService")
    def test_upload_returns_500_on_s3_failure(
        self, mock_avatar_cls, client: TestClient, avatar_user
    ):
        mock_svc = MagicMock()
        mock_avatar_cls.return_value = mock_svc
        mock_svc.validate_image.return_value = (True, "Image is valid")
        mock_svc.process_image.return_value = b"processed"
        mock_svc.upload.return_value = None

        response = client.post(
            f"{settings.API_V1_STR}/users/me/avatar",
            headers=_auth_header(avatar_user),
            files={"file": ("avatar.jpg", _make_jpeg(), "image/jpeg")},
        )

        assert response.status_code == 500
        assert "upload" in response.json()["detail"].lower()

    @patch("api.services.avatar_service.AvatarService")
    def test_upload_returns_400_on_processing_failure(
        self, mock_avatar_cls, client: TestClient, avatar_user
    ):
        mock_svc = MagicMock()
        mock_avatar_cls.return_value = mock_svc
        mock_svc.validate_image.return_value = (True, "Image is valid")
        mock_svc.process_image.return_value = None

        response = client.post(
            f"{settings.API_V1_STR}/users/me/avatar",
            headers=_auth_header(avatar_user),
            files={"file": ("avatar.jpg", _make_jpeg(), "image/jpeg")},
        )

        assert response.status_code == 400
        assert "process" in response.json()["detail"].lower()

    def test_upload_requires_authentication(self, client: TestClient):
        response = client.post(
            f"{settings.API_V1_STR}/users/me/avatar",
            files={"file": ("avatar.jpg", _make_jpeg(), "image/jpeg")},
        )

        assert response.status_code in (401, 403)

    @patch("api.services.avatar_service.AvatarService")
    @patch("api.services.auth0_service.auth0_service")
    def test_upload_succeeds_even_when_auth0_sync_fails(
        self, mock_auth0, mock_avatar_cls, client: TestClient, avatar_user
    ):
        """Auth0 sync failure should not prevent the response being returned."""
        mock_svc = MagicMock()
        mock_avatar_cls.return_value = mock_svc
        mock_svc.validate_image.return_value = (True, "Image is valid")
        mock_svc.process_image.return_value = b"processed"
        mock_svc.upload.return_value = (
            "https://trigpointinguk-avatars.s3.amazonaws.com/U00001.jpg"
        )
        mock_auth0.update_user_picture.return_value = False

        response = client.post(
            f"{settings.API_V1_STR}/users/me/avatar",
            headers=_auth_header(avatar_user),
            files={"file": ("avatar.jpg", _make_jpeg(), "image/jpeg")},
        )

        assert response.status_code == 200
        assert "avatar_url" in response.json()

    @patch("api.services.avatar_service.AvatarService")
    @patch("api.services.auth0_service.auth0_service")
    def test_upload_accepts_png(
        self, mock_auth0, mock_avatar_cls, client: TestClient, avatar_user
    ):
        mock_svc = MagicMock()
        mock_avatar_cls.return_value = mock_svc
        mock_svc.validate_image.return_value = (True, "Image is valid")
        mock_svc.process_image.return_value = b"processed"
        mock_svc.upload.return_value = (
            "https://trigpointinguk-avatars.s3.amazonaws.com/U00001.jpg"
        )
        mock_auth0.update_user_picture.return_value = True

        response = client.post(
            f"{settings.API_V1_STR}/users/me/avatar",
            headers=_auth_header(avatar_user),
            files={"file": ("avatar.png", _make_png(), "image/png")},
        )

        assert response.status_code == 200

    @patch("api.services.avatar_service.AvatarService")
    @patch("api.services.auth0_service.auth0_service")
    def test_upload_version_param_is_numeric(
        self, mock_auth0, mock_avatar_cls, client: TestClient, avatar_user
    ):
        """The ?v= cache buster should be a numeric unix timestamp."""
        mock_svc = MagicMock()
        mock_avatar_cls.return_value = mock_svc
        mock_svc.validate_image.return_value = (True, "Image is valid")
        mock_svc.process_image.return_value = b"processed"
        mock_svc.upload.return_value = (
            "https://trigpointinguk-avatars.s3.amazonaws.com/U00001.jpg"
        )
        mock_auth0.update_user_picture.return_value = True

        response = client.post(
            f"{settings.API_V1_STR}/users/me/avatar",
            headers=_auth_header(avatar_user),
            files={"file": ("avatar.jpg", _make_jpeg(), "image/jpeg")},
        )

        url = response.json()["avatar_url"]
        version = url.split("?v=")[1]
        assert version.isdigit()
        assert int(version) > 1_000_000_000  # Reasonable unix timestamp
