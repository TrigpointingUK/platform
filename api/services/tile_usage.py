"""
Tile usage tracking service with Redis-based rate limiting.

Tracks OS Maps API tile usage across multiple dimensions:
- Global totals (premium + free)
- Per-IP totals (premium + free)
- Per-user totals (premium + free)
- Anonymous total (premium + free)

All counters are tracked weekly and automatically reset.

Redis keys are namespaced by environment to prevent conflicts:
fastapi:{environment}:tiles:usage:weekly:{YYYY-WW}:{metric_type}:{identifier}
"""

import json
from datetime import datetime, timezone
from typing import Optional, Tuple

import redis
from redis.exceptions import RedisError

from api.core.config import settings
from api.core.logging import get_logger

logger = get_logger(__name__)


def is_premium_tile(layer: str, z: int, from_cache: bool) -> bool:
    """
    Determine if a tile counts as premium (costs money from OS API).

    Cached tiles are ALWAYS free (no API call needed).
    Premium tiles are high-zoom tiles that incur OS API costs.

    Premium classification:
    - Outdoor_3857 or Light_3857 at zoom > 16: Premium
    - Leisure_27700 at zoom > 5: Premium
    - All other combinations: Free

    Args:
        layer: Tile layer name (e.g., 'Outdoor_3857')
        z: Zoom level
        from_cache: Whether tile was served from cache

    Returns:
        True if tile is premium, False otherwise
    """
    if from_cache:
        return False  # Cached tiles are always free (no OS API call)

    if layer in ["Outdoor_3857", "Light_3857"] and z > 16:
        return True

    if layer == "Leisure_27700" and z > 5:
        return True

    return False  # Low zoom tiles are free from OS API


def get_week_number() -> str:
    """
    Get current ISO week number as YYYY-WW format.

    Returns:
        Week identifier (e.g., '2025-45')
    """
    now = datetime.now(timezone.utc)
    year, week, _ = now.isocalendar()
    return f"{year}-{week:02d}"


def get_redis_client() -> Optional[redis.Redis]:
    """
    Get Redis client for usage tracking.

    Returns:
        Redis client or None if Redis is not configured
    """
    if not settings.REDIS_URL:
        logger.warning("REDIS_URL not configured, tile usage tracking disabled")
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
        logger.error(f"Failed to connect to Redis for tile usage: {e}")
        return None


class TileUsageTracker:
    """
    Track and enforce tile usage limits across multiple dimensions.
    """

    def __init__(self):
        self.redis_client = get_redis_client()
        self.limits = settings.tile_limits

    def _get_key(self, metric_type: str, identifier: Optional[str] = None) -> str:
        """
        Generate Redis key for usage counter.

        Args:
            metric_type: Type of metric (e.g., 'total', 'ip', 'user', 'anon_total')
            identifier: Optional identifier (IP address or user ID)

        Returns:
            Redis key string
        """
        week = get_week_number()
        env = settings.ENVIRONMENT
        if identifier:
            return f"fastapi:{env}:tiles:usage:weekly:{week}:{metric_type}:{identifier}"
        else:
            return f"fastapi:{env}:tiles:usage:weekly:{week}:{metric_type}"

    def _get_counter(self, key: str) -> int:
        """
        Get current counter value from Redis.

        Args:
            key: Redis key

        Returns:
            Current counter value (0 if key doesn't exist)
        """
        if not self.redis_client:
            return 0

        try:
            value = self.redis_client.get(key)
            return int(value) if value else 0
        except (RedisError, ValueError) as e:
            logger.error(f"Failed to get counter {key}: {e}")
            return 0

    def _increment_counter(self, key: str) -> int:
        """
        Increment counter in Redis with 8-day TTL (just over 1 week).

        Args:
            key: Redis key

        Returns:
            New counter value
        """
        if not self.redis_client:
            return 0

        try:
            new_value = self.redis_client.incr(key)
            # Set TTL of 8 days to ensure cleanup even if key is old
            self.redis_client.expire(key, 8 * 24 * 60 * 60)
            return new_value
        except RedisError as e:
            logger.error(f"Failed to increment counter {key}: {e}")
            return 0

    def check_limits(
        self,
        layer: str,
        z: int,
        from_cache: bool,
        client_ip: str,
        user_id: Optional[int] = None,
    ) -> Tuple[bool, Optional[str]]:
        """
        Check if tile request would exceed any usage limits.

        Does NOT increment counters - use record_usage() after successful tile fetch.

        Args:
            layer: Tile layer name
            z: Zoom level
            from_cache: Whether tile is from cache
            client_ip: Client IP address
            user_id: User ID if authenticated, None for anonymous

        Returns:
            Tuple of (allowed, error_message)
            - allowed: True if all limits are ok
            - error_message: Human-readable error if limit exceeded
        """
        if not self.redis_client:
            # If Redis is down, allow requests (fail open for availability)
            logger.warning(
                "Redis unavailable, allowing tile request without limit check"
            )
            return True, None

        premium = is_premium_tile(layer, z, from_cache)
        tile_type = "premium" if premium else "free"

        # Get all applicable counters
        global_key = self._get_key(f"total:{tile_type}")
        global_count = self._get_counter(global_key)

        ip_key = self._get_key(f"ip:{client_ip}:{tile_type}")
        ip_count = self._get_counter(ip_key)

        if user_id:
            # Registered user
            user_key = self._get_key(f"user:{user_id}:{tile_type}")
            user_count = self._get_counter(user_key)

            # Check limits
            if global_count >= self.limits[f"global_{tile_type}"]:
                self._log_limit_breach(
                    "global",
                    tile_type,
                    global_count,
                    self.limits[f"global_{tile_type}"],
                )
                return False, f"Global {tile_type} tile limit exceeded for this week"

            if user_count >= self.limits[f"registered_{tile_type}"]:
                self._log_limit_breach(
                    "user",
                    tile_type,
                    user_count,
                    self.limits[f"registered_{tile_type}"],
                    str(user_id),
                )
                return False, f"Your {tile_type} tile limit exceeded for this week"

            if ip_count >= self.limits[f"registered_{tile_type}"]:
                self._log_limit_breach(
                    "ip",
                    tile_type,
                    ip_count,
                    self.limits[f"registered_{tile_type}"],
                    client_ip,
                )
                return False, f"IP {tile_type} tile limit exceeded for this week"
        else:
            # Anonymous user
            anon_total_key = self._get_key(f"anon_total:{tile_type}")
            anon_total_count = self._get_counter(anon_total_key)

            # Check limits
            if global_count >= self.limits[f"global_{tile_type}"]:
                self._log_limit_breach(
                    "global",
                    tile_type,
                    global_count,
                    self.limits[f"global_{tile_type}"],
                )
                return False, f"Global {tile_type} tile limit exceeded for this week"

            if anon_total_count >= self.limits[f"anon_total_{tile_type}"]:
                self._log_limit_breach(
                    "anon_total",
                    tile_type,
                    anon_total_count,
                    self.limits[f"anon_total_{tile_type}"],
                )
                return (
                    False,
                    f"Anonymous user {tile_type} tile limit exceeded for this week",
                )

            if ip_count >= self.limits[f"anon_ip_{tile_type}"]:
                self._log_limit_breach(
                    "anon_ip",
                    tile_type,
                    ip_count,
                    self.limits[f"anon_ip_{tile_type}"],
                    client_ip,
                )
                return False, f"Your IP {tile_type} tile limit exceeded for this week"

        return True, None

    def record_usage(
        self,
        layer: str,
        z: int,
        from_cache: bool,
        client_ip: str,
        user_id: Optional[int] = None,
    ) -> None:
        """
        Record tile usage by incrementing all applicable counters.

        Should be called AFTER successful tile delivery.

        Args:
            layer: Tile layer name
            z: Zoom level
            from_cache: Whether tile was from cache
            client_ip: Client IP address
            user_id: User ID if authenticated, None for anonymous
        """
        if not self.redis_client:
            return

        premium = is_premium_tile(layer, z, from_cache)
        tile_type = "premium" if premium else "free"

        # Increment global counter
        global_key = self._get_key(f"total:{tile_type}")
        self._increment_counter(global_key)

        # Increment IP counter
        ip_key = self._get_key(f"ip:{client_ip}:{tile_type}")
        self._increment_counter(ip_key)

        if user_id:
            # Increment user counter
            user_key = self._get_key(f"user:{user_id}:{tile_type}")
            self._increment_counter(user_key)
        else:
            # Increment anonymous total counter
            anon_total_key = self._get_key(f"anon_total:{tile_type}")
            self._increment_counter(anon_total_key)

    def get_usage_stats(
        self, user_id: Optional[int] = None, client_ip: Optional[str] = None
    ) -> dict:
        """
        Get current usage statistics.

        Args:
            user_id: Optional user ID to get user-specific stats
            client_ip: Optional IP to get IP-specific stats

        Returns:
            Dictionary with usage stats and limits
        """
        if not self.redis_client:
            return {"error": "Redis not available"}

        week = get_week_number()
        stats = {
            "week": week,
            "global": {
                "premium": {
                    "used": self._get_counter(self._get_key("total:premium")),
                    "limit": self.limits["global_premium"],
                },
                "free": {
                    "used": self._get_counter(self._get_key("total:free")),
                    "limit": self.limits["global_free"],
                },
            },
        }

        if user_id:
            stats["user"] = {
                "premium": {
                    "used": self._get_counter(self._get_key(f"user:{user_id}:premium")),
                    "limit": self.limits["registered_premium"],
                },
                "free": {
                    "used": self._get_counter(self._get_key(f"user:{user_id}:free")),
                    "limit": self.limits["registered_free"],
                },
            }

        if client_ip:
            stats["ip"] = {
                "premium": {
                    "used": self._get_counter(self._get_key(f"ip:{client_ip}:premium")),
                    "limit": (
                        self.limits["anon_ip_premium"]
                        if not user_id
                        else self.limits["registered_premium"]
                    ),
                },
                "free": {
                    "used": self._get_counter(self._get_key(f"ip:{client_ip}:free")),
                    "limit": (
                        self.limits["anon_ip_free"]
                        if not user_id
                        else self.limits["registered_free"]
                    ),
                },
            }

        if not user_id:
            stats["anonymous_total"] = {
                "premium": {
                    "used": self._get_counter(self._get_key("anon_total:premium")),
                    "limit": self.limits["anon_total_premium"],
                },
                "free": {
                    "used": self._get_counter(self._get_key("anon_total:free")),
                    "limit": self.limits["anon_total_free"],
                },
            }

        return stats

    def _log_limit_breach(
        self,
        limit_type: str,
        tile_type: str,
        current_value: int,
        limit_value: int,
        identifier: Optional[str] = None,
    ) -> None:
        """
        Log a structured JSON message when a limit is breached.

        Args:
            limit_type: Type of limit (global, user, ip, anon_total, anon_ip)
            tile_type: Tile type (premium or free)
            current_value: Current counter value
            limit_value: Limit that was exceeded
            identifier: Optional identifier (user ID or IP)
        """
        log_data = {
            "event": "tile_limit_exceeded",
            "limit_type": limit_type,
            "tile_type": tile_type,
            "current_value": current_value,
            "limit_value": limit_value,
            "week": get_week_number(),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        if identifier:
            log_data["identifier"] = identifier

        logger.warning(json.dumps(log_data))


# Global instance
_tracker = None


def get_tile_usage_tracker() -> TileUsageTracker:
    """
    Get global tile usage tracker instance.

    Returns:
        TileUsageTracker instance
    """
    global _tracker
    if _tracker is None:
        _tracker = TileUsageTracker()
    return _tracker
