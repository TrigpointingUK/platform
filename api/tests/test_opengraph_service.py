"""
Tests for the Open Graph image generation and caching service.
"""

import io
from datetime import date, datetime, timedelta, timezone
from unittest.mock import Mock, patch

from PIL import Image
from sqlalchemy.orm import Session

from api.models import TLog, TPhoto
from api.services.opengraph_service import (
    HEIGHT,
    WIDTH,
    OpenGraphService,
    _crop_center_square,
    _draw_gradient,
    _load_font,
    _make_circular,
    _round_corners,
    _select_photos_for_log,
    _select_photos_for_trig,
)


class TestHelpers:
    """Test low-level image composition helpers."""

    def test_draw_gradient(self):
        img = Image.new("RGBA", (WIDTH, HEIGHT))
        _draw_gradient(img)
        pixel = img.getpixel((0, 0))
        assert pixel[0] < 30
        assert pixel[2] > 40

    def test_load_font_returns_font(self):
        font = _load_font(24)
        assert font is not None

    def test_load_font_bold(self):
        font = _load_font(24, bold=True)
        assert font is not None

    def test_crop_center_square_landscape(self):
        img = Image.new("RGB", (200, 100))
        result = _crop_center_square(img)
        assert result.size == (100, 100)

    def test_crop_center_square_portrait(self):
        img = Image.new("RGB", (100, 200))
        result = _crop_center_square(img)
        assert result.size == (100, 100)

    def test_crop_center_square_already_square(self):
        img = Image.new("RGB", (100, 100))
        result = _crop_center_square(img)
        assert result.size == (100, 100)

    def test_round_corners(self):
        img = Image.new("RGBA", (100, 100), (255, 0, 0, 255))
        result = _round_corners(img, 10)
        assert result.mode == "RGBA"
        corner = result.getpixel((0, 0))
        assert corner[3] == 0

    def test_make_circular(self):
        img = Image.new("RGB", (200, 100), (255, 0, 0))
        result = _make_circular(img)
        assert result.mode == "RGBA"
        assert result.size[0] == result.size[1]
        corner = result.getpixel((0, 0))
        assert corner[3] == 0


class TestPhotoSelection:
    """Test photo selection logic."""

    def _make_photo(self, photo_id: int, ptype: str, tlog_id: int = 1) -> Mock:
        p = Mock(spec=TPhoto)
        p.id = photo_id
        p.type = ptype
        p.tlog_id = tlog_id
        p.deleted_ind = "N"
        p.public_ind = "Y"
        p.crt_timestamp = datetime.now()
        return p

    def test_select_photos_for_trig_prefers_variety(self):
        photos = [
            self._make_photo(1, "T"),
            self._make_photo(2, "T"),
            self._make_photo(3, "F"),
            self._make_photo(4, "L"),
            self._make_photo(5, "O"),
            self._make_photo(6, "P"),
        ]
        mock_db = Mock(spec=Session)
        query = Mock()
        query.join.return_value = query
        query.filter.return_value = query
        query.order_by.return_value = query
        query.limit.return_value = query
        query.all.return_value = photos
        mock_db.query.return_value = query

        result = _select_photos_for_trig(mock_db, trig_id=1, limit=4)
        types = [p.type for p in result]
        assert "T" in types
        assert "F" in types
        assert len(result) == 4

    def test_select_photos_for_log_prioritises_own(self):
        log_photos = [
            self._make_photo(10, "T", tlog_id=5),
            self._make_photo(11, "L", tlog_id=5),
        ]
        trig_photos = [
            self._make_photo(1, "T"),
            self._make_photo(2, "F"),
            self._make_photo(3, "L"),
        ]

        mock_db = Mock(spec=Session)
        mock_log = Mock(spec=TLog)
        mock_log.id = 5
        mock_log.trig_id = 1

        log_query = Mock()
        log_query.filter.return_value = log_query
        log_query.order_by.return_value = log_query
        log_query.all.return_value = log_photos

        trig_query = Mock()
        trig_query.join.return_value = trig_query
        trig_query.filter.return_value = trig_query
        trig_query.order_by.return_value = trig_query
        trig_query.limit.return_value = trig_query
        trig_query.all.return_value = trig_photos

        mock_db.query.side_effect = [log_query, trig_query]

        result = _select_photos_for_log(mock_db, mock_log, trig_id=1, limit=4)
        assert result[0].id == 10
        assert result[1].id == 11
        assert len(result) == 4


class TestOpenGraphService:
    """Test the OpenGraphService class."""

    @patch("api.services.opengraph_service.boto3")
    def test_init(self, mock_boto3):
        svc = OpenGraphService()
        assert svc.bucket == "trigpointinguk-opengraph"

    @patch("api.services.opengraph_service.boto3")
    def test_s3_key(self, mock_boto3):
        svc = OpenGraphService()
        assert svc._s3_key("trigs", 123) == "trigs/123.png"
        assert svc._s3_key("logs", 456) == "logs/456.png"

    @patch("api.services.opengraph_service.boto3")
    def test_get_image_url(self, mock_boto3):
        svc = OpenGraphService()
        url = svc.get_image_url("trigs", 123)
        assert "trigpointinguk-opengraph" in url
        assert "trigs/123.png" in url

    @patch("api.services.opengraph_service.boto3")
    def test_check_image_fresh_exists(self, mock_boto3):
        mock_client = Mock()
        mock_client.head_object.return_value = {
            "LastModified": datetime.now(timezone.utc) - timedelta(hours=1)
        }
        mock_boto3.client.return_value = mock_client

        svc = OpenGraphService()
        assert svc.check_image_fresh("trigs", 123) is True

    @patch("api.services.opengraph_service.boto3")
    def test_check_image_fresh_stale(self, mock_boto3):
        mock_client = Mock()
        mock_client.head_object.return_value = {
            "LastModified": datetime.now(timezone.utc) - timedelta(days=30)
        }
        mock_boto3.client.return_value = mock_client

        svc = OpenGraphService()
        assert svc.check_image_fresh("trigs", 123) is False

    @patch("api.services.opengraph_service.boto3")
    def test_check_image_fresh_not_found(self, mock_boto3):
        from botocore.exceptions import ClientError

        mock_client = Mock()
        mock_client.head_object.side_effect = ClientError(
            {"Error": {"Code": "404", "Message": "Not found"}}, "HeadObject"
        )
        mock_boto3.client.return_value = mock_client

        svc = OpenGraphService()
        assert svc.check_image_fresh("trigs", 123) is False

    @patch("api.services.opengraph_service.boto3")
    def test_upload_image(self, mock_boto3):
        mock_client = Mock()
        mock_boto3.client.return_value = mock_client

        svc = OpenGraphService()
        url = svc.upload_image("trigs", 123, b"fake-png-data")
        assert "trigs/123.png" in url
        mock_client.put_object.assert_called_once()
        call_kwargs = mock_client.put_object.call_args[1]
        assert call_kwargs["ACL"] == "public-read"
        assert call_kwargs["ContentType"] == "image/png"

    @patch("api.services.opengraph_service._download_photo")
    @patch("api.services.opengraph_service._select_photos_for_trig")
    @patch("api.services.opengraph_service.boto3")
    def test_generate_trig_image(self, mock_boto3, mock_select, mock_download):
        mock_select.return_value = []
        mock_download.return_value = None

        mock_trig = Mock()
        mock_trig.id = 1
        mock_trig.name = "Test Hill"
        mock_trig.waypoint = "TP0001"
        mock_trig.osgb_gridref = "TQ123456"
        mock_trig.osgb_height = 100.0
        mock_trig.wgs_lat = 51.5
        mock_trig.wgs_long = -0.1
        mock_trig.type_name = "Pillar"
        mock_trig.condition = "G"
        mock_trig.fb_number = "S5432"
        mock_trig.stn_number = ""
        mock_trig.stn_number_active = "12345"
        mock_trig.stn_number_passive = ""
        mock_trig.stn_number_osgb36 = ""

        mock_db = Mock(spec=Session)

        svc = OpenGraphService()
        img_bytes = svc._generate_trig_image(mock_trig, mock_db)

        assert len(img_bytes) > 0
        img = Image.open(io.BytesIO(img_bytes))
        assert img.size == (WIDTH, HEIGHT)
        assert img.mode == "RGB"

    @patch("api.services.opengraph_service._download_avatar")
    @patch("api.services.opengraph_service._download_photo")
    @patch("api.services.opengraph_service._select_photos_for_log")
    @patch("api.services.opengraph_service.boto3")
    def test_generate_log_image(
        self, mock_boto3, mock_select, mock_download_photo, mock_download_avatar
    ):
        mock_select.return_value = []
        mock_download_photo.return_value = None
        mock_download_avatar.return_value = None

        mock_trig = Mock()
        mock_trig.id = 1
        mock_trig.name = "Test Hill"
        mock_trig.waypoint = "TP0001"
        mock_trig.osgb_gridref = "TQ123456"
        mock_trig.osgb_height = 100.0
        mock_trig.wgs_lat = 51.5
        mock_trig.wgs_long = -0.1
        mock_trig.fb_number = "S5432"
        mock_trig.stn_number = ""
        mock_trig.stn_number_active = ""
        mock_trig.stn_number_passive = "P98765"
        mock_trig.stn_number_osgb36 = ""

        mock_log = Mock()
        mock_log.id = 42
        mock_log.trig_id = 1
        mock_log.user_id = 7
        mock_log.date = date(2024, 3, 15)
        mock_log.condition = "G"

        mock_user = Mock()
        mock_user.id = 7
        mock_user.name = "TestUser"

        mock_db = Mock(spec=Session)

        svc = OpenGraphService()
        img_bytes = svc._generate_log_image(mock_log, mock_trig, mock_user, mock_db)

        assert len(img_bytes) > 0
        img = Image.open(io.BytesIO(img_bytes))
        assert img.size == (WIDTH, HEIGHT)


class TestOgHtml:
    """Test OG HTML generation."""

    @patch("api.services.opengraph_service.boto3")
    def test_generate_og_html_contains_meta_tags(self, mock_boto3):
        svc = OpenGraphService()
        html = svc.generate_og_html(
            title="TP0001 - Test Hill",
            description="Trigpoint at TQ123456, 100m",
            image_url="https://example.com/image.png",
            canonical_url="https://trigpointing.uk/trigs/1",
        )
        assert "og:title" in html
        assert "og:description" in html
        assert "og:image" in html
        assert "og:url" in html
        assert "twitter:card" in html
        assert "summary_large_image" in html
        assert "TP0001 - Test Hill" in html
        assert "https://example.com/image.png" in html
        assert "https://trigpointing.uk/trigs/1" in html

    @patch("api.services.opengraph_service.boto3")
    def test_generate_og_html_escapes_html(self, mock_boto3):
        svc = OpenGraphService()
        html = svc.generate_og_html(
            title='Test <script>alert("xss")</script>',
            description="A & B",
            image_url="https://example.com/img.png",
            canonical_url="https://example.com",
        )
        assert 'content="Test &lt;script&gt;' in html
        assert "&amp;" in html

    @patch("api.services.opengraph_service.boto3")
    def test_generate_og_html_contains_redirect(self, mock_boto3):
        svc = OpenGraphService()
        html = svc.generate_og_html(
            title="Test",
            description="Desc",
            image_url="https://example.com/img.png",
            canonical_url="https://trigpointing.uk/trigs/1",
        )
        assert 'http-equiv="refresh"' in html
        assert "window.location.replace" in html
