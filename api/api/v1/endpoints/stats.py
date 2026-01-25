"""
Site-wide statistics endpoint with Redis caching.
"""

from datetime import datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from api.api.deps import get_db
from api.api.lifecycle import openapi_lifecycle
from api.utils.cache_decorator import cached

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

    # Use pg_class for fast approximate counts on large tables (trigs, logs)
    # These are much faster and usually accurate enough for dashboard stats
    approx_stats = db.execute(text("""
        SELECT
            (SELECT reltuples::bigint FROM pg_class c
             JOIN pg_namespace n ON c.relnamespace = n.oid
             WHERE relname = 'trig' AND n.nspname = current_schema()) as total_trigs,
            (SELECT reltuples::bigint FROM pg_class c
             JOIN pg_namespace n ON c.relnamespace = n.oid
             WHERE relname = 'tlog' AND n.nspname = current_schema()) as total_logs
        """)).first()

    total_trigs = int(approx_stats[0]) if approx_stats and approx_stats[0] else 0
    total_logs = int(approx_stats[1]) if approx_stats and approx_stats[1] else 0

    # Use exact count for members from user_activity_summary view
    # Falls back to 0 if view doesn't exist (e.g., in test environments)
    try:
        total_members = (
            db.execute(text("SELECT COUNT(*) FROM user_activity_summary")).scalar() or 0
        )
    except Exception:
        total_members = 0

    # Exact count for photos (filtered by deleted_ind)
    total_photos = (
        db.execute(
            text("SELECT COUNT(*) FROM tphoto WHERE deleted_ind != 'Y'")
        ).scalar()
        or 0
    )

    # Recent activity counts
    recent_logs_7d = (
        db.execute(
            text("SELECT COUNT(*) FROM tlog WHERE upd_timestamp >= :seven_days_ago"),
            {"seven_days_ago": seven_days_ago},
        ).scalar()
        or 0
    )

    recent_users_30d = (
        db.execute(
            text('SELECT COUNT(*) FROM "user" WHERE crt_date >= :thirty_days_ago'),
            {"thirty_days_ago": thirty_days_ago.date()},
        ).scalar()
        or 0
    )

    return {
        "total_trigs": total_trigs,
        "total_members": int(total_members),
        "total_logs": total_logs,
        "total_photos": int(total_photos),
        "recent_logs_7d": int(recent_logs_7d),
        "recent_users_30d": int(recent_users_30d),
    }
