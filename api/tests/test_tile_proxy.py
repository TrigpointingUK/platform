"""
Tests for OS tile proxy endpoint and usage tracking.
"""

from unittest.mock import Mock, patch

import pytest
from fastapi.testclient import TestClient

from api.main import app
from api.services.tile_usage import TileUsageTracker, is_premium_tile


class TestPremiumTileClassification:
    """Test premium tile classification logic."""

    def test_cached_tiles_always_free(self):
        """Cached tiles are always free regardless of layer or zoom."""
        assert is_premium_tile("Outdoor_3857", 20, True) is False
        assert is_premium_tile("Light_3857", 20, True) is False
        assert is_premium_tile("Leisure_27700", 10, True) is False

    def test_outdoor_premium_above_zoom_16(self):
        """Outdoor_3857 tiles are premium above zoom 16."""
        assert is_premium_tile("Outdoor_3857", 16, False) is False
        assert is_premium_tile("Outdoor_3857", 17, False) is True
        assert is_premium_tile("Outdoor_3857", 20, False) is True

    def test_light_premium_above_zoom_16(self):
        """Light_3857 tiles are premium above zoom 16."""
        assert is_premium_tile("Light_3857", 16, False) is False
        assert is_premium_tile("Light_3857", 17, False) is True
        assert is_premium_tile("Light_3857", 20, False) is True

    def test_leisure_premium_above_zoom_5(self):
        """Leisure_27700 tiles are premium above zoom 5."""
        assert is_premium_tile("Leisure_27700", 5, False) is False
        assert is_premium_tile("Leisure_27700", 6, False) is True
        assert is_premium_tile("Leisure_27700", 10, False) is True

    def test_low_zoom_always_free(self):
        """Low zoom tiles are free for all layers."""
        assert is_premium_tile("Outdoor_3857", 10, False) is False
        assert is_premium_tile("Light_3857", 10, False) is False
        assert is_premium_tile("Leisure_27700", 3, False) is False


class TestTileUsageTracker:
    """Test tile usage tracking and limit enforcement."""

    @pytest.fixture
    def mock_redis(self):
        """Mock Redis client."""
        with patch("api.services.tile_usage.get_redis_client") as mock:
            redis_mock = Mock()
            redis_mock.get.return_value = None
            redis_mock.incr.return_value = 1
            redis_mock.expire.return_value = True
            redis_mock.ping.return_value = True
            mock.return_value = redis_mock
            yield redis_mock

    def test_check_limits_allows_when_under_limit(self, mock_redis):
        """Check limits allows request when under all limits."""
        mock_redis.get.return_value = "50"  # Under all limits

        tracker = TileUsageTracker()
        allowed, error = tracker.check_limits(
            "Outdoor_3857", 17, False, "1.2.3.4", user_id=1
        )

        assert allowed is True
        assert error is None

    def test_check_limits_blocks_when_global_exceeded(self, mock_redis):
        """Check limits blocks when global limit exceeded."""

        def get_side_effect(key):
            if "total:premium" in key:
                return "7000000"  # At limit
            return "0"

        mock_redis.get.side_effect = get_side_effect

        tracker = TileUsageTracker()
        allowed, error = tracker.check_limits(
            "Outdoor_3857", 17, False, "1.2.3.4", user_id=1
        )

        assert allowed is False
        assert "Global premium tile limit exceeded" in error

    def test_check_limits_blocks_when_user_exceeded(self, mock_redis):
        """Check limits blocks when per-user limit exceeded."""

        def get_side_effect(key):
            if "user:1:premium" in key:
                return "70000"  # At user limit (1% of 7M)
            return "0"

        mock_redis.get.side_effect = get_side_effect

        tracker = TileUsageTracker()
        allowed, error = tracker.check_limits(
            "Outdoor_3857", 17, False, "1.2.3.4", user_id=1
        )

        assert allowed is False
        assert "Your premium tile limit exceeded" in error

    def test_check_limits_blocks_anon_ip_when_exceeded(self, mock_redis):
        """Check limits blocks anonymous IP when limit exceeded."""

        def get_side_effect(key):
            if "ip:1.2.3.4:premium" in key:
                return "70000"  # At IP limit
            return "0"

        mock_redis.get.side_effect = get_side_effect

        tracker = TileUsageTracker()
        allowed, error = tracker.check_limits(
            "Outdoor_3857", 17, False, "1.2.3.4", user_id=None
        )

        assert allowed is False
        assert "IP premium tile limit exceeded" in error

    def test_record_usage_increments_counters(self, mock_redis):
        """Record usage increments all applicable counters."""
        tracker = TileUsageTracker()
        tracker.record_usage("Outdoor_3857", 17, False, "1.2.3.4", user_id=1)

        # Should increment global, IP, and user counters
        assert mock_redis.incr.call_count == 3
        assert mock_redis.expire.call_count == 3

    def test_record_usage_anonymous_increments_anon_total(self, mock_redis):
        """Record usage increments anonymous total for non-authenticated users."""
        tracker = TileUsageTracker()
        tracker.record_usage("Outdoor_3857", 17, False, "1.2.3.4", user_id=None)

        # Should increment global, IP, and anon_total counters
        assert mock_redis.incr.call_count == 3

        # Check that anon_total was incremented
        call_args = [call[0][0] for call in mock_redis.incr.call_args_list]
        assert any("anon_total:premium" in arg for arg in call_args)


class TestTileProxyEndpoint:
    """Test tile proxy API endpoint."""

    @pytest.fixture
    def client(self):
        """Test client."""
        return TestClient(app)

    @pytest.fixture
    def mock_os_api(self):
        """Mock OS Maps API responses."""
        with patch("httpx.AsyncClient") as mock:
            yield mock

    @pytest.fixture
    def mock_tracker(self):
        """Mock tile usage tracker."""
        with patch("api.api.v1.endpoints.tiles.get_tile_usage_tracker") as mock:
            tracker = Mock()
            tracker.check_limits.return_value = (True, None)
            tracker.record_usage.return_value = None
            mock.return_value = tracker
            yield tracker

    def test_invalid_layer_returns_400(self, client, mock_tracker):
        """Invalid layer returns 400 Bad Request."""
        response = client.get("/v1/tiles/os/InvalidLayer/10/100/200.png")
        assert response.status_code == 400
        assert "Invalid layer" in response.json()["detail"]

    def test_limit_exceeded_returns_429(self, client, mock_tracker):
        """Rate limit exceeded returns 429 Too Many Requests."""
        mock_tracker.check_limits.return_value = (
            False,
            "Global premium tile limit exceeded",
        )

        response = client.get("/v1/tiles/os/Outdoor_3857/17/1000/2000.png")
        assert response.status_code == 429
        assert "limit exceeded" in response.json()["detail"]

    @patch("api.api.v1.endpoints.tiles.Path.exists")
    def test_cached_tile_served_from_efs(self, mock_exists, client, mock_tracker):
        """Cached tiles are served from EFS with appropriate headers."""
        mock_exists.return_value = True

        # Mock file reading
        with patch("builtins.open", create=True) as mock_open:
            mock_open.return_value.__enter__.return_value.read.return_value = (
                b"fake_png_data"
            )

            response = client.get("/v1/tiles/os/Outdoor_3857/10/100/200.png")

            assert response.status_code == 200
            assert response.headers["content-type"] == "image/png"
            assert response.headers["x-tile-source"] == "cache"
            assert response.headers["x-tile-type"] == "free"
            assert "max-age=31536000" in response.headers["cache-control"]


@pytest.mark.integration
class TestTileProxyIntegration:
    """Integration tests for tile proxy (requires Redis)."""

    @pytest.fixture
    def client(self):
        """Test client."""
        return TestClient(app)

    def test_usage_endpoint_requires_auth(self, client):
        """Usage endpoint requires authentication."""
        response = client.get("/v1/tiles/os/usage")
        assert response.status_code == 401
