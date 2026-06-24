"""
Tests for api.services.tile_usage — tile usage tracking and weekly rate limiting.

The TileUsageTracker talks to Redis; these tests inject a mock client (or None)
so the premium classification, counter, limit-check and stats logic can be
exercised without a live Redis.
"""

from unittest.mock import MagicMock, patch

import pytest
from redis.exceptions import RedisError

from api.services import tile_usage
from api.services.tile_usage import (
    TileUsageTracker,
    get_redis_client,
    get_tile_usage_tracker,
    get_week_number,
    is_premium_tile,
)


class TestIsPremiumTile:
    def test_cached_tile_is_always_free(self):
        assert is_premium_tile("Outdoor_3857", 20, from_cache=True) is False

    def test_high_zoom_outdoor_is_premium(self):
        assert is_premium_tile("Outdoor_3857", 17, from_cache=False) is True

    def test_high_zoom_light_is_premium(self):
        assert is_premium_tile("Light_3857", 17, from_cache=False) is True

    def test_low_zoom_outdoor_is_free(self):
        assert is_premium_tile("Outdoor_3857", 16, from_cache=False) is False

    def test_leisure_above_zoom_5_is_premium(self):
        assert is_premium_tile("Leisure_27700", 6, from_cache=False) is True

    def test_leisure_at_zoom_5_is_free(self):
        assert is_premium_tile("Leisure_27700", 5, from_cache=False) is False

    def test_unknown_layer_is_free(self):
        assert is_premium_tile("SomeOtherLayer", 20, from_cache=False) is False


class TestGetWeekNumber:
    def test_format_is_year_dash_week(self):
        week = get_week_number()
        year, wk = week.split("-")
        assert len(year) == 4
        assert len(wk) == 2
        assert 1 <= int(wk) <= 53


class TestGetRedisClient:
    def test_returns_none_when_redis_url_unset(self):
        with patch.object(tile_usage.settings, "REDIS_URL", ""):
            assert get_redis_client() is None

    def test_returns_client_on_successful_ping(self):
        fake = MagicMock()
        with patch.object(tile_usage.settings, "REDIS_URL", "redis://localhost:6379"):
            with patch.object(tile_usage.redis, "from_url", return_value=fake):
                client = get_redis_client()
        assert client is fake
        fake.ping.assert_called_once()

    def test_returns_none_on_redis_error(self):
        fake = MagicMock()
        fake.ping.side_effect = RedisError("boom")
        with patch.object(tile_usage.settings, "REDIS_URL", "redis://localhost:6379"):
            with patch.object(tile_usage.redis, "from_url", return_value=fake):
                assert get_redis_client() is None


@pytest.fixture
def tracker():
    """A TileUsageTracker with a mock Redis client and known staging limits."""
    with patch.object(TileUsageTracker, "__init__", lambda self: None):
        t = TileUsageTracker()
    t.redis_client = MagicMock()
    t.limits = {
        "global_premium": 100,
        "global_free": 100,
        "per_ip_premium": 10,
        "per_ip_free": 10,
    }
    return t


class TestCounters:
    def test_get_counter_returns_zero_without_client(self, tracker):
        tracker.redis_client = None
        assert tracker._get_counter("k") == 0

    def test_get_counter_parses_value(self, tracker):
        tracker.redis_client.get.return_value = "42"
        assert tracker._get_counter("k") == 42

    def test_get_counter_handles_missing_key(self, tracker):
        tracker.redis_client.get.return_value = None
        assert tracker._get_counter("k") == 0

    def test_get_counter_handles_redis_error(self, tracker):
        tracker.redis_client.get.side_effect = RedisError("down")
        assert tracker._get_counter("k") == 0

    def test_increment_counter_returns_zero_without_client(self, tracker):
        tracker.redis_client = None
        assert tracker._increment_counter("k") == 0

    def test_increment_counter_sets_ttl(self, tracker):
        tracker.redis_client.incr.return_value = 5
        assert tracker._increment_counter("k") == 5
        tracker.redis_client.expire.assert_called_once_with("k", 8 * 24 * 60 * 60)

    def test_increment_counter_handles_redis_error(self, tracker):
        tracker.redis_client.incr.side_effect = RedisError("down")
        assert tracker._increment_counter("k") == 0


class TestKeyGeneration:
    def test_key_without_identifier(self, tracker):
        with patch.object(tile_usage.settings, "ENVIRONMENT", "staging"):
            with patch(
                "api.services.tile_usage.get_week_number", return_value="2025-45"
            ):
                key = tracker._get_key("total:free")
        assert key == "fastapi:staging:tiles:usage:weekly:2025-45:total:free"

    def test_key_with_identifier(self, tracker):
        with patch.object(tile_usage.settings, "ENVIRONMENT", "staging"):
            with patch(
                "api.services.tile_usage.get_week_number", return_value="2025-45"
            ):
                key = tracker._get_key("ip", "1.2.3.4")
        assert key == "fastapi:staging:tiles:usage:weekly:2025-45:ip:1.2.3.4"


class TestCheckLimits:
    def test_fails_open_when_redis_unavailable(self, tracker):
        tracker.redis_client = None
        allowed, msg = tracker.check_limits("Outdoor_3857", 20, False, "1.2.3.4")
        assert allowed is True
        assert msg is None

    def test_allows_when_under_limits(self, tracker):
        tracker.redis_client.get.return_value = "0"
        allowed, msg = tracker.check_limits("Outdoor_3857", 20, False, "1.2.3.4")
        assert allowed is True
        assert msg is None

    def test_blocks_when_global_limit_reached(self, tracker):
        # global counter at limit, ip counter low
        tracker._get_counter = MagicMock(side_effect=[100, 0])
        allowed, msg = tracker.check_limits("Outdoor_3857", 20, False, "1.2.3.4")
        assert allowed is False
        assert "Global premium" in msg

    def test_blocks_when_ip_limit_reached(self, tracker):
        # global low, ip at limit
        tracker._get_counter = MagicMock(side_effect=[0, 10])
        allowed, msg = tracker.check_limits("Outdoor_3857", 20, False, "1.2.3.4")
        assert allowed is False
        assert "IP address premium" in msg

    def test_free_tile_uses_free_limits(self, tracker):
        tracker._get_counter = MagicMock(side_effect=[0, 0])
        allowed, msg = tracker.check_limits("Outdoor_3857", 10, False, "1.2.3.4")
        assert allowed is True


class TestRecordUsage:
    def test_noop_without_client(self, tracker):
        tracker.redis_client = None
        # Should not raise
        tracker.record_usage("Outdoor_3857", 20, False, "1.2.3.4")

    def test_increments_global_and_ip_counters(self, tracker):
        tracker._increment_counter = MagicMock()
        tracker.record_usage("Outdoor_3857", 20, False, "1.2.3.4")
        assert tracker._increment_counter.call_count == 2


class TestUsageStats:
    def test_error_when_redis_unavailable(self, tracker):
        tracker.redis_client = None
        assert tracker.get_usage_stats() == {"error": "Redis not available"}

    def test_global_only_without_ip(self, tracker):
        tracker._get_counter = MagicMock(return_value=3)
        stats = tracker.get_usage_stats()
        assert "ip" not in stats
        assert stats["global"]["premium"]["used"] == 3
        assert stats["global"]["premium"]["limit"] == 100

    def test_includes_ip_stats_when_given(self, tracker):
        tracker._get_counter = MagicMock(return_value=2)
        stats = tracker.get_usage_stats(client_ip="1.2.3.4")
        assert stats["ip"]["free"]["used"] == 2
        assert stats["ip"]["free"]["limit"] == 10


class TestInit:
    def test_init_wires_client_and_limits(self):
        fake = MagicMock()
        with patch("api.services.tile_usage.get_redis_client", return_value=fake):
            t = TileUsageTracker()
        assert t.redis_client is fake
        assert "global_premium" in t.limits


class TestGetTrackerSingleton:
    def test_returns_same_instance(self):
        tile_usage._tracker = None
        with patch.object(TileUsageTracker, "__init__", lambda self: None):
            first = get_tile_usage_tracker()
            second = get_tile_usage_tracker()
        assert first is second
        tile_usage._tracker = None
