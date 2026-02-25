"""
Avatar service for uploading user profile pictures to S3 and syncing to Auth0.
"""

import io
import logging
from typing import Optional, Tuple

import boto3
from botocore.exceptions import BotoCoreError, ClientError
from PIL import Image, ImageOps

from api.core.config import settings

logger = logging.getLogger(__name__)


class AvatarService:
    """Service for processing and storing user avatar images."""

    def __init__(self):
        try:
            self.s3_client = boto3.client("s3")
            self.bucket = settings.AVATARS_S3_BUCKET
        except Exception as e:
            logger.error(f"Failed to initialise S3 client for avatars: {e}")
            self.s3_client = None

    def _generate_key(self, user_id: int) -> str:
        return f"U{user_id:05d}.jpg"

    def get_public_url(self, user_id: int) -> str:
        key = self._generate_key(user_id)
        return f"https://{self.bucket}.s3.amazonaws.com/{key}"

    def validate_image(self, image_bytes: bytes) -> Tuple[bool, str]:
        """Validate that the uploaded file is an acceptable image for an avatar."""
        if len(image_bytes) > settings.AVATAR_MAX_SIZE:
            max_mb = settings.AVATAR_MAX_SIZE // (1024 * 1024)
            return False, f"File size exceeds maximum of {max_mb}MB"

        if len(image_bytes) < 100:
            return False, "File is too small to be a valid image"

        try:
            with Image.open(io.BytesIO(image_bytes)) as img:
                img.load()
                if img.format not in ("JPEG", "PNG", "WEBP", "MPO"):
                    return False, "Only JPEG, PNG, and WebP images are supported"
                width, height = img.size
                if width < 50 or height < 50:
                    return False, "Image must be at least 50x50 pixels"
            return True, "Image is valid"
        except Exception as e:
            logger.error(f"Avatar image validation failed: {e}")
            return False, f"Invalid image file: {e}"

    def process_image(self, image_bytes: bytes) -> Optional[bytes]:
        """
        Process avatar: apply EXIF orientation, resize to square, convert to JPEG.
        """
        try:
            with Image.open(io.BytesIO(image_bytes)) as img:
                transposed = ImageOps.exif_transpose(img)
                if transposed is None:
                    return None

                if transposed.mode not in ("RGB", "RGBA"):
                    transposed = transposed.convert("RGB")

                dim = settings.AVATAR_DIMENSION
                resized = transposed.resize((dim, dim), Image.Resampling.LANCZOS)

                if resized.mode == "RGBA":
                    resized = resized.convert("RGB")

                output = io.BytesIO()
                resized.save(output, format="JPEG", quality=90, optimize=True)
                return output.getvalue()
        except Exception as e:
            logger.error(f"Failed to process avatar image: {e}")
            return None

    def upload(self, user_id: int, image_bytes: bytes) -> Optional[str]:
        """
        Upload processed avatar to S3 with public-read ACL.

        Returns the public URL on success, None on failure.
        """
        if not self.s3_client:
            logger.error("S3 client not available for avatar upload")
            return None

        key = self._generate_key(user_id)

        try:
            self.s3_client.put_object(
                Bucket=self.bucket,
                Key=key,
                Body=image_bytes,
                ContentType="image/jpeg",
                CacheControl="no-cache",
                ACL="public-read",
            )
            url = self.get_public_url(user_id)
            logger.info(f"Uploaded avatar to S3: {key}")
            return url
        except (ClientError, BotoCoreError) as e:
            logger.error(f"S3 avatar upload failed: {e}")
            return None

    def delete(self, user_id: int) -> bool:
        """Delete a user's avatar from S3."""
        if not self.s3_client:
            logger.error("S3 client not available for avatar deletion")
            return False

        key = self._generate_key(user_id)

        try:
            self.s3_client.delete_object(Bucket=self.bucket, Key=key)
            logger.info(f"Deleted avatar from S3: {key}")
            return True
        except (ClientError, BotoCoreError) as e:
            logger.error(f"Failed to delete avatar {key}: {e}")
            return False
