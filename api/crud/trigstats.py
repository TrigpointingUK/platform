"""
CRUD operations for trigstats table.
"""

from decimal import Decimal
from typing import Optional

from sqlalchemy import case, func
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from api.core.config import settings
from api.core.logging import get_logger
from api.models.tphoto import TPhoto
from api.models.trigstats import TrigStats
from api.models.user import TLog
from api.services.cache_service import get_redis_client

logger = get_logger(__name__)

# Redis key for global mean score cache (follows fastapi:{environment}: pattern)
GLOBAL_MEAN_TTL_SECONDS = 86400  # 24 hours


def _get_global_mean_cache_key() -> str:
    """Get the Redis cache key for global mean score, namespaced by environment."""
    environment = settings.ENVIRONMENT.lower()
    return f"fastapi:{environment}:trigstats:global_mean"


# Condition codes that indicate the trig was "found" (Good or Slightly damaged)
FOUND_CONDITIONS = {"G", "S"}

# Minimum votes for Bayesian calculation (wm in the formula)
BAYESIAN_MIN_VOTES = 1


def get_trigstats_by_id(db: Session, trig_id: int) -> Optional[TrigStats]:
    """
    Get trigstats by trig ID.

    Args:
        db: Database session
        trig_id: Trigpoint ID (primary key in trigstats)

    Returns:
        TrigStats object or None if not found
    """
    return db.query(TrigStats).filter(TrigStats.id == trig_id).first()


def get_global_mean_score(db: Session) -> Decimal:
    """
    Get the global mean score across all logs.

    Uses Redis cache with 24-hour TTL to avoid expensive full table scans.
    Falls back to database query on cache miss.

    Args:
        db: Database session

    Returns:
        Global mean score as Decimal, or Decimal("0") if no logs exist
    """
    # Try Redis cache first
    cache_key = _get_global_mean_cache_key()
    client = get_redis_client()
    if client:
        try:
            cached_value = client.get(cache_key)
            if cached_value is not None:
                logger.debug(
                    "Global mean score cache hit",
                    extra={"cached_value": cached_value},
                )
                return Decimal(str(cached_value))
        except Exception as e:
            logger.warning(
                "Failed to get global mean from cache",
                extra={"error": str(e)},
            )

    # Cache miss - query database
    result = (
        db.query(
            func.sum(TLog.score),
            func.count(TLog.score),
        )
        .filter(TLog.score.isnot(None))
        .first()
    )

    if result is None:
        total_score = 0
        total_count = 0
    else:
        total_score = result[0] if result[0] is not None else 0
        total_count = result[1] if result[1] is not None else 0

    if total_count == 0:
        global_mean = Decimal("0")
    else:
        global_mean = Decimal(str(total_score)) / Decimal(str(total_count))

    # Cache the result
    if client:
        try:
            client.setex(
                cache_key,
                GLOBAL_MEAN_TTL_SECONDS,
                str(global_mean),
            )
            logger.debug(
                "Global mean score cached",
                extra={"global_mean": str(global_mean)},
            )
        except Exception as e:
            logger.warning(
                "Failed to cache global mean score",
                extra={"error": str(e)},
            )

    return global_mean


def update_trigstats(db: Session, trig_id: int) -> Optional[TrigStats]:
    """
    Update the trigstats row for a specific trigpoint.

    Recalculates all statistics from tlog and tphoto tables using efficient
    SQL aggregates:
    - logged_first, logged_last, logged_count
    - found_last, found_count (conditions 'G' or 'S')
    - photo_count
    - score_mean, score_baysian

    Args:
        db: Database session
        trig_id: Trigpoint ID

    Returns:
        Updated TrigStats object, or None if no logs exist for this trig
    """
    import time

    start_time = time.time()

    # Use SQL aggregates for efficient calculation - single query for all stats
    log_stats = (
        db.query(
            func.count(TLog.id).label("logged_count"),
            func.min(TLog.date).label("logged_first"),
            func.max(TLog.date).label("logged_last"),
            func.sum(TLog.score).label("total_score"),
            func.count(TLog.score).label("score_count"),
            # Found stats: count and last date for 'G' or 'S' conditions
            func.count(
                case((TLog.condition.in_(FOUND_CONDITIONS), TLog.id), else_=None)
            ).label("found_count"),
            func.max(
                case((TLog.condition.in_(FOUND_CONDITIONS), TLog.date), else_=None)
            ).label("found_last"),
        )
        .filter(TLog.trig_id == trig_id)
        .first()
    )

    t1 = time.time()
    logger.info(f"update_trigstats: log_stats query took {t1 - start_time:.3f}s")

    if log_stats is None:
        logged_count = 0
    else:
        logged_count = log_stats.logged_count or 0

    if logged_count == 0:
        # No logs for this trig - delete trigstats row if it exists
        existing = db.query(TrigStats).filter(TrigStats.id == trig_id).first()
        if existing:
            db.delete(existing)
            db.commit()
            logger.debug(
                "Deleted trigstats for trig with no logs",
                extra={"trig_id": trig_id},
            )
        return None

    # At this point log_stats is guaranteed to be non-None (we returned above if None)
    assert log_stats is not None

    logged_first = log_stats.logged_first
    logged_last = log_stats.logged_last
    total_score = log_stats.total_score or 0
    score_count = log_stats.score_count or 0
    found_count = log_stats.found_count or 0
    found_last = log_stats.found_last

    # Query photo count
    photo_count = (
        db.query(func.count(TPhoto.id))
        .join(TLog, TPhoto.tlog_id == TLog.id)
        .filter(TLog.trig_id == trig_id, TPhoto.deleted_ind != "Y")
        .scalar()
        or 0
    )

    t2 = time.time()
    logger.info(f"update_trigstats: photo_count query took {t2 - t1:.3f}s")

    # Calculate score mean for this trig
    if score_count > 0:
        score_mean = Decimal(str(total_score)) / Decimal(str(score_count))
    else:
        score_mean = Decimal("0")

    # Get global mean for Bayesian calculation
    global_mean = get_global_mean_score(db)

    t3 = time.time()
    logger.info(f"update_trigstats: global_mean took {t3 - t2:.3f}s")

    # Bayesian weighted rating formula:
    # score_baysian = (wv / (wv + wm)) * wR + (wm / (wv + wm)) * wC
    # where:
    #   wv = number of votes for this trig (logged_count)
    #   wm = minimum votes required (BAYESIAN_MIN_VOTES)
    #   wR = mean vote for this trig (score_mean)
    #   wC = mean vote across whole database (global_mean)
    wv = Decimal(str(logged_count))
    wm = Decimal(str(BAYESIAN_MIN_VOTES))
    wR = score_mean
    wC = global_mean

    if wv + wm > 0:
        score_baysian = (wv / (wv + wm)) * wR + (wm / (wv + wm)) * wC
    else:
        score_baysian = Decimal("0")

    # Upsert the trigstats row using PostgreSQL ON CONFLICT
    # Date columns are nullable - use NULL for "never logged/found"
    stmt = pg_insert(TrigStats).values(
        id=trig_id,
        logged_first=logged_first,  # NULL if never logged
        logged_last=logged_last,  # NULL if never logged
        logged_count=logged_count,
        found_last=found_last,  # NULL if never found
        found_count=found_count,
        photo_count=photo_count,
        score_mean=round(score_mean, 2),
        score_baysian=round(score_baysian, 2),
    )

    stmt = stmt.on_conflict_do_update(
        index_elements=["id"],
        set_={
            "logged_first": stmt.excluded.logged_first,
            "logged_last": stmt.excluded.logged_last,
            "logged_count": stmt.excluded.logged_count,
            "found_last": stmt.excluded.found_last,
            "found_count": stmt.excluded.found_count,
            "photo_count": stmt.excluded.photo_count,
            "score_mean": stmt.excluded.score_mean,
            "score_baysian": stmt.excluded.score_baysian,
        },
    )

    db.execute(stmt)
    db.commit()

    t4 = time.time()
    logger.info(
        f"update_trigstats: upsert+commit took {t4 - t3:.3f}s, total {t4 - start_time:.3f}s"
    )

    logger.debug(
        "Updated trigstats",
        extra={
            "trig_id": trig_id,
            "logged_count": logged_count,
            "found_count": found_count,
            "photo_count": photo_count,
            "score_mean": str(score_mean),
            "score_baysian": str(score_baysian),
        },
    )

    return get_trigstats_by_id(db, trig_id)
