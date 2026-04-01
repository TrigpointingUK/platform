"""
Tests for the Open Graph image generation and caching service.
"""

import io
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from botocore.exceptions import ClientError
from PIL import Image
from sqlalchemy.orm import Session

from api.services.opengraph_service import (
    HEIGHT,
    PADDING,
    WIDTH,
    OpenGraphService,
    _add_drop_shadow,
    _compose_photo_strip,
    _crop_center_square,
    _draw_gradient,
    _draw_uk_map,
    _get_station_number,
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

    def test_draw_gradient_bottom_brighter(self):
        img = Image.new("RGBA", (WIDTH, HEIGHT))
        _draw_gradient(img)
        top = img.getpixel((0, 0))
        bottom = img.getpixel((0, HEIGHT - 1))
        assert bottom[0] > top[0]
        assert bottom[1] > top[1]

    def test_load_font_returns_font(self):
        font = _load_font(24)
        assert font is not None

    def test_load_font_bold(self):
        font = _load_font(24, bold=True)
        assert font is not None

    def test_load_font_different_sizes(self):
        small = _load_font(12)
        large = _load_font(48)
        assert small is not None
        assert large is not None

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

    def test_round_corners_center_opaque(self):
        img = Image.new("RGBA", (100, 100), (255, 0, 0, 255))
        result = _round_corners(img, 10)
        center = result.getpixel((50, 50))
        assert center[3] == 255

    def test_make_circular(self):
        img = Image.new("RGB", (200, 100), (255, 0, 0))
        result = _make_circular(img)
        assert result.mode == "RGBA"
        assert result.size[0] == result.size[1]
        corner = result.getpixel((0, 0))
        assert corner[3] == 0

    def test_make_circular_center_opaque(self):
        img = Image.new("RGB", (100, 100), (255, 0, 0))
        result = _make_circular(img)
        cx, cy = result.size[0] // 2, result.size[1] // 2
        center = result.getpixel((cx, cy))
        assert center[3] == 255

    def test_add_drop_shadow_larger_canvas(self):
        img = Image.new("RGBA", (100, 100), (255, 0, 0, 255))
        result = _add_drop_shadow(img, offset=4, blur_radius=8)
        assert result.size[0] > 100
        assert result.size[1] > 100
        assert result.mode == "RGBA"

    def test_add_drop_shadow_preserves_content(self):
        img = Image.new("RGBA", (50, 50), (0, 255, 0, 255))
        result = _add_drop_shadow(img, offset=2, blur_radius=4)
        px = result.getpixel((4, 4))
        assert px[1] == 255

    def test_compose_photo_strip_empty(self):
        canvas = Image.new("RGBA", (WIDTH, HEIGHT))
        _compose_photo_strip(canvas, [], 300)

    def test_compose_photo_strip_single(self):
        canvas = Image.new("RGBA", (WIDTH, HEIGHT))
        photo = Image.new("RGB", (400, 300), (255, 0, 0))
        _compose_photo_strip(canvas, [photo], 300)
        px = canvas.getpixel((PADDING + 10, 310))
        assert px[0] > 200

    def test_compose_photo_strip_multiple(self):
        canvas = Image.new("RGBA", (WIDTH, HEIGHT))
        photos = [
            Image.new("RGB", (400, 300), (255, 0, 0)),
            Image.new("RGB", (400, 300), (0, 255, 0)),
            Image.new("RGB", (400, 300), (0, 0, 255)),
        ]
        _compose_photo_strip(canvas, photos, 300)


class TestGetStationNumber:
    """Test _get_station_number priority logic."""

    def _make_trig(self, **kwargs):
        trig = Mock()
        trig.stn_number_active = kwargs.get("active", "")
        trig.stn_number_passive = kwargs.get("passive", "")
        trig.stn_number_osgb36 = kwargs.get("osgb36", "")
        trig.stn_number = kwargs.get("stn", "")
        return trig

    def test_prefers_active(self):
        trig = self._make_trig(active="A1", passive="P1", stn="S1")
        assert _get_station_number(trig) == "A1"

    def test_falls_back_to_passive(self):
        trig = self._make_trig(passive="P1", stn="S1")
        assert _get_station_number(trig) == "P1"

    def test_falls_back_to_osgb36(self):
        trig = self._make_trig(osgb36="O1")
        assert _get_station_number(trig) == "O1"

    def test_falls_back_to_stn_number(self):
        trig = self._make_trig(stn="S1")
        assert _get_station_number(trig) == "S1"

    def test_returns_empty_when_none(self):
        trig = self._make_trig()
        assert _get_station_number(trig) == ""

    def test_strips_whitespace(self):
        trig = self._make_trig(active="  A1  ")
        assert _get_station_number(trig) == "A1"

    def test_skips_blank_active(self):
        trig = self._make_trig(active="   ", passive="P1")
        assert _get_station_number(trig) == "P1"


class TestDrawUkMap:
    """Test _draw_uk_map returns a valid image."""

    def test_returns_placeholder_when_files_missing(self):
        trig = Mock()
        trig.wgs_lat = 51.5
        trig.wgs_long = -0.1
        with patch(
            "api.services.opengraph_service._find_res_dir",
            return_value=Path("/nonexistent"),
        ):
            result = _draw_uk_map(trig)
        assert result.size == (200, 200)
        assert result.mode == "RGBA"

    def test_returns_image_with_res_files(self):
        trig = Mock()
        trig.wgs_lat = 51.5
        trig.wgs_long = -0.1
        result = _draw_uk_map(trig)
        assert result.mode == "RGBA"
        assert max(result.size) == 200


class TestLoadConditionIcon:
    """Test _load_condition_icon."""

    def test_returns_none_when_condition_not_found(self):
        from api.services.opengraph_service import _load_condition_icon

        mock_db = Mock(spec=Session)
        query = Mock()
        query.filter.return_value = query
        query.first.return_value = None
        mock_db.query.return_value = query
        assert _load_condition_icon("X", mock_db) is None

    def test_returns_none_when_no_icon_file(self):
        from api.services.opengraph_service import _load_condition_icon

        mock_db = Mock(spec=Session)
        cond = Mock()
        cond.icon_file = None
        query = Mock()
        query.filter.return_value = query
        query.first.return_value = cond
        mock_db.query.return_value = query
        assert _load_condition_icon("G", mock_db) is None


class TestPhotoSelection:
    """Test photo selection logic."""

    def _make_photo(self, photo_id: int, ptype: str, tlog_id: int = 1) -> Mock:
        p = Mock()
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

    def test_select_photos_for_trig_respects_limit(self):
        photos = [self._make_photo(i, "T") for i in range(10)]
        mock_db = Mock(spec=Session)
        query = Mock()
        query.join.return_value = query
        query.filter.return_value = query
        query.order_by.return_value = query
        query.limit.return_value = query
        query.all.return_value = photos
        mock_db.query.return_value = query

        result = _select_photos_for_trig(mock_db, trig_id=1, limit=3)
        assert len(result) == 3

    def test_select_photos_for_trig_fewer_than_limit(self):
        photos = [self._make_photo(1, "T")]
        mock_db = Mock(spec=Session)
        query = Mock()
        query.join.return_value = query
        query.filter.return_value = query
        query.order_by.return_value = query
        query.limit.return_value = query
        query.all.return_value = photos
        mock_db.query.return_value = query

        result = _select_photos_for_trig(mock_db, trig_id=1, limit=4)
        assert len(result) == 1

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
        mock_log = Mock()
        mock_log.id = 5
        mock_log.trig_id = 1
        mock_log.user_id = None

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

    def test_select_photos_for_log_enough_from_log(self):
        log_photos = [self._make_photo(i, "T", tlog_id=5) for i in range(4)]

        mock_db = Mock(spec=Session)
        mock_log = Mock()
        mock_log.id = 5
        mock_log.trig_id = 1
        mock_log.user_id = None

        log_query = Mock()
        log_query.filter.return_value = log_query
        log_query.order_by.return_value = log_query
        log_query.all.return_value = log_photos

        mock_db.query.return_value = log_query

        result = _select_photos_for_log(mock_db, mock_log, trig_id=1, limit=4)
        assert len(result) == 4

    def test_select_photos_for_log_includes_user_photos(self):
        log_photos = [self._make_photo(10, "T", tlog_id=5)]
        user_photos = [
            self._make_photo(20, "F", tlog_id=6),
            self._make_photo(21, "L", tlog_id=6),
        ]
        trig_photos = [self._make_photo(30, "O")]

        mock_db = Mock(spec=Session)
        mock_log = Mock()
        mock_log.id = 5
        mock_log.trig_id = 1
        mock_log.user_id = 7

        call_count = [0]

        def side_effect(*args, **kwargs):
            call_count[0] += 1
            q = Mock()
            q.join.return_value = q
            q.filter.return_value = q
            q.order_by.return_value = q
            q.limit.return_value = q
            if call_count[0] == 1:
                q.all.return_value = log_photos
            elif call_count[0] == 2:
                q.all.return_value = user_photos
            else:
                q.all.return_value = trig_photos
            return q

        mock_db.query.side_effect = side_effect

        result = _select_photos_for_log(mock_db, mock_log, trig_id=1, limit=4)
        assert result[0].id == 10
        assert len(result) >= 3


class TestOpenGraphService:
    """Test the OpenGraphService class."""

    @patch("api.services.opengraph_service.boto3")
    def test_init(self, mock_boto3):
        svc = OpenGraphService()
        assert svc.bucket == "trigpointinguk-opengraph"

    @patch("api.services.opengraph_service.boto3")
    def test_init_s3_failure(self, mock_boto3):
        mock_boto3.client.side_effect = Exception("boom")
        svc = OpenGraphService()
        assert svc.s3_client is None

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
        mock_client = Mock()
        mock_client.head_object.side_effect = ClientError(
            {"Error": {"Code": "404", "Message": "Not found"}}, "HeadObject"
        )
        mock_boto3.client.return_value = mock_client

        svc = OpenGraphService()
        assert svc.check_image_fresh("trigs", 123) is False

    @patch("api.services.opengraph_service.boto3")
    def test_check_image_fresh_other_error(self, mock_boto3):
        mock_client = Mock()
        mock_client.head_object.side_effect = ClientError(
            {"Error": {"Code": "403", "Message": "Forbidden"}}, "HeadObject"
        )
        mock_boto3.client.return_value = mock_client

        svc = OpenGraphService()
        assert svc.check_image_fresh("trigs", 123) is False

    @patch("api.services.opengraph_service.boto3")
    def test_check_image_fresh_no_client(self, mock_boto3):
        mock_boto3.client.side_effect = Exception("boom")
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

    @patch("api.services.opengraph_service.boto3")
    def test_delete_image(self, mock_boto3):
        mock_client = Mock()
        mock_boto3.client.return_value = mock_client

        svc = OpenGraphService()
        svc.delete_image("trigs", 123)
        mock_client.delete_object.assert_called_once()

    @patch("api.services.opengraph_service.boto3")
    def test_delete_image_no_client(self, mock_boto3):
        mock_boto3.client.side_effect = Exception("boom")
        svc = OpenGraphService()
        svc.delete_image("trigs", 123)

    @patch("api.services.opengraph_service.boto3")
    def test_delete_image_s3_error(self, mock_boto3):
        mock_client = Mock()
        mock_client.delete_object.side_effect = ClientError(
            {"Error": {"Code": "500", "Message": "Oops"}}, "DeleteObject"
        )
        mock_boto3.client.return_value = mock_client

        svc = OpenGraphService()
        svc.delete_image("trigs", 123)

    @patch("api.services.opengraph_service.boto3")
    def test_get_or_create_trig_image_fresh(self, mock_boto3):
        mock_client = Mock()
        mock_client.head_object.return_value = {
            "LastModified": datetime.now(timezone.utc) - timedelta(hours=1)
        }
        mock_boto3.client.return_value = mock_client

        svc = OpenGraphService()
        mock_db = Mock(spec=Session)
        url = svc.get_or_create_trig_image(123, mock_db)
        assert "trigs/123.png" in url
        mock_db.query.assert_not_called()

    @patch("api.services.opengraph_service.boto3")
    def test_get_or_create_trig_image_not_found(self, mock_boto3):
        mock_client = Mock()
        mock_client.head_object.side_effect = ClientError(
            {"Error": {"Code": "404", "Message": "Not found"}}, "HeadObject"
        )
        mock_boto3.client.return_value = mock_client

        svc = OpenGraphService()
        mock_db = Mock(spec=Session)
        query = Mock()
        query.filter.return_value = query
        query.first.return_value = None
        mock_db.query.return_value = query

        with pytest.raises(ValueError, match="Trig 999 not found"):
            svc.get_or_create_trig_image(999, mock_db)

    @patch("api.services.opengraph_service.boto3")
    def test_get_or_create_log_image_fresh(self, mock_boto3):
        mock_client = Mock()
        mock_client.head_object.return_value = {
            "LastModified": datetime.now(timezone.utc) - timedelta(hours=1)
        }
        mock_boto3.client.return_value = mock_client

        svc = OpenGraphService()
        mock_db = Mock(spec=Session)
        url = svc.get_or_create_log_image(42, mock_db)
        assert "logs/42.png" in url
        mock_db.query.assert_not_called()

    @patch("api.services.opengraph_service.boto3")
    def test_get_or_create_log_image_not_found(self, mock_boto3):
        mock_client = Mock()
        mock_client.head_object.side_effect = ClientError(
            {"Error": {"Code": "404", "Message": "Not found"}}, "HeadObject"
        )
        mock_boto3.client.return_value = mock_client

        svc = OpenGraphService()
        mock_db = Mock(spec=Session)
        query = Mock()
        query.filter.return_value = query
        query.first.return_value = None
        mock_db.query.return_value = query

        with pytest.raises(ValueError, match="Log 999 not found"):
            svc.get_or_create_log_image(999, mock_db)

    @patch("api.services.opengraph_service._fetch_os_map_tile")
    @patch("api.services.opengraph_service._download_photo")
    @patch("api.services.opengraph_service._select_photos_for_trig")
    @patch("api.services.opengraph_service.boto3")
    def test_generate_trig_image(
        self, mock_boto3, mock_select, mock_download, mock_os_tile
    ):
        mock_select.return_value = []
        mock_download.return_value = None
        mock_os_tile.return_value = None

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

    @patch("api.services.opengraph_service._fetch_os_map_tile")
    @patch("api.services.opengraph_service._download_photo")
    @patch("api.services.opengraph_service._select_photos_for_trig")
    @patch("api.services.opengraph_service.boto3")
    def test_generate_trig_image_no_optional_fields(
        self, mock_boto3, mock_select, mock_download, mock_os_tile
    ):
        mock_select.return_value = []
        mock_download.return_value = None
        mock_os_tile.return_value = None

        mock_trig = Mock()
        mock_trig.id = 2
        mock_trig.name = "Bare Trig"
        mock_trig.waypoint = "TP0002"
        mock_trig.osgb_gridref = "SU000000"
        mock_trig.osgb_height = None
        mock_trig.wgs_lat = 52.0
        mock_trig.wgs_long = -1.0
        mock_trig.type_name = None
        mock_trig.condition = None
        mock_trig.fb_number = None
        mock_trig.stn_number = None
        mock_trig.stn_number_active = None
        mock_trig.stn_number_passive = None
        mock_trig.stn_number_osgb36 = None

        mock_db = Mock(spec=Session)

        svc = OpenGraphService()
        img_bytes = svc._generate_trig_image(mock_trig, mock_db)
        img = Image.open(io.BytesIO(img_bytes))
        assert img.size == (WIDTH, HEIGHT)

    @patch("api.services.opengraph_service._fetch_os_map_tile")
    @patch("api.services.opengraph_service._download_photo")
    @patch("api.services.opengraph_service._select_photos_for_trig")
    @patch("api.services.opengraph_service.boto3")
    def test_generate_trig_image_with_photos(
        self, mock_boto3, mock_select, mock_download, mock_os_tile
    ):
        mock_photo = Mock()
        mock_select.return_value = [mock_photo]
        mock_download.return_value = Image.new("RGB", (400, 300), (128, 128, 128))
        mock_os_tile.return_value = Image.new("RGB", (400, 400), (200, 200, 200))

        mock_trig = Mock()
        mock_trig.id = 3
        mock_trig.name = "Photo Hill"
        mock_trig.waypoint = "TP0003"
        mock_trig.osgb_gridref = "ST111222"
        mock_trig.osgb_height = 55.123
        mock_trig.wgs_lat = 51.0
        mock_trig.wgs_long = -2.0
        mock_trig.type_name = "Pillar"
        mock_trig.condition = "G"
        mock_trig.fb_number = ""
        mock_trig.stn_number = ""
        mock_trig.stn_number_active = ""
        mock_trig.stn_number_passive = ""
        mock_trig.stn_number_osgb36 = ""

        mock_db = Mock(spec=Session)

        svc = OpenGraphService()
        img_bytes = svc._generate_trig_image(mock_trig, mock_db)
        img = Image.open(io.BytesIO(img_bytes))
        assert img.size == (WIDTH, HEIGHT)

    @patch("api.services.opengraph_service._fetch_os_map_tile")
    @patch("api.services.opengraph_service._download_avatar")
    @patch("api.services.opengraph_service._download_photo")
    @patch("api.services.opengraph_service._select_photos_for_log")
    @patch("api.services.opengraph_service.boto3")
    def test_generate_log_image(
        self,
        mock_boto3,
        mock_select,
        mock_download_photo,
        mock_download_avatar,
        mock_os_tile,
    ):
        mock_select.return_value = []
        mock_download_photo.return_value = None
        mock_download_avatar.return_value = None
        mock_os_tile.return_value = None

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

    @patch("api.services.opengraph_service._fetch_os_map_tile")
    @patch("api.services.opengraph_service._download_avatar")
    @patch("api.services.opengraph_service._download_photo")
    @patch("api.services.opengraph_service._select_photos_for_log")
    @patch("api.services.opengraph_service.boto3")
    def test_generate_log_image_no_trig(
        self,
        mock_boto3,
        mock_select,
        mock_download_photo,
        mock_download_avatar,
        mock_os_tile,
    ):
        mock_select.return_value = []
        mock_download_photo.return_value = None
        mock_download_avatar.return_value = None
        mock_os_tile.return_value = None

        mock_log = Mock()
        mock_log.id = 99
        mock_log.trig_id = 0
        mock_log.user_id = 1
        mock_log.date = None
        mock_log.condition = None

        mock_user = Mock()
        mock_user.id = 1
        mock_user.name = "Anon"

        mock_db = Mock(spec=Session)

        svc = OpenGraphService()
        img_bytes = svc._generate_log_image(mock_log, None, mock_user, mock_db)
        img = Image.open(io.BytesIO(img_bytes))
        assert img.size == (WIDTH, HEIGHT)

    @patch("api.services.opengraph_service._fetch_os_map_tile")
    @patch("api.services.opengraph_service._download_avatar")
    @patch("api.services.opengraph_service._download_photo")
    @patch("api.services.opengraph_service._select_photos_for_log")
    @patch("api.services.opengraph_service.boto3")
    def test_generate_log_image_no_user(
        self,
        mock_boto3,
        mock_select,
        mock_download_photo,
        mock_download_avatar,
        mock_os_tile,
    ):
        mock_select.return_value = []
        mock_download_photo.return_value = None
        mock_download_avatar.return_value = None
        mock_os_tile.return_value = None

        mock_trig = Mock()
        mock_trig.id = 1
        mock_trig.name = "Test Hill"
        mock_trig.waypoint = "TP0001"
        mock_trig.osgb_gridref = "TQ123456"
        mock_trig.osgb_height = 100.0
        mock_trig.wgs_lat = 51.5
        mock_trig.wgs_long = -0.1
        mock_trig.fb_number = ""
        mock_trig.stn_number = ""
        mock_trig.stn_number_active = ""
        mock_trig.stn_number_passive = ""
        mock_trig.stn_number_osgb36 = ""

        mock_log = Mock()
        mock_log.id = 100
        mock_log.trig_id = 1
        mock_log.user_id = None
        mock_log.date = date(2025, 1, 1)
        mock_log.condition = "D"

        mock_db = Mock(spec=Session)

        svc = OpenGraphService()
        img_bytes = svc._generate_log_image(mock_log, mock_trig, None, mock_db)
        img = Image.open(io.BytesIO(img_bytes))
        assert img.size == (WIDTH, HEIGHT)

    @patch("api.services.opengraph_service._fetch_os_map_tile")
    @patch("api.services.opengraph_service._download_avatar")
    @patch("api.services.opengraph_service._download_photo")
    @patch("api.services.opengraph_service._select_photos_for_log")
    @patch("api.services.opengraph_service.boto3")
    def test_generate_log_image_with_avatar(
        self,
        mock_boto3,
        mock_select,
        mock_download_photo,
        mock_download_avatar,
        mock_os_tile,
    ):
        mock_select.return_value = []
        mock_download_photo.return_value = None
        mock_download_avatar.return_value = Image.new("RGB", (200, 200), (0, 128, 0))
        mock_os_tile.return_value = None

        mock_trig = Mock()
        mock_trig.id = 1
        mock_trig.name = "Avatar Hill"
        mock_trig.waypoint = "TP0001"
        mock_trig.osgb_gridref = "TQ123456"
        mock_trig.osgb_height = 50.0
        mock_trig.wgs_lat = 51.5
        mock_trig.wgs_long = -0.1
        mock_trig.fb_number = ""
        mock_trig.stn_number = ""
        mock_trig.stn_number_active = ""
        mock_trig.stn_number_passive = ""
        mock_trig.stn_number_osgb36 = ""

        mock_log = Mock()
        mock_log.id = 50
        mock_log.trig_id = 1
        mock_log.user_id = 7
        mock_log.date = date(2024, 6, 1)
        mock_log.condition = "G"

        mock_user = Mock()
        mock_user.id = 7
        mock_user.name = "AvatarUser"

        mock_db = Mock(spec=Session)

        svc = OpenGraphService()
        img_bytes = svc._generate_log_image(mock_log, mock_trig, mock_user, mock_db)
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

    @patch("api.services.opengraph_service.boto3")
    def test_generate_og_html_contains_dimensions(self, mock_boto3):
        svc = OpenGraphService()
        html = svc.generate_og_html(
            title="T",
            description="D",
            image_url="https://example.com/img.png",
            canonical_url="https://example.com",
        )
        assert 'content="1200"' in html
        assert 'content="630"' in html

    @patch("api.services.opengraph_service.boto3")
    def test_generate_og_html_site_name(self, mock_boto3):
        svc = OpenGraphService()
        html = svc.generate_og_html(
            title="T",
            description="D",
            image_url="https://example.com/img.png",
            canonical_url="https://example.com",
        )
        assert "TrigpointingUK" in html


class TestFetchOsMapTile:
    """Test _fetch_os_map_tile."""

    @patch("api.services.opengraph_service.settings")
    def test_returns_none_without_api_key(self, mock_settings):
        from api.services.opengraph_service import _fetch_os_map_tile

        mock_settings.OS_API_KEY = ""
        assert _fetch_os_map_tile(51.5, -0.1) is None

    @patch("api.services.opengraph_service.settings")
    def test_returns_none_with_none_api_key(self, mock_settings):
        from api.services.opengraph_service import _fetch_os_map_tile

        mock_settings.OS_API_KEY = None
        assert _fetch_os_map_tile(51.5, -0.1) is None


class TestDownloadPhoto:
    """Test _download_photo."""

    @patch("api.services.opengraph_service.boto3")
    def test_download_from_s3(self, mock_boto3):
        from api.services.opengraph_service import _download_photo

        img = Image.new("RGB", (100, 100), (255, 0, 0))
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)

        mock_s3 = Mock()
        mock_s3.get_object.return_value = {"Body": Mock(read=lambda: buf.getvalue())}
        mock_boto3.client.return_value = mock_s3

        mock_photo = Mock()
        mock_photo.id = 1
        mock_photo.filename = "test.jpg"
        mock_db = Mock(spec=Session)

        result = _download_photo(mock_db, mock_photo)
        assert result is not None
        assert result.size == (100, 100)

    @patch("api.services.opengraph_service.boto3")
    def test_download_returns_none_on_failure(self, mock_boto3):
        from api.services.opengraph_service import _download_photo

        mock_s3 = Mock()
        mock_s3.get_object.side_effect = Exception("not found")
        mock_boto3.client.return_value = mock_s3

        mock_photo = Mock()
        mock_photo.id = 1
        mock_photo.filename = "missing.jpg"
        mock_photo.server_id = None

        mock_db = Mock(spec=Session)
        query = Mock()
        query.filter.return_value = query
        query.first.return_value = None
        mock_db.query.return_value = query

        result = _download_photo(mock_db, mock_photo)
        assert result is None


class TestDownloadAvatar:
    """Test _download_avatar."""

    @patch("api.services.opengraph_service.boto3")
    def test_returns_none_on_failure(self, mock_boto3):
        from api.services.opengraph_service import _download_avatar

        mock_s3 = Mock()
        mock_s3.get_object.side_effect = Exception("not found")
        mock_boto3.client.return_value = mock_s3

        mock_user = Mock()
        mock_user.id = 1
        result = _download_avatar(mock_user)
        assert result is None

    @patch("api.services.opengraph_service.boto3")
    def test_returns_image_on_success(self, mock_boto3):
        from api.services.opengraph_service import _download_avatar

        img = Image.new("RGB", (200, 200), (0, 128, 0))
        buf = io.BytesIO()
        img.save(buf, format="JPEG")
        buf.seek(0)

        mock_s3 = Mock()
        mock_s3.get_object.return_value = {"Body": Mock(read=lambda: buf.getvalue())}
        mock_boto3.client.return_value = mock_s3

        mock_user = Mock()
        mock_user.id = 7
        result = _download_avatar(mock_user)
        assert result is not None
        assert result.size == (200, 200)
