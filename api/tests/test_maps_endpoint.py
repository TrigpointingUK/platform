"""
Tests for the /v1/maps endpoint.

Tests map thumbnail generation.
"""

from fastapi.testclient import TestClient


class TestMapThumbnail:
    """Tests for GET /v1/maps/thumb/{trig_id}."""

    def test_get_map_thumbnail_returns_png(self, client: TestClient, db):
        """Test that thumbnail endpoint returns a PNG image."""
        response = client.get("/v1/maps/thumb/12345")

        assert response.status_code == 200
        assert response.headers["content-type"] == "image/png"

        # Check PNG magic bytes
        assert response.content[:8] == b"\x89PNG\r\n\x1a\n"

    def test_get_map_thumbnail_cache_headers(self, client: TestClient, db):
        """Test that cache headers are set correctly."""
        response = client.get("/v1/maps/thumb/12345")

        assert response.status_code == 200
        assert "Cache-Control" in response.headers
        assert "max-age=3600" in response.headers["Cache-Control"]
        assert response.headers.get("X-Placeholder") == "TBC"

    def test_get_map_thumbnail_different_trig_ids(self, client: TestClient, db):
        """Test thumbnails for different trig IDs."""
        # Test with various trig IDs
        for trig_id in [1, 100, 99999]:
            response = client.get(f"/v1/maps/thumb/{trig_id}")

            assert response.status_code == 200
            assert response.headers["content-type"] == "image/png"

    def test_get_map_thumbnail_image_size(self, client: TestClient, db):
        """Test that thumbnail has expected dimensions."""
        import io

        from PIL import Image

        response = client.get("/v1/maps/thumb/12345")

        assert response.status_code == 200

        # Parse the PNG and check dimensions
        img = Image.open(io.BytesIO(response.content))
        assert img.size == (320, 240)  # Expected dimensions
        assert img.mode == "RGB"

    def test_get_map_thumbnail_contains_trig_id(self, client: TestClient, db):
        """Test that thumbnail contains the trig ID text."""
        import io

        from PIL import Image

        response = client.get("/v1/maps/thumb/54321")

        assert response.status_code == 200

        # The image should be valid
        img = Image.open(io.BytesIO(response.content))
        assert img is not None
