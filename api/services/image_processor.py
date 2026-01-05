"""
Image processing service for photo uploads.
"""

import io
import logging
from typing import Optional, Tuple

from PIL import Image, ImageOps

from api.core.config import settings

logger = logging.getLogger(__name__)


class ImageProcessor:
    """Service for processing uploaded images."""

    def __init__(self):
        """Initialise the image processor."""
        pass

    def process_image(self, image_bytes: bytes) -> Tuple[
        Optional[bytes],
        Optional[bytes],
        Optional[Tuple[int, int]],
        Optional[Tuple[int, int]],
    ]:
        """
        Process uploaded image: resize, create thumbnail, apply EXIF orientation.

        Args:
            image_bytes: Raw image data

        Returns:
            Tuple of (processed_image_bytes, thumbnail_bytes, image_dimensions, thumbnail_dimensions)
        """
        try:
            # Open image and apply EXIF orientation
            with Image.open(io.BytesIO(image_bytes)) as img:
                # Apply EXIF orientation
                transposed = ImageOps.exif_transpose(img)
                if transposed is None:
                    return None, None, None, None

                # Get original dimensions
                original_width, original_height = transposed.size

                # Calculate new dimensions for main image (max 4000x4000, preserve aspect ratio)
                image_dimensions = self._calculate_dimensions(
                    original_width, original_height, settings.MAX_IMAGE_DIMENSION
                )

                # Resize main image
                if image_dimensions != (original_width, original_height):
                    processed = transposed.resize(
                        image_dimensions, Image.Resampling.LANCZOS
                    )
                else:
                    processed = transposed

                # Convert to RGB if necessary (strip EXIF and ensure compatibility)
                if processed.mode != "RGB":
                    processed = processed.convert("RGB")

                # Save processed image
                output = io.BytesIO()
                processed.save(output, format="JPEG", quality=95, optimize=True)
                processed_image_bytes = output.getvalue()

                # Calculate thumbnail dimensions (max 120x120, preserve aspect ratio)
                thumbnail_dimensions = self._calculate_dimensions(
                    original_width, original_height, settings.THUMBNAIL_SIZE
                )

                # Create thumbnail
                if thumbnail_dimensions != (original_width, original_height):
                    thumbnail = processed.resize(
                        thumbnail_dimensions, Image.Resampling.LANCZOS
                    )
                else:
                    thumbnail = processed.copy()

                # Save thumbnail
                thumbnail_output = io.BytesIO()
                thumbnail.save(
                    thumbnail_output, format="JPEG", quality=85, optimize=True
                )
                thumbnail_bytes = thumbnail_output.getvalue()

                logger.info(
                    f"Processed image: {original_width}x{original_height} -> "
                    f"{image_dimensions[0]}x{image_dimensions[1]}, "
                    f"thumbnail: {thumbnail_dimensions[0]}x{thumbnail_dimensions[1]}"
                )

                return (
                    processed_image_bytes,
                    thumbnail_bytes,
                    image_dimensions,
                    thumbnail_dimensions,
                )

        except Exception as e:
            logger.error(f"Failed to process image: {e}")
            return None, None, None, None

    def _calculate_dimensions(
        self, width: int, height: int, max_size: int
    ) -> Tuple[int, int]:
        """Calculate new dimensions preserving aspect ratio."""
        if width <= max_size and height <= max_size:
            return width, height

        aspect_ratio = width / height

        if width > height:
            new_width = min(width, max_size)
            new_height = int(new_width / aspect_ratio)
        else:
            new_height = min(height, max_size)
            new_width = int(new_height * aspect_ratio)

        # Ensure neither dimension exceeds max_size
        new_width = min(new_width, max_size)
        new_height = min(new_height, max_size)

        return new_width, new_height

    def validate_image(self, image_bytes: bytes) -> Tuple[bool, str]:
        """
        Validate uploaded image file.

        Accepts JPEG and JPEG-based formats (including MPO from iPhones).
        All images are converted to standard JPEG during processing.
        """
        try:
            # Check file size first (before loading)
            if len(image_bytes) > settings.MAX_IMAGE_SIZE:
                return (
                    False,
                    f"File size exceeds maximum of {settings.MAX_IMAGE_SIZE // (1024 * 1024)}MB",
                )

            # Check for JPEG magic bytes at start of file
            # JPEG files start with FF D8 FF
            # This includes:
            # - Standard JPEG/JPG files
            # - MPO files (Multi-Picture Object, used by iPhones with depth data)
            # - JFIF files (JPEG File Interchange Format)
            if len(image_bytes) < 3:
                return False, "File is too small to be a valid image"

            if not (
                image_bytes[0] == 0xFF
                and image_bytes[1] == 0xD8
                and image_bytes[2] == 0xFF
            ):
                return False, "Only JPEG images are supported"

            # Try to open and validate the image with PIL
            with Image.open(io.BytesIO(image_bytes)) as img:
                # Load the image data to ensure it's valid
                # This will raise an exception if the image is corrupted
                img.load()

                # Verify we can get basic properties
                _ = img.size
                _ = img.mode

                logger.info(
                    f"Image validated: {img.size}, format={img.format}, mode={img.mode}"
                )

            return True, "Image is valid"

        except Exception as e:
            logger.error(f"Image validation failed: {e}")
            return False, f"Invalid image file: {str(e)}"
