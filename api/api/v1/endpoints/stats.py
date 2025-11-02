"""
Site-wide statistics endpoint with Redis caching.
"""

from datetime import datetime, timedelta

from fastapi import APIRouter, Depends
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
    - total_trigs: Total number of trigpoints
    - total_users: Total number of registered users
    - total_logs: Total number of visit logs
    - total_photos: Total number of photos
    - recent_logs_7d: Number of logs in last 7 days
    - recent_users_30d: Number of users joined in last 30 days

    This endpoint is expensive to compute, so results are cached in Redis for 60 minutes.
    Cache is automatically invalidated when logs, photos, or users are created.
    """
    # Basic counts
    total_trigs = db.query(Trig).count()
    total_users = db.query(User).count()
    total_logs = db.query(TLog).count()
    total_photos = db.query(TPhoto).filter(TPhoto.deleted_ind != "Y").count()

    # Recent activity
    seven_days_ago = datetime.now() - timedelta(days=7)
    recent_logs_7d = db.query(TLog).filter(TLog.upd_timestamp >= seven_days_ago).count()

    thirty_days_ago = datetime.now() - timedelta(days=30)
    recent_users_30d = (
        db.query(User).filter(User.crt_date >= thirty_days_ago.date()).count()
    )

    result = {
        "total_trigs": total_trigs,
        "total_users": total_users,
        "total_logs": total_logs,
        "total_photos": total_photos,
        "recent_logs_7d": recent_logs_7d,
        "recent_users_30d": recent_users_30d,
    }

    return result
