"""
Download rate limiting service with Redis-based tracking.

Tracks download usage per user to prevent abuse:
- Per-user hourly limits (for lighter downloads)
- Per-user daily limits (for heavier downloads)
- Per-user weekly limits (for expensive operations like photo archives)

Redis keys are namespaced by environment to prevent conflicts:
fastapi:{environment}:downloads:{period}:{YYYY-WW|YYYY-DDD|YYYY-DDD-HH}:{user_id}:{download_type}
"""

import json
from datetime import datetime, timezone
from typing import Optional, Tuple

import redis
from redis.exceptions import RedisError

from api.core.config import settings
from api.core.logging import get_logger

logger = get_logger(__name__)


# Download limits configuration
# Format: {download_type: {per_user_hourly, per_user_daily, per_user_weekly}}
DOWNLOAD_LIMITS = {
    "trigs_csv": {"per_user_hourly": 20, "per_user_daily": 100},
    "trigs_geojson": {"per_user_hourly": 20, "per_user_daily": 100},
    "trigs_kml": {"per_user_hourly": 10, "per_user_daily": 50},
    "trigs_gpx": {"per_user_hourly": 10, "per_user_daily": 50},
    "my_logs": {"per_user_daily": 20},
    "my_photos_metadata": {"per_user_daily": 10},
    "my_photos_zip": {"per_user_weekly": 1},  # Expensive operation
    # Anonymous users (identified by IP) have lower limits
    "anon_csv": {"per_ip_hourly": 5, "per_ip_daily": 20},
    "anon_geojson": {"per_ip_hourly": 5, "per_ip_daily": 20},
    "anon_kml": {"per_ip_hourly": 3, "per_ip_daily": 10},
    "anon_gpx": {"per_ip_hourly": 3, "per_ip_daily": 10},
}


def get_week_key() -> str:
    """Get current ISO week as YYYY-WW format."""
    now = datetime.now(timezone.utc)
    year, week, _ = now.isocalendar()
    return f"{year}-{week:02d}"


def get_day_key() -> str:
    """Get current day as YYYY-DDD format (day of year)."""
    now = datetime.now(timezone.utc)
    return f"{now.year}-{now.timetuple().tm_yday:03d}"


def get_hour_key() -> str:
    """Get current hour as YYYY-DDD-HH format."""
    now = datetime.now(timezone.utc)
    return f"{now.year}-{now.timetuple().tm_yday:03d}-{now.hour:02d}"


def get_redis_client() -> Optional[redis.Redis]:
    """
    Get Redis client for download tracking.

    Returns:
        Redis client or None if Redis is not configured
    """
    if not settings.REDIS_URL:
        logger.debug("REDIS_URL not configured, download rate limiting disabled")
        return None

    try:
        client = redis.from_url(
            settings.REDIS_URL,
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=5,
        )
        # Test connection
        client.ping()
        return client
    except RedisError as e:
        logger.error(f"Failed to connect to Redis for download limits: {e}")
        return None


class DownloadRateLimiter:
    """
    Track and enforce download rate limits.
    """

    def __init__(self):
        self.redis_client = get_redis_client()
        self.limits = DOWNLOAD_LIMITS

    def _get_key(
        self, period: str, period_key: str, identifier: str, download_type: str
    ) -> str:
        """
        Generate Redis key for download counter.

        Args:
            period: Time period (hourly, daily, weekly)
            period_key: Period identifier (YYYY-WW, YYYY-DDD, YYYY-DDD-HH)
            identifier: User ID or IP address
            download_type: Type of download (e.g., trigs_csv)

        Returns:
            Redis key string
        """
        env = settings.ENVIRONMENT
        return f"fastapi:{env}:downloads:{period}:{period_key}:{identifier}:{download_type}"

    def _get_counter(self, key: str) -> int:
        """Get current counter value from Redis."""
        if not self.redis_client:
            return 0

        try:
            value = self.redis_client.get(key)
            return int(value) if value else 0
        except (RedisError, ValueError) as e:
            logger.error(f"Failed to get download counter {key}: {e}")
            return 0

    def _increment_counter(self, key: str, ttl_seconds: int) -> int:
        """
        Increment counter in Redis with specified TTL.

        Args:
            key: Redis key
            ttl_seconds: Time to live in seconds

        Returns:
            New counter value
        """
        if not self.redis_client:
            return 0

        try:
            new_value = self.redis_client.incr(key)
            self.redis_client.expire(key, ttl_seconds)
            return new_value
        except RedisError as e:
            logger.error(f"Failed to increment download counter {key}: {e}")
            return 0

    def check_limit(
        self,
        download_type: str,
        user_id: Optional[int] = None,
        client_ip: Optional[str] = None,
    ) -> Tuple[bool, Optional[str]]:
        """
        Check if download request would exceed rate limits.

        Args:
            download_type: Type of download (e.g., 'csv', 'geojson')
            user_id: Authenticated user ID (None for anonymous)
            client_ip: Client IP address (used for anonymous rate limiting)

        Returns:
            Tuple of (allowed, error_message)
        """
        if not self.redis_client:
            # If Redis is down, allow requests (fail open for availability)
            logger.debug("Redis unavailable, allowing download without limit check")
            return True, None

        # Determine which limits to check
        if user_id:
            # Authenticated user limits
            limit_key = f"trigs_{download_type}"
            identifier = f"user:{user_id}"
        else:
            # Anonymous user limits (by IP)
            limit_key = f"anon_{download_type}"
            identifier = f"ip:{client_ip}"

        limits = self.limits.get(limit_key, {})
        if not limits:
            # No limits configured for this download type
            return True, None

        # Check hourly limit
        if "per_user_hourly" in limits or "per_ip_hourly" in limits:
            hourly_limit = limits.get("per_user_hourly") or limits.get("per_ip_hourly")
            hourly_key = self._get_key("hourly", get_hour_key(), identifier, limit_key)
            hourly_count = self._get_counter(hourly_key)

            if hourly_count >= hourly_limit:
                self._log_limit_breach(
                    "hourly", limit_key, hourly_count, hourly_limit, identifier
                )
                return (
                    False,
                    f"Hourly download limit exceeded ({hourly_limit}/hour). Please try again later.",
                )

        # Check daily limit
        if "per_user_daily" in limits or "per_ip_daily" in limits:
            daily_limit = limits.get("per_user_daily") or limits.get("per_ip_daily")
            daily_key = self._get_key("daily", get_day_key(), identifier, limit_key)
            daily_count = self._get_counter(daily_key)

            if daily_count >= daily_limit:
                self._log_limit_breach(
                    "daily", limit_key, daily_count, daily_limit, identifier
                )
                return (
                    False,
                    f"Daily download limit exceeded ({daily_limit}/day). Please try again tomorrow.",
                )

        # Check weekly limit
        if "per_user_weekly" in limits:
            weekly_limit = limits["per_user_weekly"]
            weekly_key = self._get_key("weekly", get_week_key(), identifier, limit_key)
            weekly_count = self._get_counter(weekly_key)

            if weekly_count >= weekly_limit:
                self._log_limit_breach(
                    "weekly", limit_key, weekly_count, weekly_limit, identifier
                )
                return (
                    False,
                    f"Weekly download limit exceeded ({weekly_limit}/week). Please try again next week.",
                )

        return True, None

    def record_download(
        self,
        download_type: str,
        user_id: Optional[int] = None,
        client_ip: Optional[str] = None,
    ) -> None:
        """
        Record a download by incrementing all applicable counters.

        Should be called AFTER successful download delivery.

        Args:
            download_type: Type of download (e.g., 'csv', 'geojson')
            user_id: Authenticated user ID (None for anonymous)
            client_ip: Client IP address (used for anonymous rate limiting)
        """
        if not self.redis_client:
            return

        # Determine which limits to track
        if user_id:
            limit_key = f"trigs_{download_type}"
            identifier = f"user:{user_id}"
        else:
            limit_key = f"anon_{download_type}"
            identifier = f"ip:{client_ip}"

        limits = self.limits.get(limit_key, {})
        if not limits:
            return

        # Increment hourly counter (TTL: 2 hours)
        if "per_user_hourly" in limits or "per_ip_hourly" in limits:
            hourly_key = self._get_key("hourly", get_hour_key(), identifier, limit_key)
            self._increment_counter(hourly_key, 2 * 60 * 60)

        # Increment daily counter (TTL: 2 days)
        if "per_user_daily" in limits or "per_ip_daily" in limits:
            daily_key = self._get_key("daily", get_day_key(), identifier, limit_key)
            self._increment_counter(daily_key, 2 * 24 * 60 * 60)

        # Increment weekly counter (TTL: 8 days)
        if "per_user_weekly" in limits:
            weekly_key = self._get_key("weekly", get_week_key(), identifier, limit_key)
            self._increment_counter(weekly_key, 8 * 24 * 60 * 60)

    def get_usage_stats(
        self,
        download_type: str,
        user_id: Optional[int] = None,
        client_ip: Optional[str] = None,
    ) -> dict:
        """
        Get current usage statistics for a user/IP.

        Args:
            download_type: Type of download
            user_id: User ID (None for anonymous)
            client_ip: Client IP address

        Returns:
            Dictionary with usage stats and limits
        """
        if not self.redis_client:
            return {"error": "Redis not available"}

        if user_id:
            limit_key = f"trigs_{download_type}"
            identifier = f"user:{user_id}"
        else:
            limit_key = f"anon_{download_type}"
            identifier = f"ip:{client_ip}"

        limits = self.limits.get(limit_key, {})
        stats: dict = {
            "download_type": download_type,
            "identifier_type": "user" if user_id else "ip",
        }

        if "per_user_hourly" in limits or "per_ip_hourly" in limits:
            hourly_limit = limits.get("per_user_hourly") or limits.get("per_ip_hourly")
            hourly_key = self._get_key("hourly", get_hour_key(), identifier, limit_key)
            stats["hourly"] = {
                "used": self._get_counter(hourly_key),
                "limit": hourly_limit,
            }

        if "per_user_daily" in limits or "per_ip_daily" in limits:
            daily_limit = limits.get("per_user_daily") or limits.get("per_ip_daily")
            daily_key = self._get_key("daily", get_day_key(), identifier, limit_key)
            stats["daily"] = {
                "used": self._get_counter(daily_key),
                "limit": daily_limit,
            }

        if "per_user_weekly" in limits:
            weekly_key = self._get_key("weekly", get_week_key(), identifier, limit_key)
            stats["weekly"] = {
                "used": self._get_counter(weekly_key),
                "limit": limits["per_user_weekly"],
            }

        return stats

    def _log_limit_breach(
        self,
        period: str,
        download_type: str,
        current_value: int,
        limit_value: int,
        identifier: str,
    ) -> None:
        """Log a structured message when a limit is breached."""
        log_data = {
            "event": "download_limit_exceeded",
            "period": period,
            "download_type": download_type,
            "current_value": current_value,
            "limit_value": limit_value,
            "identifier": identifier,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        logger.warning(json.dumps(log_data))


# Global instance
_limiter: Optional[DownloadRateLimiter] = None


def get_download_rate_limiter() -> DownloadRateLimiter:
    """
    Get global download rate limiter instance.

    Returns:
        DownloadRateLimiter instance
    """
    global _limiter
    if _limiter is None:
        _limiter = DownloadRateLimiter()
    return _limiter
