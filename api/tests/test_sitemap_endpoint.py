"""
Tests for the sitemap endpoints.
"""

from datetime import date, datetime
from unittest.mock import patch

from api.api.v1.endpoints.sitemap import _api_base_url, _format_date, _site_base_url


class TestHelperFunctions:
    def test_format_date_with_none(self):
        assert _format_date(None) is None

    def test_format_date_with_date(self):
        assert _format_date(date(2024, 6, 15)) == "2024-06-15"

    def test_format_date_with_datetime(self):
        assert _format_date(datetime(2024, 6, 15, 10, 30)) == "2024-06-15"

    @patch("api.api.v1.endpoints.sitemap.settings")
    def test_site_base_url_production(self, mock_settings):
        mock_settings.ENVIRONMENT = "production"
        assert _site_base_url() == "https://trigpointing.uk"

    @patch("api.api.v1.endpoints.sitemap.settings")
    def test_site_base_url_staging(self, mock_settings):
        mock_settings.ENVIRONMENT = "staging"
        assert _site_base_url() == "https://trigpointing.me"

    @patch("api.api.v1.endpoints.sitemap.settings")
    def test_api_base_url_production(self, mock_settings):
        mock_settings.ENVIRONMENT = "production"
        assert _api_base_url() == "https://api.trigpointing.uk"

    @patch("api.api.v1.endpoints.sitemap.settings")
    def test_api_base_url_staging(self, mock_settings):
        mock_settings.ENVIRONMENT = "staging"
        assert _api_base_url() == "https://api.trigpointing.me"


class TestSitemapIndex:
    def test_returns_xml(self, client, db, make_trig):
        make_trig()
        resp = client.get("/v1/sitemap")
        assert resp.status_code == 200
        assert "application/xml" in resp.headers["content-type"]
        assert "<sitemapindex" in resp.text
        assert "/v1/sitemap/static" in resp.text
        assert "/v1/sitemap/trigs" in resp.text
        assert "/v1/sitemap/photos" in resp.text


class TestSitemapStatic:
    def test_returns_xml_with_static_pages(self, client):
        resp = client.get("/v1/sitemap/static")
        assert resp.status_code == 200
        assert "<urlset" in resp.text
        assert "/trigs" in resp.text
        assert "/about" in resp.text
        assert "/contact" in resp.text


class TestSitemapTrigs:
    def test_returns_xml_with_trigs(self, client, db, make_trig):
        trig = make_trig()
        resp = client.get("/v1/sitemap/trigs?page=1")
        assert resp.status_code == 200
        assert "<urlset" in resp.text
        assert f"/trigs/{trig.id}" in resp.text

    def test_pagination(self, client, db, make_trig):
        make_trig()
        resp = client.get("/v1/sitemap/trigs?page=99999")
        assert resp.status_code == 200
        assert "<urlset" in resp.text


class TestSitemapPhotos:
    def test_returns_xml(self, client, db):
        resp = client.get("/v1/sitemap/photos")
        assert resp.status_code == 200
        assert "<urlset" in resp.text
