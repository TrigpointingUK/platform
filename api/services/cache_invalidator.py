"""
Cache invalidation service.

Provides centralized cache invalidation logic for CRUD operations.
Defines invalidation patterns for each resource type.

All patterns are automatically prefixed with 'fastapi:{environment}:' to avoid
collisions with other applications sharing the same Redis instance.
"""

import json
from typing import List, Optional

from api.core.config import settings
from api.core.logging import get_logger
from api.services.cache_service import cache_delete_pattern

logger = get_logger(__name__)


def _prefix_pattern(pattern: str) -> str:
    """
    Add fastapi:{environment}: prefix to cache pattern.

    Args:
        pattern: Cache pattern (e.g., 'stats:site:*')

    Returns:
        Prefixed pattern (e.g., 'fastapi:development:stats:site:*')
    """
    environment = settings.ENVIRONMENT.lower()
    return f"fastapi:{environment}:{pattern}"


def invalidate_patterns(patterns: List[str]) -> int:
    """
    Invalidate cache keys matching the given patterns.

    Automatically prefixes patterns with 'fastapi:{environment}:' to ensure
    we only invalidate this application's cache keys in this environment.

    Args:
        patterns: List of Redis key patterns (e.g., ['trig:123:*', 'stats:site:*'])

    Returns:
        Total number of keys deleted
    """
    total_deleted = 0

    # Prefix all patterns with app name and environment
    prefixed_patterns = [_prefix_pattern(p) for p in patterns]

    for pattern in prefixed_patterns:
        deleted = cache_delete_pattern(pattern)
        if deleted >= 0:
            total_deleted += deleted

    if total_deleted > 0:
        logger.info(
            json.dumps(
                {
                    "event": "cache_invalidated",
                    "patterns": prefixed_patterns,
                    "keys_deleted": total_deleted,
                }
            )
        )

    return total_deleted


def invalidate_log_caches(trig_id: int, user_id: int, log_id: Optional[int] = None):
    """
    Invalidate caches when a log is created, updated, or deleted.

    Args:
        trig_id: ID of the trig the log belongs to
        user_id: ID of the user who created the log
        log_id: Optional ID of the specific log (for updates/deletes)
    """
    patterns = [
        "stats:site:*",  # Site-wide stats
        f"trig:{trig_id}:*",  # All trig-related caches
        f"user:{user_id}:*",  # All user-related caches
        "trigs:list:*",  # All trig list queries
        "logs:list:*",  # All log list queries
    ]

    if log_id is not None:
        patterns.append(f"log:{log_id}:*")  # Specific log caches

    invalidate_patterns(patterns)


def invalidate_photo_caches(
    trig_id: int, user_id: int, log_id: int, photo_id: Optional[int] = None
):
    """
    Invalidate caches when a photo is created, updated, or deleted.

    Args:
        trig_id: ID of the trig the photo belongs to
        user_id: ID of the user who uploaded the photo
        log_id: ID of the log the photo belongs to
        photo_id: Optional ID of the specific photo (for updates/deletes)
    """
    patterns = [
        "stats:site:*",  # Site-wide stats
        f"trig:{trig_id}:*",  # All trig-related caches (includes photos)
        f"user:{user_id}:*",  # All user-related caches (includes badge, photos)
        f"log:{log_id}:*",  # Specific log caches
        "photos:list:*",  # All photo list queries
    ]

    if photo_id is not None:
        patterns.append(f"photo:{photo_id}:*")  # Specific photo caches

    invalidate_patterns(patterns)


def invalidate_user_caches(user_id: Optional[int] = None):
    """
    Invalidate caches when a user is created or updated.

    Args:
        user_id: Optional ID of the specific user (for updates)
    """
    patterns = [
        "stats:site:*",  # Site-wide stats
        "users:list:*",  # All user list queries
    ]

    if user_id is not None:
        patterns.append(f"user:{user_id}:*")  # Specific user caches

    invalidate_patterns(patterns)


def invalidate_trig_caches(trig_id: int):
    """
    Invalidate caches when a trig is updated.

    Args:
        trig_id: ID of the trig
    """
    patterns = [
        f"trig:{trig_id}:*",  # All trig-related caches
        "trigs:list:*",  # All trig list queries
    ]

    invalidate_patterns(patterns)
