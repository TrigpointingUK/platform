"""
Tests for avatar service (image validation, processing, S3 upload).
"""

import io
from unittest.mock import Mock, patch

from botocore.exceptions import ClientError
from PIL import Image

from api.services.avatar_service import AvatarService


def _make_jpeg(width: int = 300, height: int = 300) -> bytes:
    """Create a minimal JPEG image in memory."""
    img = Image.new("RGB", (width, height), color=(128, 128, 128))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


def _make_png(width: int = 300, height: int = 300) -> bytes:
    img = Image.new("RGBA", (width, height), color=(128, 128, 128, 255))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


class TestAvatarServiceKeyGeneration:
    def test_generate_key(self):
        service = AvatarService()
        assert service._generate_key(1) == "U00001.jpg"
        assert service._generate_key(12345) == "U12345.jpg"

    def test_get_public_url(self):
        service = AvatarService()
        url = service.get_public_url(42)
        assert "U00042.jpg" in url
        assert "s3.amazonaws.com" in url


class TestAvatarValidation:
    def test_valid_jpeg(self):
        service = AvatarService()
        ok, msg = service.validate_image(_make_jpeg())
        assert ok is True

    def test_valid_png(self):
        service = AvatarService()
        ok, msg = service.validate_image(_make_png())
        assert ok is True

    def test_too_small_file(self):
        service = AvatarService()
        ok, msg = service.validate_image(b"tiny")
        assert ok is False
        assert "too small" in msg.lower()

    @patch("api.services.avatar_service.settings")
    def test_too_large_file(self, mock_settings):
        mock_settings.AVATAR_MAX_SIZE = 100
        service = AvatarService()
        ok, msg = service.validate_image(_make_jpeg())
        assert ok is False
        assert "exceeds" in msg.lower()

    def test_image_too_small_dimensions(self):
        service = AvatarService()
        ok, msg = service.validate_image(_make_jpeg(10, 10))
        assert ok is False
        assert "50x50" in msg

    def test_invalid_format(self):
        service = AvatarService()
        ok, msg = service.validate_image(b"\x00" * 200)
        assert ok is False


class TestAvatarProcessing:
    def test_process_jpeg(self):
        service = AvatarService()
        result = service.process_image(_make_jpeg(400, 400))
        assert result is not None
        with Image.open(io.BytesIO(result)) as img:
            assert img.size == (200, 200)
            assert img.format == "JPEG"

    def test_process_png_converts_to_jpeg(self):
        service = AvatarService()
        result = service.process_image(_make_png())
        assert result is not None
        with Image.open(io.BytesIO(result)) as img:
            assert img.format == "JPEG"

    def test_process_invalid_returns_none(self):
        service = AvatarService()
        result = service.process_image(b"not an image at all")
        assert result is None


class TestAvatarUpload:
    @patch("api.services.avatar_service.boto3.client")
    def test_upload_success(self, mock_boto_client):
        mock_client = Mock()
        mock_boto_client.return_value = mock_client

        service = AvatarService()
        url = service.upload(42, b"imagedata")

        assert url is not None
        assert "U00042.jpg" in url
        mock_client.put_object.assert_called_once()
        call_kwargs = mock_client.put_object.call_args.kwargs
        assert call_kwargs["ACL"] == "public-read"
        assert call_kwargs["ContentType"] == "image/jpeg"

    @patch("api.services.avatar_service.boto3.client")
    def test_upload_sets_no_cache(self, mock_boto_client):
        """Avatars are mutable; S3 must send no-cache so browsers revalidate."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client

        service = AvatarService()
        service.upload(1, b"imagedata")

        call_kwargs = mock_client.put_object.call_args.kwargs
        assert call_kwargs["CacheControl"] == "no-cache"

    @patch("api.services.avatar_service.boto3.client")
    def test_upload_uses_correct_bucket_and_key(self, mock_boto_client):
        """Verify the bucket and key passed to put_object match the service's config."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client

        service = AvatarService()
        service.upload(7, b"imagedata")

        call_kwargs = mock_client.put_object.call_args.kwargs
        assert call_kwargs["Bucket"] == service.bucket
        assert call_kwargs["Key"] == "U00007.jpg"
        assert call_kwargs["Body"] == b"imagedata"

    @patch("api.services.avatar_service.boto3.client")
    def test_upload_failure_returns_none(self, mock_boto_client):
        mock_client = Mock()
        mock_boto_client.return_value = mock_client
        mock_client.put_object.side_effect = ClientError(
            {"Error": {"Code": "AccessDenied"}}, "PutObject"
        )

        service = AvatarService()
        url = service.upload(42, b"imagedata")
        assert url is None

    def test_upload_without_s3_client(self):
        service = AvatarService()
        service.s3_client = None
        url = service.upload(42, b"imagedata")
        assert url is None

    @patch("api.services.avatar_service.boto3.client")
    def test_delete_success(self, mock_boto_client):
        mock_client = Mock()
        mock_boto_client.return_value = mock_client

        service = AvatarService()
        assert service.delete(42) is True
        mock_client.delete_object.assert_called_once()

    @patch("api.services.avatar_service.boto3.client")
    def test_delete_failure(self, mock_boto_client):
        mock_client = Mock()
        mock_boto_client.return_value = mock_client
        mock_client.delete_object.side_effect = ClientError(
            {"Error": {"Code": "NoSuchKey"}}, "DeleteObject"
        )

        service = AvatarService()
        assert service.delete(42) is False

    def test_delete_without_s3_client(self):
        service = AvatarService()
        service.s3_client = None
        assert service.delete(42) is False
