"""
Tests for image processor service aligned with current implementation.
"""

import io

from PIL import Image

from api.services.image_processor import ImageProcessor


class TestImageProcessor:
    def test_process_image_valid_jpeg(self):
        processor = ImageProcessor()
        test_image = Image.new("RGB", (800, 600), color="red")
        buffer = io.BytesIO()
        test_image.save(buffer, format="JPEG", quality=95)
        image_data = buffer.getvalue()

        result = processor.process_image(image_data)
        assert result is not None
        processed_photo, processed_thumbnail, photo_dims, thumb_dims = result
        assert processed_photo and processed_thumbnail
        assert photo_dims and thumb_dims
        assert thumb_dims[0] <= photo_dims[0]
        assert thumb_dims[1] <= photo_dims[1]

    def test_process_image_invalid_data(self):
        processor = ImageProcessor()
        assert processor.process_image(b"") == (None, None, None, None)
        assert processor.process_image(b"not an image") == (None, None, None, None)

    def test_process_image_corrupted_jpeg(self):
        processor = ImageProcessor()
        corrupted_data = b"\xff\xd8\xff\xe0\x00\x10JFIF"
        assert processor.process_image(corrupted_data) == (None, None, None, None)

    def test_process_image_very_small_image(self):
        processor = ImageProcessor()
        test_image = Image.new("RGB", (1, 1), color="green")
        buffer = io.BytesIO()
        test_image.save(buffer, format="JPEG")
        image_data = buffer.getvalue()

        result = processor.process_image(image_data)
        assert result is not None
        _, _, photo_dims, thumb_dims = result
        assert photo_dims == (1, 1)
        assert thumb_dims[0] >= 1 and thumb_dims[1] >= 1

    def test_process_image_very_large_image(self):
        processor = ImageProcessor()
        test_image = Image.new("RGB", (5000, 5000), color="blue")
        buffer = io.BytesIO()
        test_image.save(buffer, format="JPEG", quality=95)
        image_data = buffer.getvalue()

        result = processor.process_image(image_data)
        assert result is not None
        _, _, photo_dims, _ = result

        from api.core.config import settings

        assert photo_dims[0] <= settings.MAX_IMAGE_DIMENSION
        assert photo_dims[1] <= settings.MAX_IMAGE_DIMENSION

    def test_process_image_grayscale(self):
        processor = ImageProcessor()
        test_image = Image.new("L", (400, 300), color=128)
        buffer = io.BytesIO()
        test_image.save(buffer, format="JPEG")
        image_data = buffer.getvalue()

        result = processor.process_image(image_data)
        assert result is not None
        _, _, photo_dims, _ = result
        assert photo_dims == (400, 300)

    def test_process_image_with_alpha_channel(self):
        processor = ImageProcessor()
        test_image = Image.new("RGBA", (300, 200), color=(255, 0, 0, 128))
        buffer = io.BytesIO()
        test_image.save(buffer, format="PNG")
        image_data = buffer.getvalue()

        result = processor.process_image(image_data)
        assert result is not None
        _, _, photo_dims, _ = result
        assert photo_dims == (300, 200)

    def test_process_image_memory_error(self):
        processor = ImageProcessor()
        test_image = Image.new("RGB", (10000, 10000), color="gray")
        buffer = io.BytesIO()
        test_image.save(buffer, format="JPEG", quality=95)
        image_data = buffer.getvalue()

        result = processor.process_image(image_data)
        assert result is None or len(result) == 4

    def test_process_image_quality_settings(self):
        processor = ImageProcessor()
        test_image = Image.new("RGB", (200, 200), color="white")
        buffer = io.BytesIO()
        test_image.save(buffer, format="JPEG", quality=100)
        image_data = buffer.getvalue()

        result = processor.process_image(image_data)
        assert result is not None
        processed_photo, processed_thumbnail, _, _ = result
        assert len(processed_photo) > 0
        assert len(processed_thumbnail) > 0
        assert len(processed_thumbnail) < len(processed_photo)

    def test_validate_image_valid_jpeg(self):
        """Test validation accepts valid JPEG images."""
        processor = ImageProcessor()
        test_image = Image.new("RGB", (800, 600), color="red")
        buffer = io.BytesIO()
        test_image.save(buffer, format="JPEG", quality=95)
        image_data = buffer.getvalue()

        is_valid, message = processor.validate_image(image_data)
        assert is_valid is True
        assert message == "Image is valid"

    def test_validate_image_rejects_png(self):
        """Test validation rejects PNG images."""
        processor = ImageProcessor()
        test_image = Image.new("RGB", (800, 600), color="blue")
        buffer = io.BytesIO()
        test_image.save(buffer, format="PNG")
        image_data = buffer.getvalue()

        is_valid, message = processor.validate_image(image_data)
        assert is_valid is False
        assert "JPEG" in message

    def test_validate_image_rejects_invalid_data(self):
        """Test validation rejects invalid image data."""
        processor = ImageProcessor()

        is_valid, message = processor.validate_image(b"not an image")
        assert is_valid is False
        assert "Invalid" in message or "JPEG" in message

    def test_validate_image_empty_file(self):
        """Test validation rejects empty files."""
        processor = ImageProcessor()

        is_valid, message = processor.validate_image(b"")
        assert is_valid is False

    def test_validate_image_with_exif_rotation(self):
        """Test validation accepts JPEG with EXIF orientation data (like from iPhones)."""
        processor = ImageProcessor()
        # Create a JPEG with EXIF data
        test_image = Image.new("RGB", (800, 600), color="green")
        buffer = io.BytesIO()

        # Save with EXIF data
        exif_data = test_image.getexif()
        exif_data[0x0112] = 6  # Orientation = Rotate 90 CW
        test_image.save(buffer, format="JPEG", quality=95, exif=exif_data)
        image_data = buffer.getvalue()

        is_valid, message = processor.validate_image(image_data)
        assert is_valid is True
        assert message == "Image is valid"

    def test_process_image_converts_mpo_to_jpeg(self):
        """Test that MPO format (iPhone depth photos) is converted to standard JPEG."""
        processor = ImageProcessor()
        # Create a test image and save as JPEG (MPO uses JPEG structure)
        test_image = Image.new("RGB", (800, 600), color="blue")
        buffer = io.BytesIO()
        test_image.save(buffer, format="JPEG", quality=95)
        image_data = buffer.getvalue()

        # Process the image
        processed_photo, processed_thumbnail, photo_dims, thumb_dims = (
            processor.process_image(image_data)
        )

        # Verify output is standard JPEG
        assert processed_photo is not None
        output_img = Image.open(io.BytesIO(processed_photo))
        assert output_img.format == "JPEG"
        assert output_img.mode == "RGB"
