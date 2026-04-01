"""
Tests for the download rate limiting service.
"""

from unittest.mock import MagicMock, patch

from redis.exceptions import RedisError

from api.services.download_limits import (
    DOWNLOAD_LIMITS,
    DownloadRateLimiter,
    get_day_key,
    get_download_rate_limiter,
    get_hour_key,
    get_week_key,
)


class TestTimeKeyFunctions:
    def test_get_week_key_format(self):
        key = get_week_key()
        parts = key.split("-")
        assert len(parts) == 2
        assert len(parts[0]) == 4
        assert 1 <= int(parts[1]) <= 53

    def test_get_day_key_format(self):
        key = get_day_key()
        parts = key.split("-")
        assert len(parts) == 2
        assert len(parts[0]) == 4
        assert 1 <= int(parts[1]) <= 366

    def test_get_hour_key_format(self):
        key = get_hour_key()
        parts = key.split("-")
        assert len(parts) == 3
        assert 0 <= int(parts[2]) <= 23


class TestDownloadRateLimiterKeyGeneration:
    def test_get_key_format(self):
        limiter = DownloadRateLimiter.__new__(DownloadRateLimiter)
        limiter.redis_client = None
        limiter.limits = DOWNLOAD_LIMITS
        key = limiter._get_key("hourly", "2024-01", "user:42", "trigs_csv")
        assert "downloads:hourly:2024-01:user:42:trigs_csv" in key


class TestDownloadRateLimiterNoRedis:
    """Tests for DownloadRateLimiter when Redis is not available."""

    def setup_method(self):
        self.limiter = DownloadRateLimiter.__new__(DownloadRateLimiter)
        self.limiter.redis_client = None
        self.limiter.limits = DOWNLOAD_LIMITS

    def test_check_limit_allows_when_no_redis(self):
        allowed, msg = self.limiter.check_limit("csv", user_id=1)
        assert allowed is True
        assert msg is None

    def test_record_download_noop_when_no_redis(self):
        self.limiter.record_download("csv", user_id=1)

    def test_get_usage_stats_returns_error_when_no_redis(self):
        stats = self.limiter.get_usage_stats("csv", user_id=1)
        assert "error" in stats

    def test_get_counter_returns_zero_when_no_redis(self):
        assert self.limiter._get_counter("any_key") == 0

    def test_increment_counter_returns_zero_when_no_redis(self):
        assert self.limiter._increment_counter("any_key", 3600) == 0


class TestDownloadRateLimiterWithRedis:
    """Tests for DownloadRateLimiter with a mocked Redis client."""

    def setup_method(self):
        self.limiter = DownloadRateLimiter.__new__(DownloadRateLimiter)
        self.limiter.redis_client = MagicMock()
        self.limiter.limits = DOWNLOAD_LIMITS

    def test_get_counter_returns_value(self):
        self.limiter.redis_client.get.return_value = "5"
        assert self.limiter._get_counter("key") == 5

    def test_get_counter_returns_zero_for_none(self):
        self.limiter.redis_client.get.return_value = None
        assert self.limiter._get_counter("key") == 0

    def test_get_counter_returns_zero_on_redis_error(self):
        self.limiter.redis_client.get.side_effect = RedisError("fail")
        assert self.limiter._get_counter("key") == 0

    def test_increment_counter_calls_incr_and_expire(self):
        self.limiter.redis_client.incr.return_value = 3
        result = self.limiter._increment_counter("key", 7200)
        assert result == 3
        self.limiter.redis_client.incr.assert_called_once_with("key")
        self.limiter.redis_client.expire.assert_called_once_with("key", 7200)

    def test_increment_counter_returns_zero_on_redis_error(self):
        self.limiter.redis_client.incr.side_effect = RedisError("fail")
        assert self.limiter._increment_counter("key", 3600) == 0

    def test_check_limit_allows_under_hourly_limit(self):
        self.limiter.redis_client.get.return_value = "3"
        allowed, msg = self.limiter.check_limit("csv", user_id=1)
        assert allowed is True
        assert msg is None

    def test_check_limit_blocks_at_hourly_limit(self):
        self.limiter.redis_client.get.return_value = "10"
        allowed, msg = self.limiter.check_limit("csv", user_id=1)
        assert allowed is False
        assert "Hourly" in msg

    def test_check_limit_blocks_at_daily_limit(self):
        def get_side_effect(key):
            if "hourly" in key:
                return "0"
            if "daily" in key:
                return "20"
            return "0"

        self.limiter.redis_client.get.side_effect = get_side_effect
        allowed, msg = self.limiter.check_limit("csv", user_id=1)
        assert allowed is False
        assert "Daily" in msg

    def test_check_limit_allows_unknown_download_type(self):
        allowed, msg = self.limiter.check_limit("unknown_type", user_id=1)
        assert allowed is True
        assert msg is None

    def test_check_limit_blocks_weekly(self):
        self.limiter.redis_client.get.return_value = "1"
        self.limiter.limits = {"trigs_test": {"per_user_weekly": 1}}
        allowed, msg = self.limiter.check_limit("test", user_id=1)
        assert allowed is False
        assert "Weekly" in msg

    def test_record_download_increments_counters(self):
        self.limiter.redis_client.incr.return_value = 1
        self.limiter.record_download("csv", user_id=1)
        assert self.limiter.redis_client.incr.call_count == 2  # hourly + daily

    def test_record_download_noop_for_unknown_type(self):
        self.limiter.record_download("unknown_type", user_id=1)
        self.limiter.redis_client.incr.assert_not_called()

    def test_record_download_weekly_counter(self):
        self.limiter.redis_client.incr.return_value = 1
        self.limiter.limits = {"trigs_test": {"per_user_weekly": 5}}
        self.limiter.record_download("test", user_id=1)
        assert self.limiter.redis_client.incr.call_count == 1
        call_key = self.limiter.redis_client.incr.call_args[0][0]
        assert "weekly" in call_key

    def test_get_usage_stats_returns_all_periods(self):
        self.limiter.redis_client.get.return_value = "3"
        stats = self.limiter.get_usage_stats("csv", user_id=42)
        assert stats["download_type"] == "csv"
        assert stats["user_id"] == 42
        assert "hourly" in stats
        assert stats["hourly"]["used"] == 3
        assert stats["hourly"]["limit"] == 10
        assert "daily" in stats

    def test_get_usage_stats_weekly(self):
        self.limiter.redis_client.get.return_value = "0"
        self.limiter.limits = {"trigs_test": {"per_user_weekly": 1}}
        stats = self.limiter.get_usage_stats("test", user_id=1)
        assert "weekly" in stats
        assert stats["weekly"]["limit"] == 1


class TestLogLimitBreach:
    def test_log_limit_breach_does_not_raise(self):
        limiter = DownloadRateLimiter.__new__(DownloadRateLimiter)
        limiter.redis_client = None
        limiter.limits = DOWNLOAD_LIMITS
        limiter._log_limit_breach("hourly", "csv", 11, 10, "user:1")


class TestGetDownloadRateLimiter:
    @patch("api.services.download_limits._limiter", None)
    @patch("api.services.download_limits.get_redis_client", return_value=None)
    def test_creates_singleton(self, mock_redis):
        limiter = get_download_rate_limiter()
        assert isinstance(limiter, DownloadRateLimiter)

    @patch("api.services.download_limits.get_redis_client", return_value=None)
    def test_returns_same_instance(self, mock_redis):
        import api.services.download_limits as mod

        mod._limiter = None
        a = get_download_rate_limiter()
        b = get_download_rate_limiter()
        assert a is b


class TestGetRedisClient:
    @patch("api.services.download_limits.settings")
    def test_returns_none_when_no_redis_url(self, mock_settings):
        mock_settings.REDIS_URL = None
        from api.services.download_limits import get_redis_client as grc

        assert grc() is None

    @patch("api.services.download_limits.settings")
    @patch("api.services.download_limits.redis.from_url")
    def test_returns_client_on_success(self, mock_from_url, mock_settings):
        mock_settings.REDIS_URL = "redis://localhost:6379"
        mock_client = MagicMock()
        mock_from_url.return_value = mock_client
        from api.services.download_limits import get_redis_client as grc

        result = grc()
        assert result == mock_client

    @patch("api.services.download_limits.settings")
    @patch("api.services.download_limits.redis.from_url")
    def test_returns_none_on_connection_error(self, mock_from_url, mock_settings):
        mock_settings.REDIS_URL = "redis://localhost:6379"
        mock_from_url.side_effect = RedisError("connection refused")
        from api.services.download_limits import get_redis_client as grc

        assert grc() is None
