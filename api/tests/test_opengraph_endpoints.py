"""
Tests for the Open Graph HTML and image endpoints.
"""

from datetime import date, datetime
from unittest.mock import patch

from api.models import TLog, Trig
from api.models.user import User


def _create_trig(db, *, trig_id, waypoint="TP0001", name="Test Hill"):
    """Helper to create a trig with required fields."""
    trig = Trig(
        id=trig_id,
        waypoint=waypoint,
        name=name,
        osgb_gridref="TQ123456",
        osgb_height=100.0,
        wgs_lat=51.5,
        wgs_long=-0.1,
        fb_number="",
        stn_number="",
        condition="G",
        osgb_eastings=500000,
        osgb_northings=200000,
        current_use="",
        historic_use="",
        town="",
        permission_ind="Y",
        needs_attention=0,
        attention_comment="",
        crt_date=date.today(),
        crt_time=datetime.now().time(),
        crt_ip_addr="",
        user_added=0,
    )
    db.add(trig)
    db.flush()
    return trig


def _create_user(db, *, user_id=1, name="testuser"):
    """Helper to create a user."""
    user = User(id=user_id, name=name, email=f"{name}@example.com")
    db.add(user)
    db.flush()
    return user


def _create_log(db, *, log_id, trig_id, user_id):
    """Helper to create a log."""
    log = TLog(
        id=log_id,
        trig_id=trig_id,
        user_id=user_id,
        date=date(2024, 6, 15),
        condition="G",
        status="P",
    )
    db.add(log)
    db.flush()
    return log


class TestTrigOpengraphHtml:
    """Tests for GET /v1/trigs/{trig_id}/opengraph."""

    @patch("api.api.v1.endpoints.opengraph.OpenGraphService")
    def test_returns_html_with_og_tags(self, MockService, client, db):
        mock_svc = MockService.return_value
        mock_svc.get_or_create_trig_image.return_value = (
            "https://bucket.s3.amazonaws.com/trigs/1.png"
        )
        mock_svc.generate_trig_seo_html.return_value = (
            '<html><meta property="og:title" content="TP0001"/></html>'
        )

        _create_trig(db, trig_id=1)
        db.commit()

        response = client.get("/v1/trigs/1/opengraph")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        mock_svc.generate_trig_seo_html.assert_called_once()

    @patch("api.api.v1.endpoints.opengraph.OpenGraphService")
    def test_returns_cache_header(self, MockService, client, db):
        mock_svc = MockService.return_value
        mock_svc.get_or_create_trig_image.return_value = "https://example.com/img.png"
        mock_svc.generate_trig_seo_html.return_value = "<html></html>"

        _create_trig(db, trig_id=10)
        db.commit()

        response = client.get("/v1/trigs/10/opengraph")
        assert response.status_code == 200
        assert "max-age=3600" in response.headers.get("cache-control", "")

    @patch("api.api.v1.endpoints.opengraph.OpenGraphService")
    def test_image_generation_failure_returns_empty_image_url(
        self, MockService, client, db
    ):
        mock_svc = MockService.return_value
        mock_svc.get_or_create_trig_image.side_effect = Exception("S3 error")
        mock_svc.generate_trig_seo_html.return_value = "<html></html>"

        _create_trig(db, trig_id=11)
        db.commit()

        response = client.get("/v1/trigs/11/opengraph")
        assert response.status_code == 200
        call_kwargs = mock_svc.generate_trig_seo_html.call_args[1]
        assert call_kwargs["image_url"] == ""

    def test_trig_not_found(self, client):
        response = client.get("/v1/trigs/999999/opengraph")
        assert response.status_code == 404

    @patch("api.api.v1.endpoints.opengraph.OpenGraphService")
    def test_trig_with_no_height(self, MockService, client, db):
        mock_svc = MockService.return_value
        mock_svc.get_or_create_trig_image.return_value = "https://example.com/img.png"
        mock_svc.generate_trig_seo_html.return_value = "<html></html>"

        trig = Trig(
            id=12,
            waypoint="TP0012",
            name="No Height",
            osgb_gridref="SU000000",
            osgb_height=None,
            wgs_lat=52.0,
            wgs_long=-1.0,
            fb_number="",
            stn_number="",
            condition="G",
            osgb_eastings=400000,
            osgb_northings=300000,
            current_use="",
            historic_use="",
            town="",
            permission_ind="Y",
            needs_attention=0,
            attention_comment="",
            crt_date=date.today(),
            crt_time=datetime.now().time(),
            crt_ip_addr="",
            user_added=0,
        )
        db.add(trig)
        db.commit()

        response = client.get("/v1/trigs/12/opengraph")
        assert response.status_code == 200


class TestTrigOpengraphImage:
    """Tests for GET /v1/trigs/{trig_id}/opengraph-image."""

    @patch("api.api.v1.endpoints.opengraph.OpenGraphService")
    def test_redirects_to_s3(self, MockService, client, db):
        mock_svc = MockService.return_value
        mock_svc.get_or_create_trig_image.return_value = (
            "https://bucket.s3.amazonaws.com/trigs/2.png"
        )

        _create_trig(db, trig_id=2, waypoint="TP0002", name="Test Peak")
        db.commit()

        response = client.get("/v1/trigs/2/opengraph-image", follow_redirects=False)
        assert response.status_code == 302
        assert "bucket.s3.amazonaws.com" in response.headers["location"]

    @patch("api.api.v1.endpoints.opengraph.OpenGraphService")
    def test_refresh_deletes_and_adds_cachebuster(self, MockService, client, db):
        mock_svc = MockService.return_value
        mock_svc.get_or_create_trig_image.return_value = (
            "https://bucket.s3.amazonaws.com/trigs/20.png"
        )

        _create_trig(db, trig_id=20, waypoint="TP0020", name="Refresh Hill")
        db.commit()

        response = client.get(
            "/v1/trigs/20/opengraph-image?refresh=1", follow_redirects=False
        )
        assert response.status_code == 302
        assert "?t=" in response.headers["location"]
        mock_svc.delete_image.assert_called_once_with("trigs", 20)

    @patch("api.api.v1.endpoints.opengraph.OpenGraphService")
    def test_image_generation_failure_returns_500(self, MockService, client, db):
        mock_svc = MockService.return_value
        mock_svc.get_or_create_trig_image.side_effect = Exception("generation failed")

        _create_trig(db, trig_id=21, waypoint="TP0021", name="Broken Hill")
        db.commit()

        response = client.get("/v1/trigs/21/opengraph-image", follow_redirects=False)
        assert response.status_code == 500

    def test_trig_not_found(self, client):
        response = client.get(
            "/v1/trigs/999999/opengraph-image", follow_redirects=False
        )
        assert response.status_code == 404


class TestLogOpengraphHtml:
    """Tests for GET /v1/logs/{log_id}/opengraph."""

    @patch("api.api.v1.endpoints.opengraph.OpenGraphService")
    def test_returns_html_with_og_tags(self, MockService, client, db):
        mock_svc = MockService.return_value
        mock_svc.get_or_create_log_image.return_value = (
            "https://bucket.s3.amazonaws.com/logs/1.png"
        )
        mock_svc.generate_og_html.return_value = (
            '<html><meta property="og:title" content="Log #1"/></html>'
        )

        _create_user(db)
        _create_trig(db, trig_id=3, waypoint="TP0003", name="Hill Three")
        _create_log(db, log_id=1, trig_id=3, user_id=1)
        db.commit()

        response = client.get("/v1/logs/1/opengraph")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

    @patch("api.api.v1.endpoints.opengraph.OpenGraphService")
    def test_image_generation_failure_returns_empty_url(self, MockService, client, db):
        mock_svc = MockService.return_value
        mock_svc.get_or_create_log_image.side_effect = Exception("S3 error")
        mock_svc.generate_og_html.return_value = "<html></html>"

        _create_user(db, user_id=2, name="erruser")
        _create_trig(db, trig_id=30, waypoint="TP0030", name="Error Hill")
        _create_log(db, log_id=30, trig_id=30, user_id=2)
        db.commit()

        response = client.get("/v1/logs/30/opengraph")
        assert response.status_code == 200
        call_kwargs = mock_svc.generate_og_html.call_args[1]
        assert call_kwargs["image_url"] == ""

    @patch("api.api.v1.endpoints.opengraph.OpenGraphService")
    def test_log_with_no_condition(self, MockService, client, db):
        mock_svc = MockService.return_value
        mock_svc.get_or_create_log_image.return_value = "https://example.com/img.png"
        mock_svc.generate_og_html.return_value = "<html></html>"

        _create_user(db, user_id=3, name="nocond")
        _create_trig(db, trig_id=31, waypoint="TP0031", name="Cond Hill")
        log = TLog(
            id=31,
            trig_id=31,
            user_id=3,
            date=date(2024, 1, 1),
            condition=None,
            status="P",
        )
        db.add(log)
        db.commit()

        response = client.get("/v1/logs/31/opengraph")
        assert response.status_code == 200

    def test_log_not_found(self, client):
        response = client.get("/v1/logs/999999/opengraph")
        assert response.status_code == 404


class TestLogOpengraphImage:
    """Tests for GET /v1/logs/{log_id}/opengraph-image."""

    @patch("api.api.v1.endpoints.opengraph.OpenGraphService")
    def test_redirects_to_s3(self, MockService, client, db):
        mock_svc = MockService.return_value
        mock_svc.get_or_create_log_image.return_value = (
            "https://bucket.s3.amazonaws.com/logs/40.png"
        )

        _create_user(db, user_id=4, name="logimg")
        _create_trig(db, trig_id=40, waypoint="TP0040", name="Image Hill")
        _create_log(db, log_id=40, trig_id=40, user_id=4)
        db.commit()

        response = client.get("/v1/logs/40/opengraph-image", follow_redirects=False)
        assert response.status_code == 302
        assert "bucket.s3.amazonaws.com" in response.headers["location"]

    @patch("api.api.v1.endpoints.opengraph.OpenGraphService")
    def test_refresh_deletes_and_adds_cachebuster(self, MockService, client, db):
        mock_svc = MockService.return_value
        mock_svc.get_or_create_log_image.return_value = (
            "https://bucket.s3.amazonaws.com/logs/41.png"
        )

        _create_user(db, user_id=5, name="refresh")
        _create_trig(db, trig_id=41, waypoint="TP0041", name="Refresh Log Hill")
        _create_log(db, log_id=41, trig_id=41, user_id=5)
        db.commit()

        response = client.get(
            "/v1/logs/41/opengraph-image?refresh=1", follow_redirects=False
        )
        assert response.status_code == 302
        assert "?t=" in response.headers["location"]
        mock_svc.delete_image.assert_called_once_with("logs", 41)

    @patch("api.api.v1.endpoints.opengraph.OpenGraphService")
    def test_image_generation_failure_returns_500(self, MockService, client, db):
        mock_svc = MockService.return_value
        mock_svc.get_or_create_log_image.side_effect = Exception("generation failed")

        _create_user(db, user_id=6, name="broken")
        _create_trig(db, trig_id=42, waypoint="TP0042", name="Broken Log Hill")
        _create_log(db, log_id=42, trig_id=42, user_id=6)
        db.commit()

        response = client.get("/v1/logs/42/opengraph-image", follow_redirects=False)
        assert response.status_code == 500

    def test_log_not_found(self, client):
        response = client.get("/v1/logs/999999/opengraph-image", follow_redirects=False)
        assert response.status_code == 404
