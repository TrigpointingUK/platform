"""
Redis cache service for API response caching.

Provides Redis client singleton, cache key generation, and pattern-based invalidation.
Gracefully degrades when Redis is unavailable.
"""

import hashlib
import json
import ssl
import time
from typing import Any, Optional
from urllib.parse import urlparse

import redis
from redis.exceptions import RedisError

from api.core.config import settings
from api.core.logging import get_logger

logger = get_logger(__name__)

# Global Redis client singleton
_redis_client: Optional[redis.Redis] = None
_redis_available: bool = True


def get_redis_client() -> Optional[redis.Redis]:
    """
    Get or create Redis client singleton.

    Returns:
        Redis client or None if unavailable/disabled
    """
    global _redis_client, _redis_available

    # Check if caching is disabled via environment variable
    cache_enabled = getattr(settings, "CACHE_ENABLED", True)
    if not cache_enabled:
        logger.debug("Caching disabled via CACHE_ENABLED=false")
        return None

    # Return existing client if available
    if _redis_client is not None:
        return _redis_client

    # Check if we previously determined Redis is unavailable
    if not _redis_available:
        return None

    # Check if Redis URL is configured
    if not settings.REDIS_URL:
        logger.debug("Redis not configured (REDIS_URL not set), caching disabled")
        _redis_available = False
        return None

    try:
        redis_url = settings.REDIS_URL

        # Convert redis:// to rediss:// for serverless endpoints (ElastiCache Serverless)
        if "serverless" in redis_url and redis_url.startswith("redis://"):
            redis_url = redis_url.replace("redis://", "rediss://", 1)

        parsed = urlparse(redis_url)

        # Build connection with or without TLS
        if parsed.scheme == "rediss":
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE

            _redis_client = redis.from_url(
                redis_url,
                decode_responses=True,
                socket_connect_timeout=2,
                socket_timeout=2,
                retry_on_timeout=True,
                ssl=True,
                ssl_context=ssl_context,
            )
        else:
            _redis_client = redis.from_url(
                redis_url,
                decode_responses=True,
                socket_connect_timeout=2,
                socket_timeout=2,
                retry_on_timeout=True,
            )

        # Test connection
        _redis_client.ping()
        logger.info(
            json.dumps(
                {
                    "event": "cache_redis_connected",
                    "host": parsed.hostname,
                    "port": parsed.port,
                }
            )
        )
        return _redis_client

    except Exception as e:
        logger.warning(
            json.dumps(
                {
                    "event": "cache_redis_connection_failed",
                    "error": str(e),
                    "message": "Caching disabled - API will continue without cache",
                }
            )
        )
        _redis_available = False
        return None


def generate_cache_key(
    resource_type: str,
    resource_id: Optional[str] = None,
    subresource: Optional[str] = None,
    params: Optional[dict] = None,
    version: str = "v1",
) -> str:
    """
    Generate a cache key following the pattern:
    fastapi:{environment}:{resource_type}:{resource_id}:{subresource}:params_{hash}:{version}

    Args:
        resource_type: Type of resource (e.g., 'trig', 'user', 'log')
        resource_id: Optional ID of the resource
        subresource: Optional subresource (e.g., 'logs', 'photos')
        params: Optional dict of query parameters to hash
        version: Cache version for invalidation

    Returns:
        Cache key string

    Example:
        generate_cache_key('trig', '123', 'logs', {'skip': 0, 'limit': 10})
        # Returns: 'fastapi:development:trig:123:logs:params_abc123:v1'
    """
    # Get environment from settings (development, staging, production)
    environment = settings.ENVIRONMENT.lower()

    # Start with app name and environment namespace
    parts = ["fastapi", environment, resource_type]

    if resource_id:
        parts.append(str(resource_id))

    if subresource:
        parts.append(subresource)

    # Hash parameters for consistent key generation
    if params:
        # Sort keys for consistent hashing
        params_str = json.dumps(params, sort_keys=True)
        params_hash = (
            hashlib.md5(  # nosec B303, B324 - used for cache keys, not security
                params_str.encode(), usedforsecurity=False
            ).hexdigest()[:8]
        )
        parts.append(f"params_{params_hash}")

    parts.append(version)

    return ":".join(parts)


def cache_get(key: str) -> tuple[Optional[Any], Optional[int]]:
    """
    Get value from cache.

    Args:
        key: Cache key

    Returns:
        Tuple of (value, age_seconds) or (None, None) if not found or error
    """
    client = get_redis_client()
    if not client:
        return None, None

    try:
        # Use pipeline to get value and TTL atomically
        pipe = client.pipeline()
        pipe.get(key)
        pipe.ttl(key)
        results = pipe.execute()

        value = results[0]
        ttl = results[1]

        if value is None:
            return None, None

        # Deserialize JSON
        try:
            data = json.loads(value)

            # Calculate age from TTL if available
            age = None
            if ttl > 0 and "ttl" in data:
                original_ttl = data.get("ttl", ttl)
                age = original_ttl - ttl

            return data.get("value"), age
        except json.JSONDecodeError:
            logger.warning(f"Failed to decode cached value for key: {key}")
            return None, None

    except RedisError as e:
        logger.warning(
            json.dumps(
                {
                    "event": "cache_get_error",
                    "key": key,
                    "error": str(e),
                }
            )
        )
        return None, None


def cache_set(key: str, value: Any, ttl: int) -> bool:
    """
    Set value in cache with TTL.

    Args:
        key: Cache key
        value: Value to cache (must be JSON serializable)
        ttl: Time to live in seconds

    Returns:
        True if successful, False otherwise
    """
    client = get_redis_client()
    if not client:
        return False

    try:
        # Wrap value with metadata
        cache_data = {
            "value": value,
            "ttl": ttl,
            "cached_at": int(time.time()),
        }

        serialized = json.dumps(cache_data)
        client.setex(key, ttl, serialized)

        logger.debug(
            json.dumps(
                {
                    "event": "cache_set",
                    "key": key,
                    "ttl": ttl,
                }
            )
        )
        return True

    except (RedisError, TypeError, ValueError) as e:
        logger.warning(
            json.dumps(
                {
                    "event": "cache_set_error",
                    "key": key,
                    "error": str(e),
                }
            )
        )
        return False


def cache_delete(key: str) -> bool:
    """
    Delete a single cache key.

    Args:
        key: Cache key to delete

    Returns:
        True if successful, False otherwise
    """
    client = get_redis_client()
    if not client:
        return False

    try:
        deleted = client.delete(key)  # type: ignore[misc]
        logger.debug(
            json.dumps(
                {
                    "event": "cache_delete",
                    "key": key,
                    "deleted": deleted > 0,  # type: ignore[operator]
                }
            )
        )
        return deleted > 0  # type: ignore[operator]

    except RedisError as e:
        logger.warning(
            json.dumps(
                {
                    "event": "cache_delete_error",
                    "key": key,
                    "error": str(e),
                }
            )
        )
        return False


def cache_delete_pattern(pattern: str) -> int:
    """
    Delete all cache keys matching a pattern.

    Args:
        pattern: Redis key pattern (e.g., 'trig:123:*')

    Returns:
        Number of keys deleted, or -1 on error
    """
    client = get_redis_client()
    if not client:
        return -1

    try:
        # Use SCAN to avoid blocking on large keysets
        deleted_count = 0
        cursor = 0

        while True:
            cursor, keys = client.scan(cursor, match=pattern, count=100)  # type: ignore[misc]
            if keys:
                deleted_count += client.delete(*keys)  # type: ignore[operator]

            if cursor == 0:  # type: ignore[comparison-overlap]
                break

        logger.info(
            json.dumps(
                {
                    "event": "cache_delete_pattern",
                    "pattern": pattern,
                    "deleted_count": deleted_count,
                }
            )
        )
        return deleted_count

    except RedisError as e:
        logger.warning(
            json.dumps(
                {
                    "event": "cache_delete_pattern_error",
                    "pattern": pattern,
                    "error": str(e),
                }
            )
        )
        return -1


def cache_flush_all() -> bool:
    """
    Flush all cache keys from the current database.

    WARNING: This deletes ALL keys in the Redis database!

    Returns:
        True if successful, False otherwise
    """
    client = get_redis_client()
    if not client:
        return False

    try:
        client.flushdb()
        logger.info(
            json.dumps(
                {
                    "event": "cache_flush_all",
                    "message": "All cache keys flushed",
                }
            )
        )
        return True

    except RedisError as e:
        logger.warning(
            json.dumps(
                {
                    "event": "cache_flush_all_error",
                    "error": str(e),
                }
            )
        )
        return False


def cache_get_stats() -> Optional[dict]:
    """
    Get cache statistics.

    Returns:
        Dict with cache statistics or None on error
    """
    client = get_redis_client()
    if not client:
        return None

    try:
        info = client.info("stats")  # type: ignore[misc]
        memory = client.info("memory")  # type: ignore[misc]
        keyspace = client.info("keyspace")  # type: ignore[misc]

        # Count total keys
        total_keys = 0
        if "db0" in keyspace:  # type: ignore[operator]
            total_keys = keyspace["db0"].get("keys", 0)  # type: ignore[index,union-attr]

        # Calculate hit rate
        hits = info.get("keyspace_hits", 0)  # type: ignore[union-attr]
        misses = info.get("keyspace_misses", 0)  # type: ignore[union-attr]
        total_requests = hits + misses
        hit_rate = (hits / total_requests * 100) if total_requests > 0 else 0

        return {
            "total_keys": total_keys,
            "memory_used_bytes": memory.get("used_memory", 0),  # type: ignore[union-attr]
            "memory_used_human": memory.get("used_memory_human", "0B"),  # type: ignore[union-attr]
            "keyspace_hits": hits,
            "keyspace_misses": misses,
            "hit_rate_percent": round(hit_rate, 2),
            "connected_clients": info.get("connected_clients", 0),  # type: ignore[union-attr]
        }

    except RedisError as e:
        logger.warning(
            json.dumps(
                {
                    "event": "cache_stats_error",
                    "error": str(e),
                }
            )
        )
        return None
