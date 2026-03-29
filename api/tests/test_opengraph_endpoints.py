"""
Tests for the Open Graph HTML and image endpoints.
"""

from datetime import date, datetime
from unittest.mock import patch

from api.models import TLog, Trig
from api.models.user import User


class TestTrigOpengraphHtml:
    """Tests for GET /v1/trigs/{trig_id}/opengraph."""

    @patch("api.api.v1.endpoints.opengraph.OpenGraphService")
    def test_returns_html_with_og_tags(self, MockService, client, db):
        mock_svc = MockService.return_value
        mock_svc.get_or_create_trig_image.return_value = (
            "https://bucket.s3.amazonaws.com/trigs/1.png"
        )
        mock_svc.generate_og_html.return_value = (
            '<html><meta property="og:title" content="TP0001"/></html>'
        )

        trig = Trig(
            id=1,
            waypoint="TP0001",
            name="Test Hill",
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
        db.commit()

        response = client.get("/v1/trigs/1/opengraph")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        mock_svc.generate_og_html.assert_called_once()

    def test_trig_not_found(self, client):
        response = client.get("/v1/trigs/999999/opengraph")
        assert response.status_code == 404


class TestTrigOpengraphImage:
    """Tests for GET /v1/trigs/{trig_id}/opengraph-image."""

    @patch("api.api.v1.endpoints.opengraph.OpenGraphService")
    def test_redirects_to_s3(self, MockService, client, db):
        mock_svc = MockService.return_value
        mock_svc.get_or_create_trig_image.return_value = (
            "https://bucket.s3.amazonaws.com/trigs/1.png"
        )

        trig = Trig(
            id=2,
            waypoint="TP0002",
            name="Test Peak",
            osgb_gridref="SU123456",
            osgb_height=200.0,
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

        response = client.get("/v1/trigs/2/opengraph-image", follow_redirects=False)
        assert response.status_code == 302
        assert "bucket.s3.amazonaws.com" in response.headers["location"]

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

        user = User(
            id=1,
            name="testuser",
            email="test@example.com",
        )
        db.add(user)

        trig = Trig(
            id=3,
            waypoint="TP0003",
            name="Hill Three",
            osgb_gridref="ST123456",
            osgb_height=150.0,
            wgs_lat=51.0,
            wgs_long=-2.0,
            fb_number="",
            stn_number="",
            condition="G",
            osgb_eastings=350000,
            osgb_northings=150000,
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

        log = TLog(
            id=1,
            trig_id=3,
            user_id=1,
            date=date(2024, 6, 15),
            condition="G",
            status="P",
        )
        db.add(log)
        db.commit()

        response = client.get("/v1/logs/1/opengraph")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

    def test_log_not_found(self, client):
        response = client.get("/v1/logs/999999/opengraph")
        assert response.status_code == 404


class TestLogOpengraphImage:
    """Tests for GET /v1/logs/{log_id}/opengraph-image."""

    def test_log_not_found(self, client):
        response = client.get("/v1/logs/999999/opengraph-image", follow_redirects=False)
        assert response.status_code == 404
