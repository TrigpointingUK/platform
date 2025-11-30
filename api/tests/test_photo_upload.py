"""
Tests for photo upload endpoint.
"""

import io
from datetime import datetime
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from api.core.config import settings
from api.models.user import TLog, User


def seed_user_and_tlog(db: Session) -> tuple[User, TLog]:
    """Create a user and tlog with dynamic IDs to avoid collisions."""
    import uuid

    unique_name = f"uploaduser_{uuid.uuid4().hex[:6]}"
    user = User(
        name=unique_name,
        firstname="Upload",
        surname="User",
        email=f"{unique_name}@example.com",
        cryptpw="test",
        about="Photo upload tester",
        email_valid="Y",
        public_ind="Y",
        auth0_user_id=f"auth0|{uuid.uuid4().hex[:8]}",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    # Ensure Auth0 ID matches expected token pattern so auth succeeds
    user.auth0_user_id = f"auth0|{user.id}"  # type: ignore
    db.commit()
    db.refresh(user)

    tlog = TLog(
        trig_id=1,
        user_id=user.id,
        date=datetime(2023, 1, 1).date(),
        time=datetime(2023, 1, 1).time(),
        osgb_eastings=1,
        osgb_northings=1,
        osgb_gridref="AA 00000 00000",
        fb_number="",
        condition="G",
        comment="Test log for photo upload",
        score=0,
        ip_addr="127.0.0.1",
        source="W",
    )
    db.add(tlog)
    db.commit()
    db.refresh(tlog)
    return user, tlog


def create_test_image() -> io.BytesIO:
    """Create a valid JPEG image for testing using PIL."""
    from PIL import Image

    # Create a small test image
    img = Image.new("RGB", (100, 100), color="red")
    buffer = io.BytesIO()
    img.save(buffer, format="JPEG", quality=85)
    buffer.seek(0)
    return buffer


@patch("api.services.image_processor.ImageProcessor.process_image")
@patch("api.services.s3_service.S3Service.upload_photo_and_thumbnail")
def test_create_photo_with_user_facing_names_works(
    mock_s3_upload, mock_image_processor, client: TestClient, db: Session
):
    """
    Test that user-facing parameter names work correctly.
    This test demonstrates that the fix allows users to send 'caption' and 'license'.
    """
    # Mock the image processing and S3 upload
    mock_image_processor.return_value = (
        (100, 100),
        b"processed_image",
        (50, 50),
        b"thumbnail",
    )
    mock_s3_upload.return_value = ("photo_key", "thumb_key")

    user, tlog = seed_user_and_tlog(db)

    headers = {"Authorization": f"Bearer auth0_user_{user.id}"}

    # Create test image
    test_image = create_test_image()

    # Try using user-facing parameter names (this should work but currently fails)
    files = {"file": ("test.jpg", test_image, "image/jpeg")}
    data = {
        "caption": "Test Photo Caption",  # User-facing name
        "text_desc": "Test description",
        "type": "T",
        "license": "Y",  # User-facing name (not "licence")
    }

    resp = client.post(
        f"{settings.API_V1_STR}/photos/?log_id={tlog.id}",
        files=files,
        data=data,
        headers=headers,
    )

    # This should succeed but currently fails
    print(f"Response status: {resp.status_code}")
    print(f"Response body: {resp.json()}")

    # This should succeed now that the fix is in place
    assert (
        resp.status_code == 201
    ), f"Expected 201, got {resp.status_code}: {resp.json()}"

    body = resp.json()
    assert body["caption"] == "Test Photo Caption"
    assert body["text_desc"] == "Test description"
    assert body["type"] == "T"
    assert body["license"] == "Y"


@patch("api.services.image_processor.ImageProcessor.process_image")
@patch("api.services.s3_service.S3Service.upload_photo_and_thumbnail")
def test_create_photo_comprehensive_validation(
    mock_s3_upload, mock_image_processor, client: TestClient, db: Session
):
    """
    Test comprehensive validation of the photo upload endpoint.
    This verifies all parameter validation works correctly.
    """
    # Mock the image processing and S3 upload
    mock_image_processor.return_value = (
        (100, 100),
        b"processed_image",
        (50, 50),
        b"thumbnail",
    )
    mock_s3_upload.return_value = ("photo_key", "thumb_key")

    user, tlog = seed_user_and_tlog(db)

    headers = {"Authorization": f"Bearer auth0_user_{user.id}"}

    # Create test image
    test_image = create_test_image()

    # Use the correct user-facing parameter names
    files = {"file": ("test.jpg", test_image, "image/jpeg")}
    data = {
        "caption": "Test Photo Name",  # User-facing parameter name
        "text_desc": "Test description",
        "type": "T",
        "license": "Y",  # User-facing parameter name
    }

    resp = client.post(
        f"{settings.API_V1_STR}/photos/?log_id={tlog.id}",
        files=files,
        data=data,
        headers=headers,
    )

    # This should succeed
    assert resp.status_code == 201

    body = resp.json()
    assert body["caption"] == "Test Photo Name"
    assert body["text_desc"] == "Test description"
    assert body["type"] == "T"
    assert body["license"] == "Y"

    # Test validation errors for invalid values
    # Test invalid photo type
    data_invalid_type = data.copy()
    data_invalid_type["type"] = "X"  # Invalid type
    test_image_invalid = create_test_image()

    resp_invalid = client.post(
        f"{settings.API_V1_STR}/photos/?log_id={tlog.id}",
        files={"file": ("test.jpg", test_image_invalid, "image/jpeg")},
        data=data_invalid_type,
        headers=headers,
    )
    assert resp_invalid.status_code == 422  # Validation error

    # Test invalid license
    data_invalid_license = data.copy()
    data_invalid_license["license"] = "Z"  # Invalid license
    test_image_invalid2 = create_test_image()

    resp_invalid2 = client.post(
        f"{settings.API_V1_STR}/photos/?log_id={tlog.id}",
        files={"file": ("test.jpg", test_image_invalid2, "image/jpeg")},
        data=data_invalid_license,
        headers=headers,
    )
    assert resp_invalid2.status_code == 422  # Validation error
