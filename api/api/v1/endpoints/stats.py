"""
Site-wide statistics endpoint with Redis caching.
"""

from datetime import datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from api.api.deps import get_db
from api.api.lifecycle import openapi_lifecycle
from api.core.logging import get_logger
from api.models.tphoto import TPhoto
from api.models.trig import Trig
from api.models.user import TLog, User
from api.utils.cache_decorator import cached

logger = get_logger(__name__)
router = APIRouter()


@router.get("/site", openapi_extra=openapi_lifecycle("beta"))
@cached(resource_type="stats", ttl=3600, subresource="site")  # 1 hour
def get_site_stats(db: Session = Depends(get_db)):
    """
    Get site-wide statistics.

    Returns:
    - total_trigs: Total number of trigpoints (approximate)
    - total_members: Number of active members (exact count from user_activity_summary)
    - total_logs: Total number of visit logs (approximate)
    - total_photos: Total number of photos (exact)
    - recent_logs_7d: Number of logs in last 7 days
    - recent_users_30d: Number of users joined in last 30 days

    Results are cached in Redis for 1 hour. Cache is automatically invalidated
    when logs, photos, or users are created.

    Performance: Uses pg_class statistics for large tables (trigs, logs) and
    exact counts for smaller tables (members, photos) where accuracy matters.
    """
    # Calculate date thresholds once
    seven_days_ago = datetime.now() - timedelta(days=7)
    thirty_days_ago = datetime.now() - timedelta(days=30)

    # Strategy: Use approximate counts from PostgreSQL statistics for large tables
    # These are much faster and usually accurate enough for dashboard stats
    try:
        # Try to use pg_class for fast approximate counts (PostgreSQL specific)
        # This is orders of magnitude faster than COUNT(*) on large tables
        # Note: Filter by current schema to handle test isolation (multiple schemas)
        approx_stats = db.execute(text("""
            SELECT
                (SELECT reltuples::bigint FROM pg_class c
                 JOIN pg_namespace n ON c.relnamespace = n.oid
                 WHERE relname = 'trig' AND n.nspname = current_schema()) as total_trigs,
                (SELECT reltuples::bigint FROM pg_class c
                 JOIN pg_namespace n ON c.relnamespace = n.oid
                 WHERE relname = 'tlog' AND n.nspname = current_schema()) as total_logs
            """)).first()

        # Use exact count for members (small table, needs to match /users page)
        total_members = db.execute(
            text("SELECT COUNT(*) FROM user_activity_summary")
        ).scalar()

        # For photos, we need exact count due to deleted_ind filter, but optimize it
        total_photos = db.execute(
            text("SELECT COUNT(*) FROM tphoto WHERE deleted_ind != 'Y'")
        ).scalar()

        # For recent activity, use optimized queries with proper indexes
        recent_logs_7d = db.execute(
            text("SELECT COUNT(*) FROM tlog WHERE upd_timestamp >= :seven_days_ago"),
            {"seven_days_ago": seven_days_ago},
        ).scalar()

        recent_users_30d = db.execute(
            text('SELECT COUNT(*) FROM "user" WHERE crt_date >= :thirty_days_ago'),
            {"thirty_days_ago": thirty_days_ago.date()},
        ).scalar()

        result = {
            "total_trigs": (
                int(approx_stats[0]) if approx_stats and approx_stats[0] else 0
            ),
            "total_members": int(total_members) if total_members else 0,
            "total_logs": (
                int(approx_stats[1]) if approx_stats and approx_stats[1] else 0
            ),
            "total_photos": int(total_photos) if total_photos else 0,
            "recent_logs_7d": int(recent_logs_7d) if recent_logs_7d else 0,
            "recent_users_30d": int(recent_users_30d) if recent_users_30d else 0,
        }

        logger.debug(f"Site stats computed using optimized queries: {result}")

    except Exception as e:
        # Fallback to standard COUNT queries if pg_class fails (e.g., on MySQL or in tests)
        logger.warning(
            f"Failed to use pg_class for stats, falling back to standard counts: {e}"
        )

        total_trigs = db.query(Trig).count()
        total_members = db.execute(
            text("SELECT COUNT(*) FROM user_activity_summary")
        ).scalar()
        total_logs = db.query(TLog).count()
        total_photos = db.query(TPhoto).filter(TPhoto.deleted_ind != "Y").count()

        recent_logs_7d = (
            db.query(TLog).filter(TLog.upd_timestamp >= seven_days_ago).count()
        )
        recent_users_30d = (
            db.query(User).filter(User.crt_date >= thirty_days_ago.date()).count()
        )

        result = {
            "total_trigs": total_trigs,
            "total_members": total_members if total_members else 0,
            "total_logs": total_logs,
            "total_photos": total_photos,
            "recent_logs_7d": recent_logs_7d,
            "recent_users_30d": recent_users_30d,
        }

    return result
