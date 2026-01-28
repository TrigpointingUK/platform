"""
CRUD operations for trigstats table.
"""

import math
from decimal import Decimal
from typing import Optional, Tuple

from sqlalchemy import case, func, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from api.core.config import settings
from api.core.logging import get_logger
from api.crud.condition import get_found_condition_codes
from api.models.tphoto import TPhoto
from api.models.trig import Trig
from api.models.trigstats import TrigStats
from api.models.user import TLog
from api.services.cache_service import get_redis_client

logger = get_logger(__name__)

# Redis key for global mean score cache (follows fastapi:{environment}: pattern)
GLOBAL_MEAN_TTL_SECONDS = 86400  # 24 hours

# Attribute IDs for OSGB coordinates in attrval table
ATTR_ID_EASTINGS = 4
ATTR_ID_NORTHINGS = 5


def _calculate_euclidean_distance(e1: float, n1: float, e2: float, n2: float) -> float:
    """Calculate 2D Euclidean distance between two points in metres."""
    return math.sqrt((e2 - e1) ** 2 + (n2 - n1) ** 2)


def _get_attrval_osgb_coords(
    db: Session, trig_id: int
) -> Optional[Tuple[float, float]]:
    """
    Get OSGB coordinates from attrval table for a trigpoint.

    Queries the attrval table via attrset_attrval and attrset to find
    eastings (attr_id=4) and northings (attr_id=5) for the given trig.

    Args:
        db: Database session
        trig_id: Trigpoint ID

    Returns:
        Tuple of (eastings, northings) or None if not found
    """
    # Query to get attrval coords for this trig
    # attr_id=4 is eastings, attr_id=5 is northings
    result = db.execute(
        text("""
            SELECT av.attr_id, av.value_double
            FROM attrval av
            INNER JOIN attrset_attrval aa ON aa.attrval_id = av.id
            INNER JOIN attrset s ON aa.attrset_id = s.id
            WHERE s.trig_id = :trig_id
            AND av.attr_id IN (:attr_eastings, :attr_northings)
            """),
        {
            "trig_id": trig_id,
            "attr_eastings": ATTR_ID_EASTINGS,
            "attr_northings": ATTR_ID_NORTHINGS,
        },
    ).fetchall()

    if not result or len(result) < 2:
        return None

    eastings = None
    northings = None

    for row in result:
        attr_id = row[0]
        value = row[1]
        if value is None:
            continue
        try:
            coord_value = float(value)
            if attr_id == ATTR_ID_EASTINGS:
                eastings = coord_value
            elif attr_id == ATTR_ID_NORTHINGS:
                northings = coord_value
        except (ValueError, TypeError):
            continue

    if eastings is None or northings is None:
        return None

    return (eastings, northings)


def calculate_coordinate_distances(
    db: Session, trig_id: int
) -> Tuple[Optional[Decimal], Optional[Decimal]]:
    """
    Calculate coordinate discrepancy distances for a trigpoint.

    Returns two distances:
    1. dist_wgs_osgb: Distance between WGS84 coords (transformed via OSTN15)
       and the stored OSGB coords in trig table
    2. dist_osgb_osgb: Distance between trig.osgb* coords and attrval OSGB coords

    Args:
        db: Database session
        trig_id: Trigpoint ID

    Returns:
        Tuple of (dist_wgs_osgb, dist_osgb_osgb), each may be None if
        calculation is not possible (e.g., missing data, Irish grid)
    """
    # Get the trig record
    trig = db.query(Trig).filter(Trig.id == trig_id).first()
    if not trig:
        return (None, None)

    dist_wgs_osgb: Optional[Decimal] = None
    dist_osgb_osgb: Optional[Decimal] = None

    # Get stored OSGB coords from trig table
    try:
        trig_eastings = float(trig.osgb_eastings)
        trig_northings = float(trig.osgb_northings)
    except (ValueError, TypeError):
        logger.warning(
            "Cannot parse trig OSGB coords",
            extra={"trig_id": trig_id},
        )
        return (None, None)

    # Calculate dist_wgs_osgb: WGS84 -> OSTN15 -> compare with trig.osgb*
    # Only for GB trigs (Irish grid uses different transformation)
    # Irish grid uses single letter (e.g., "O 12345"), GB uses two (e.g., "TQ 12345")
    gridref = str(trig.osgb_gridref) if trig.osgb_gridref else ""
    is_irish_grid = len(gridref) >= 2 and gridref[1] == " "

    if not is_irish_grid:
        try:
            from api.services.coordinate_service import convert_wgs84_to_osgb

            wgs_lat = float(trig.wgs_lat)
            wgs_lon = float(trig.wgs_long)

            # Transform WGS84 to OSGB via OSTN15
            transformed_e, transformed_n, _ = convert_wgs84_to_osgb(wgs_lon, wgs_lat)

            # Calculate Euclidean distance
            distance = _calculate_euclidean_distance(
                transformed_e, transformed_n, trig_eastings, trig_northings
            )
            # Cap at 100km - larger values indicate bad data (or test fixtures)
            # DECIMAL(10,4) can only store up to 999999.9999
            if distance <= 100000:
                dist_wgs_osgb = Decimal(str(round(distance, 4)))

        except Exception as e:
            logger.warning(
                "Failed to calculate dist_wgs_osgb",
                extra={"trig_id": trig_id, "error": str(e)},
            )

    # Calculate dist_osgb_osgb: trig.osgb* vs attrval coords
    attrval_coords = _get_attrval_osgb_coords(db, trig_id)
    if attrval_coords:
        attr_eastings, attr_northings = attrval_coords
        try:
            distance = _calculate_euclidean_distance(
                trig_eastings, trig_northings, attr_eastings, attr_northings
            )
            # Cap at 100km - larger values indicate bad data (or test fixtures)
            if distance <= 100000:
                dist_osgb_osgb = Decimal(str(round(distance, 4)))
        except Exception as e:
            logger.warning(
                "Failed to calculate dist_osgb_osgb",
                extra={"trig_id": trig_id, "error": str(e)},
            )

    return (dist_wgs_osgb, dist_osgb_osgb)


def _get_global_mean_cache_key() -> str:
    """Get the Redis cache key for global mean score, namespaced by environment."""
    environment = settings.ENVIRONMENT.lower()
    return f"fastapi:{environment}:trigstats:global_mean"


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
    # Only include published logs (exclude drafts)
    result = (
        db.query(
            func.sum(TLog.score),
            func.count(TLog.score),
        )
        .filter(TLog.score.isnot(None))
        .filter(TLog.status == "P")
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
    - found_last, found_count (conditions with green/yellow log_colour)
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

    # Get "found" condition codes from condition table
    found_conditions = get_found_condition_codes(db)

    # Use SQL aggregates for efficient calculation - single query for all stats
    # Only include published logs (exclude drafts)
    log_stats = (
        db.query(
            func.count(TLog.id).label("logged_count"),
            func.min(TLog.date).label("logged_first"),
            func.max(TLog.date).label("logged_last"),
            func.sum(TLog.score).label("total_score"),
            func.count(TLog.score).label("score_count"),
            # Found stats: count and last date for conditions with green/yellow log_colour
            func.count(
                case((TLog.condition.in_(found_conditions), TLog.id), else_=None)
            ).label("found_count"),
            func.max(
                case((TLog.condition.in_(found_conditions), TLog.date), else_=None)
            ).label("found_last"),
        )
        .filter(TLog.trig_id == trig_id)
        .filter(TLog.status == "P")  # Only published logs
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

    # Query photo count (only from published logs)
    photo_count = (
        db.query(func.count(TPhoto.id))
        .join(TLog, TPhoto.tlog_id == TLog.id)
        .filter(TLog.trig_id == trig_id, TPhoto.deleted_ind != "Y")
        .filter(TLog.status == "P")  # Only published logs
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

    # Calculate coordinate discrepancy distances
    dist_wgs_osgb, dist_osgb_osgb = calculate_coordinate_distances(db, trig_id)

    t3b = time.time()
    logger.info(f"update_trigstats: coordinate distances took {t3b - t3:.3f}s")

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
        dist_wgs_osgb=dist_wgs_osgb,
        dist_osgb_osgb=dist_osgb_osgb,
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
            "dist_wgs_osgb": stmt.excluded.dist_wgs_osgb,
            "dist_osgb_osgb": stmt.excluded.dist_osgb_osgb,
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


def update_trigstats_distances(db: Session, trig_id: int) -> None:
    """
    Update only the coordinate distance columns for a trigpoint.

    Called when a trig is created or updated (coordinates may have changed).
    If a trigstats row exists, updates only the distance columns.
    If no trigstats row exists, creates one with zeros for stats and the
    calculated distances.

    Args:
        db: Database session
        trig_id: Trigpoint ID
    """
    # Calculate coordinate distances
    dist_wgs_osgb, dist_osgb_osgb = calculate_coordinate_distances(db, trig_id)

    # Check if trigstats row exists
    existing = db.query(TrigStats).filter(TrigStats.id == trig_id).first()

    if existing:
        # Update only distance columns
        existing.dist_wgs_osgb = dist_wgs_osgb  # type: ignore
        existing.dist_osgb_osgb = dist_osgb_osgb  # type: ignore
        db.commit()
        logger.debug(
            "Updated trigstats distances",
            extra={
                "trig_id": trig_id,
                "dist_wgs_osgb": str(dist_wgs_osgb) if dist_wgs_osgb else None,
                "dist_osgb_osgb": str(dist_osgb_osgb) if dist_osgb_osgb else None,
            },
        )
    else:
        # Create trigstats row with zero stats but calculated distances
        stmt = pg_insert(TrigStats).values(
            id=trig_id,
            logged_first=None,
            logged_last=None,
            logged_count=0,
            found_last=None,
            found_count=0,
            photo_count=0,
            score_mean=Decimal("0"),
            score_baysian=Decimal("0"),
            dist_wgs_osgb=dist_wgs_osgb,
            dist_osgb_osgb=dist_osgb_osgb,
        )
        # Use ON CONFLICT in case of race condition
        stmt = stmt.on_conflict_do_update(
            index_elements=["id"],
            set_={
                "dist_wgs_osgb": stmt.excluded.dist_wgs_osgb,
                "dist_osgb_osgb": stmt.excluded.dist_osgb_osgb,
            },
        )
        db.execute(stmt)
        db.commit()
        logger.debug(
            "Created trigstats row with distances",
            extra={
                "trig_id": trig_id,
                "dist_wgs_osgb": str(dist_wgs_osgb) if dist_wgs_osgb else None,
                "dist_osgb_osgb": str(dist_osgb_osgb) if dist_osgb_osgb else None,
            },
        )
