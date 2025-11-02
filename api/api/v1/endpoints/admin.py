"""
Admin endpoints for cache management.
"""

import json
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from api.api.deps import get_db, require_admin
from api.api.lifecycle import openapi_lifecycle
from api.core.config import settings
from api.core.logging import get_logger
from api.models.user import User
from api.services.cache_service import cache_delete_pattern, get_redis_client

logger = get_logger(__name__)
router = APIRouter()


@router.get(
    "/stats",
    openapi_extra=openapi_lifecycle("beta", note="Get cache statistics"),
)
def get_cache_stats(
    admin_user: User = Depends(require_admin), db: Session = Depends(get_db)
):
    """
    Get statistics about the Redis cache for this application and environment.

    Requires `api:admin` scope.

    Returns:
    - info: Redis INFO dictionary (subset)
    - keys_count: Number of keys belonging to this application/environment
    """
    client = get_redis_client()
    if not client:
        raise HTTPException(
            status_code=503, detail="Cache unavailable or not configured"
        )

    try:
        info = client.info()  # type: ignore[misc]
        # Filter info to relevant stats
        stats = {
            "redis_version": info.get("redis_version"),  # type: ignore[union-attr]
            "uptime_in_seconds": info.get("uptime_in_seconds"),  # type: ignore[union-attr]
            "connected_clients": info.get("connected_clients"),  # type: ignore[union-attr]
            "used_memory_human": info.get("used_memory_human"),  # type: ignore[union-attr]
            "total_keys": info.get("db0", {}).get("keys"),  # type: ignore[union-attr]
        }

        # Count keys specific to this application and environment
        environment = settings.ENVIRONMENT.lower()
        app_env_pattern = f"fastapi:{environment}:*"
        keys_count = len(client.keys(app_env_pattern))  # type: ignore[arg-type]

        stats["app_env_keys_count"] = keys_count
        stats["app_env_pattern"] = app_env_pattern

        logger.info(
            json.dumps(
                {
                    "event": "cache_stats_retrieved",
                    "app_env_keys_count": keys_count,
                }
            )
        )

        return stats
    except Exception as e:
        logger.error(
            json.dumps(
                {
                    "event": "cache_stats_error",
                    "error": str(e),
                    "detail": "Failed to retrieve Redis info",
                }
            )
        )
        raise HTTPException(
            status_code=503,
            detail=f"Failed to retrieve Redis info: {e}",
        )


@router.delete(
    "",
    openapi_extra=openapi_lifecycle("beta", note="Flush cache by pattern or all"),
)
def flush_cache(
    pattern: Optional[str] = Query(
        None,
        description="Redis key pattern to delete (e.g., 'trig:*'). Pattern will be automatically prefixed with 'fastapi:{environment}:'. If omitted, flushes ALL FastAPI cache for this environment.",
    ),
    admin_user: User = Depends(require_admin),
):
    """
    Flush cache keys by pattern or flush all cache for this application/environment.

    Requires `api:admin` scope.

    Args:
    - pattern: Optional Redis key pattern (e.g., 'trig:123:*', 'user:*')

    If pattern is provided, only matching keys are deleted (automatically prefixed with 'fastapi:{environment}:').
    If pattern is omitted, ALL cache keys for this application and environment are deleted.

    Note: This only affects FastAPI caches in the current environment. Other applications
    (mediawiki, forum) and other environments are not affected.

    Returns:
    - deleted_count: Number of keys deleted
    - pattern: The full pattern used (including prefix)
    """
    environment = settings.ENVIRONMENT.lower()

    if pattern:
        # Add fastapi:environment prefix to user's pattern
        full_pattern = f"fastapi:{environment}:{pattern}"
        deleted_count = cache_delete_pattern(full_pattern)
        if deleted_count < 0:
            raise HTTPException(
                status_code=503,
                detail="Cache unavailable or not configured",
            )
        return {
            "deleted_count": deleted_count,
            "pattern": full_pattern,
            "message": f"Deleted {deleted_count} cache keys matching pattern '{full_pattern}'",
        }
    else:
        # Flush all FastAPI cache for this environment only
        full_pattern = f"fastapi:{environment}:*"
        deleted_count = cache_delete_pattern(full_pattern)
        if deleted_count < 0:
            raise HTTPException(
                status_code=503,
                detail="Cache unavailable or not configured",
            )
        return {
            "deleted_count": deleted_count,
            "pattern": full_pattern,
            "message": f"Flushed all FastAPI cache keys for {environment} environment ({deleted_count} keys)",
        }
