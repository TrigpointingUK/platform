"""
CRUD operations for tlog table.
"""

from datetime import date as DateType
from typing import Iterable, List, Optional, Tuple

from sqlalchemy import Float, asc, cast, desc, func, text
from sqlalchemy.orm import Session

from api.models.tphoto import TPhoto
from api.models.trig import Trig
from api.models.user import TLog, User
from api.services.cache_invalidator import (
    invalidate_log_caches,
    invalidate_photo_caches,
)

# Import update_trigstats lazily to avoid circular imports
_trigstats_crud = None


def _is_sqlite(db: Session) -> bool:
    """Check if the database engine is SQLite (used for tests)."""
    return "sqlite" in str(db.get_bind().dialect.name).lower()


def _get_trigstats_crud():
    """Lazy import of trigstats crud to avoid circular imports."""
    global _trigstats_crud
    if _trigstats_crud is None:
        from api.crud import trigstats as trigstats_crud

        _trigstats_crud = trigstats_crud
    return _trigstats_crud


# Condition values that indicate the trig condition is "unknown" or "pending"
# and should be updated from user log data
TRIG_CONDITIONS_TO_UPDATE = {"P", "U", "N", "Z", "", None}

# Condition values from tlog that should NOT update the trig
# (i.e., these are also "unknown" or "pending" log conditions)
TLOG_CONDITIONS_TO_SKIP = {"P", "Q", "U", "N", "Z", "", None}


def maybe_update_trig_condition(
    db: Session, *, trig_id: int, tlog_condition: Optional[str]
) -> bool:
    """
    Update trig.condition based on a tlog's condition value.

    Logic:
    - If trig.condition is in ['P', 'U', 'N', 'Z', '', null] (unknown/pending)
    - AND tlog.condition is NOT in ['P', 'Q', 'U', 'N', 'Z', '', null] (known condition)
    - Then update trig.condition with tlog.condition

    Args:
        db: Database session
        trig_id: ID of the trig to potentially update
        tlog_condition: The condition value from the tlog

    Returns:
        True if the trig condition was updated, False otherwise
    """
    # Check if tlog condition should trigger an update
    if tlog_condition in TLOG_CONDITIONS_TO_SKIP:
        return False

    # Get the trig and check its current condition
    trig = db.query(Trig).filter(Trig.id == trig_id).first()
    if not trig:
        return False

    # Check if trig condition should be updated
    current_condition = str(trig.condition) if trig.condition else None
    if current_condition not in TRIG_CONDITIONS_TO_UPDATE:
        return False

    # Update the trig condition
    # Type ignore needed as SQLAlchemy Column assignment works at runtime
    trig.condition = tlog_condition  # type: ignore[assignment]
    db.add(trig)
    # Note: We don't commit here - let the caller handle the transaction

    return True


def get_log_by_id(db: Session, log_id: int) -> Optional[TLog]:
    return db.query(TLog).filter(TLog.id == log_id).first()


def get_existing_log_for_user_trig_date(
    db: Session,
    *,
    user_id: int,
    trig_id: int,
    date: DateType,
    exclude_log_id: Optional[int] = None,
) -> Optional[TLog]:
    """Check if user already has a published log for this trig on this date.

    Only checks published logs (status='P'), not drafts.
    """
    q = db.query(TLog).filter(
        TLog.user_id == user_id,
        TLog.trig_id == trig_id,
        TLog.date == date,
        TLog.status == "P",  # Only check published logs
    )
    if exclude_log_id:
        q = q.filter(TLog.id != exclude_log_id)
    return q.first()


def list_logs_filtered(
    db: Session,
    *,
    trig_id: Optional[int] = None,
    user_id: Optional[int] = None,
    order: Optional[str] = None,
    skip: int = 0,
    limit: int = 10,
    center_lat: Optional[float] = None,
    center_lon: Optional[float] = None,
    max_km: Optional[float] = None,
    category_codes: Optional[List[str]] = None,
    area_id: Optional[int] = None,
    from_date: Optional[DateType] = None,
    to_date: Optional[DateType] = None,
    exclude_found_by_user_id: Optional[int] = None,
    only_found_by_user_id: Optional[int] = None,
    include_drafts: bool = False,
) -> List[TLog]:
    from api.crud.trig import _get_type_ids_for_categories

    q = db.query(TLog)

    # By default, exclude draft logs from listings
    if not include_drafts:
        q = q.filter(TLog.status == "P")

    # Join to trig table if we need to filter by trig properties
    needs_trig_join = (
        center_lat is not None
        or center_lon is not None
        or max_km is not None
        or category_codes is not None
        or area_id is not None
    )

    if needs_trig_join:
        q = q.join(Trig, TLog.trig_id == Trig.id)

    if trig_id is not None:
        q = q.filter(TLog.trig_id == trig_id)
    if user_id is not None:
        q = q.filter(TLog.user_id == user_id)

    # Filter by category codes (trigpoint type categories)
    if category_codes:
        type_id_list = _get_type_ids_for_categories(db, category_codes)
        if type_id_list:
            q = q.filter(Trig.type_id.in_(type_id_list))
        else:
            # No matching categories, return empty
            q = q.filter(Trig.id == -1)

    # Filter by area using trig_area table
    if area_id is not None and not _is_sqlite(db):
        area_subquery = text(
            "SELECT trig_id FROM trig_area WHERE area_id = :area_id"
        ).bindparams(area_id=area_id)
        q = q.filter(Trig.id.in_(area_subquery))

    # Filter by date range
    if from_date is not None:
        q = q.filter(TLog.date >= from_date)
    if to_date is not None:
        q = q.filter(TLog.date <= to_date)

    # Exclude logs for trigpoints already found by user (show only unlogged trigs)
    if exclude_found_by_user_id is not None:
        found_trigs_subquery = (
            db.query(TLog.trig_id)
            .filter(TLog.user_id == exclude_found_by_user_id)
            .distinct()
            .subquery()
        )
        q = q.filter(~TLog.trig_id.in_(found_trigs_subquery))  # type: ignore[arg-type]

    # Include ONLY logs for trigpoints found by user (show only logged trigs)
    if only_found_by_user_id is not None:
        found_trigs_subquery = (
            db.query(TLog.trig_id)
            .filter(TLog.user_id == only_found_by_user_id)
            .distinct()
            .subquery()
        )
        q = q.filter(TLog.trig_id.in_(found_trigs_subquery))  # type: ignore[arg-type]

    # Filter by distance from center point
    if center_lat is not None and center_lon is not None and max_km is not None:
        # Use haversine formula for distance calculation
        lat1_rad = func.radians(center_lat)
        lat2_rad = func.radians(Trig.wgs_lat)
        lon1_rad = func.radians(center_lon)
        lon2_rad = func.radians(Trig.wgs_long)

        dlat = lat2_rad - lat1_rad
        dlon = lon2_rad - lon1_rad

        a = func.sin(dlat / 2) * func.sin(dlat / 2) + func.cos(lat1_rad) * func.cos(
            lat2_rad
        ) * func.sin(dlon / 2) * func.sin(dlon / 2)
        c = 2 * func.atan2(func.sqrt(a), func.sqrt(1 - a))
        distance_expr = cast(6371000 * c, Float)  # Earth radius in metres

        # Apply distance filter
        q = q.filter(distance_expr < max_km * 1000)

    # Default ordering newest first by (date, time, id)
    if order:
        # support order fields with optional '-' prefix
        directives: List[Tuple[str, bool]] = []
        for token in order.split(","):
            token = token.strip()
            if not token:
                continue
            desc_ind = token.startswith("-")
            field = token[1:] if desc_ind else token
            directives.append((field, desc_ind))

        for field, is_desc in directives:
            col = getattr(TLog, field, None)
            if col is None:
                continue
            q = q.order_by(desc(col) if is_desc else asc(col))
    else:
        q = q.order_by(desc(TLog.date), desc(TLog.time), desc(TLog.id))

    return q.offset(skip).limit(limit).all()


def list_recent_activity_logs(
    db: Session,
    *,
    min_count: int = 10,
) -> List[TLog]:
    """Return all published logs from today and yesterday, with a guaranteed
    minimum of *min_count* rows.  If today+yesterday yields fewer than
    *min_count*, older logs are fetched to fill the gap.
    """
    from datetime import timedelta

    yesterday = DateType.today() - timedelta(days=1)

    recent = (
        db.query(TLog)
        .filter(TLog.status == "P", TLog.date >= yesterday)
        .order_by(desc(TLog.date), desc(TLog.time), desc(TLog.id))
        .all()
    )

    if len(recent) >= min_count:
        return recent

    shortfall = min_count - len(recent)

    backfill = (
        db.query(TLog)
        .filter(TLog.status == "P", TLog.date < yesterday)
        .order_by(desc(TLog.date), desc(TLog.time), desc(TLog.id))
        .limit(shortfall)
        .all()
    )

    return recent + backfill


def count_logs_filtered(
    db: Session,
    *,
    trig_id: Optional[int] = None,
    user_id: Optional[int] = None,
    center_lat: Optional[float] = None,
    center_lon: Optional[float] = None,
    max_km: Optional[float] = None,
    category_codes: Optional[List[str]] = None,
    area_id: Optional[int] = None,
    from_date: Optional[DateType] = None,
    to_date: Optional[DateType] = None,
    exclude_found_by_user_id: Optional[int] = None,
    only_found_by_user_id: Optional[int] = None,
    include_drafts: bool = False,
) -> int:
    from api.crud.trig import _get_type_ids_for_categories

    q = db.query(func.count(TLog.id))

    # By default, exclude draft logs from counts
    if not include_drafts:
        q = q.filter(TLog.status == "P")

    # Join to trig table if we need to filter by trig properties
    needs_trig_join = (
        center_lat is not None
        or center_lon is not None
        or max_km is not None
        or category_codes is not None
        or area_id is not None
    )

    if needs_trig_join:
        q = q.join(Trig, TLog.trig_id == Trig.id)

    if trig_id is not None:
        q = q.filter(TLog.trig_id == trig_id)
    if user_id is not None:
        q = q.filter(TLog.user_id == user_id)

    # Filter by category codes (trigpoint type categories)
    if category_codes:
        type_id_list = _get_type_ids_for_categories(db, category_codes)
        if type_id_list:
            q = q.filter(Trig.type_id.in_(type_id_list))
        else:
            # No matching categories, return 0
            return 0

    # Filter by area using trig_area table
    if area_id is not None and not _is_sqlite(db):
        area_subquery = text(
            "SELECT trig_id FROM trig_area WHERE area_id = :area_id"
        ).bindparams(area_id=area_id)
        q = q.filter(Trig.id.in_(area_subquery))

    # Filter by date range
    if from_date is not None:
        q = q.filter(TLog.date >= from_date)
    if to_date is not None:
        q = q.filter(TLog.date <= to_date)

    # Exclude logs for trigpoints already found by user (show only unlogged trigs)
    if exclude_found_by_user_id is not None:
        found_trigs_subquery = (
            db.query(TLog.trig_id)
            .filter(TLog.user_id == exclude_found_by_user_id)
            .distinct()
            .subquery()
        )
        q = q.filter(~TLog.trig_id.in_(found_trigs_subquery))  # type: ignore[arg-type]

    # Include ONLY logs for trigpoints found by user (show only logged trigs)
    if only_found_by_user_id is not None:
        found_trigs_subquery = (
            db.query(TLog.trig_id)
            .filter(TLog.user_id == only_found_by_user_id)
            .distinct()
            .subquery()
        )
        q = q.filter(TLog.trig_id.in_(found_trigs_subquery))  # type: ignore[arg-type]

    # Filter by distance from center point
    if center_lat is not None and center_lon is not None and max_km is not None:
        # Use haversine formula for distance calculation
        lat1_rad = func.radians(center_lat)
        lat2_rad = func.radians(Trig.wgs_lat)
        lon1_rad = func.radians(center_lon)
        lon2_rad = func.radians(Trig.wgs_long)

        dlat = lat2_rad - lat1_rad
        dlon = lon2_rad - lon1_rad

        a = func.sin(dlat / 2) * func.sin(dlat / 2) + func.cos(lat1_rad) * func.cos(
            lat2_rad
        ) * func.sin(dlon / 2) * func.sin(dlon / 2)
        c = 2 * func.atan2(func.sqrt(a), func.sqrt(1 - a))
        distance_expr = cast(6371000 * c, Float)  # Earth radius in metres

        # Apply distance filter
        q = q.filter(distance_expr < max_km * 1000)

    return int(q.scalar() or 0)


def create_log(
    db: Session,
    *,
    trig_id: int,
    user_id: int,
    values: dict,
) -> TLog:
    # Remove trig_id and user_id from values to avoid duplicate keyword arguments
    # These are explicitly set via function parameters
    log_values = {k: v for k, v in values.items() if k not in ("trig_id", "user_id")}
    log = TLog(trig_id=trig_id, user_id=user_id, **log_values)
    db.add(log)

    # Check if trig condition should be updated based on log condition
    tlog_condition = log_values.get("condition")
    maybe_update_trig_condition(db, trig_id=trig_id, tlog_condition=tlog_condition)

    db.commit()
    db.refresh(log)

    # Invalidate related caches
    invalidate_log_caches(trig_id=trig_id, user_id=user_id, log_id=int(log.id))

    # Update trigstats for this trig
    _get_trigstats_crud().update_trigstats(db, trig_id)

    return log


def update_log(db: Session, *, log_id: int, updates: dict) -> Optional[TLog]:
    log = db.query(TLog).filter(TLog.id == log_id).first()
    if not log:
        return None
    for key, value in updates.items():
        if hasattr(log, key):
            setattr(log, key, value)
    db.add(log)

    # Check if trig condition should be updated based on the updated log condition
    if "condition" in updates:
        maybe_update_trig_condition(
            db, trig_id=int(log.trig_id), tlog_condition=updates["condition"]
        )

    db.commit()
    db.refresh(log)

    # Invalidate related caches
    invalidate_log_caches(
        trig_id=int(log.trig_id), user_id=int(log.user_id), log_id=log_id
    )

    # Update trigstats for this trig
    _get_trigstats_crud().update_trigstats(db, int(log.trig_id))

    return log


def delete_log_hard(db: Session, *, log_id: int) -> bool:
    log = db.query(TLog).filter(TLog.id == log_id).first()
    if not log:
        return False

    # Store IDs for cache invalidation before deleting
    trig_id = int(log.trig_id)
    user_id = int(log.user_id)

    db.delete(log)
    db.commit()

    # Invalidate related caches
    invalidate_log_caches(trig_id=trig_id, user_id=user_id, log_id=log_id)

    # Update trigstats for this trig
    _get_trigstats_crud().update_trigstats(db, trig_id)

    return True


def soft_delete_photos_for_log(db: Session, *, log_id: int) -> int:
    """Soft delete all photos for a given tlog.

    Sets deleted_ind='Y' and nullifies tlog_id to explicitly break the FK
    reference before the parent tlog is deleted. This ensures referential
    integrity is maintained by the application, with FK constraints serving
    as a safety net rather than the primary mechanism.

    Returns count of photos soft-deleted.
    """
    photos: Iterable[TPhoto] = (
        db.query(TPhoto)
        .filter(TPhoto.tlog_id == log_id, TPhoto.deleted_ind != "Y")
        .all()
    )
    count = 0

    # Get trig_id and user_id from the log for cache invalidation
    from api.models.user import TLog as TLogModel

    log = db.query(TLogModel).filter(TLogModel.id == log_id).first()

    for p in photos:
        setattr(p, "deleted_ind", "Y")
        setattr(p, "tlog_id", None)  # Explicitly break FK before parent deletion
        db.add(p)
        count += 1
    db.commit()

    # Invalidate photo-related caches if any photos were deleted
    if count > 0 and log:
        invalidate_photo_caches(
            trig_id=int(log.trig_id), user_id=int(log.user_id), log_id=log_id
        )
        # Update trigstats for this trig (photo_count changed)
        _get_trigstats_crud().update_trigstats(db, int(log.trig_id))

    return count


def get_trig_count(db: Session, trig_id: int) -> int:
    """Get count of rows matching trig_id in tlog table."""
    return db.query(func.count(TLog.id)).filter(TLog.trig_id == trig_id).scalar() or 0


def search_logs_by_text(
    db: Session, text_pattern: str, skip: int = 0, limit: int = 100
) -> List[TLog]:
    """
    Search logs by comment text using substring matching.

    Args:
        db: Database session
        text_pattern: Text pattern to search for (case-insensitive)
        skip: Number of records to skip
        limit: Maximum number of records to return

    Returns:
        List of TLog objects
    """
    return (
        db.query(TLog)
        .filter(TLog.comment.ilike(f"%{text_pattern}%"))
        .order_by(desc(TLog.date), desc(TLog.time), desc(TLog.id))
        .offset(skip)
        .limit(limit)
        .all()
    )


def count_logs_by_text(db: Session, text_pattern: str) -> int:
    """
    Count logs matching comment text pattern.

    Args:
        db: Database session
        text_pattern: Text pattern to search for (case-insensitive)

    Returns:
        Count of matching logs
    """
    return (
        db.query(func.count(TLog.id))
        .filter(TLog.comment.ilike(f"%{text_pattern}%"))
        .scalar()
        or 0
    )


def search_logs_by_regex(
    db: Session, regex_pattern: str, skip: int = 0, limit: int = 100
) -> List[TLog]:
    """
    Search logs by comment text using regex matching.

    Args:
        db: Database session
        regex_pattern: Regex pattern to search for (PostgreSQL ~* case-insensitive)
        skip: Number of records to skip
        limit: Maximum number of records to return

    Returns:
        List of TLog objects
    """
    # PostgreSQL case-insensitive regex operator
    return (
        db.query(TLog)
        .filter(TLog.comment.op("~*")(regex_pattern))
        .order_by(desc(TLog.date), desc(TLog.time), desc(TLog.id))
        .offset(skip)
        .limit(limit)
        .all()
    )


def count_logs_by_regex(db: Session, regex_pattern: str) -> int:
    """
    Count logs matching regex pattern.

    Args:
        db: Database session
        regex_pattern: Regex pattern to search for (PostgreSQL ~* case-insensitive)

    Returns:
        Count of matching logs
    """
    # PostgreSQL case-insensitive regex operator
    return (
        db.query(func.count(TLog.id))
        .filter(TLog.comment.op("~*")(regex_pattern))
        .scalar()
        or 0
    )


def search_logs_by_text_with_names(
    db: Session, text_pattern: str, skip: int = 0, limit: int = 100
) -> List[Tuple[TLog, Optional[str], Optional[str]]]:
    """
    Search logs by comment text with trig and user names joined.

    Args:
        db: Database session
        text_pattern: Text pattern to search for (case-insensitive)
        skip: Number of records to skip
        limit: Maximum number of records to return

    Returns:
        List of tuples (TLog, trig_name, user_name)
    """
    rows = (
        db.query(TLog, Trig.name, User.name)
        .outerjoin(Trig, TLog.trig_id == Trig.id)
        .outerjoin(User, TLog.user_id == User.id)
        .filter(TLog.comment.ilike(f"%{text_pattern}%"))
        .order_by(desc(TLog.date), desc(TLog.time), desc(TLog.id))
        .offset(skip)
        .limit(limit)
        .all()
    )
    return [
        (
            log,
            trig_name if trig_name is not None else None,
            user_name if user_name is not None else None,
        )
        for log, trig_name, user_name in rows
    ]


def search_logs_by_regex_with_names(
    db: Session, regex_pattern: str, skip: int = 0, limit: int = 100
) -> List[Tuple[TLog, Optional[str], Optional[str]]]:
    """
    Search logs by regex pattern with trig and user names joined.

    Args:
        db: Database session
        regex_pattern: Regex pattern to search for (PostgreSQL ~* case-insensitive)
        skip: Number of results to skip
        limit: Maximum number of results to return

    Returns:
        List of tuples (TLog, trig_name, user_name)
    """
    rows = (
        db.query(TLog, Trig.name, User.name)
        .outerjoin(Trig, TLog.trig_id == Trig.id)
        .outerjoin(User, TLog.user_id == User.id)
        .filter(TLog.comment.op("~*")(regex_pattern))
        .order_by(desc(TLog.date), desc(TLog.time), desc(TLog.id))
        .offset(skip)
        .limit(limit)
        .all()
    )
    return [
        (
            log,
            trig_name if trig_name is not None else None,
            user_name if user_name is not None else None,
        )
        for log, trig_name, user_name in rows
    ]


# ============================================================================
# Admin: Logs Needing Attention
# ============================================================================


def get_orphaned_logs_count(db: Session) -> int:
    """
    Count logs that reference deleted trigpoints (trig_id not in trig table).
    """
    return (
        db.query(func.count(TLog.id))
        .outerjoin(Trig, TLog.trig_id == Trig.id)
        .filter(Trig.id.is_(None))
        .scalar()
        or 0
    )


def get_duplicate_logs_count(db: Session) -> int:
    """
    Count duplicate log entries where user_id, trig_id, date, time, condition, comment
    are identical and no photos have been uploaded.

    Returns the count of logs that would be deleted (total - unique groups).
    """
    from api.models.tphoto import TPhoto

    # Subquery to find logs with photos
    logs_with_photos = (
        db.query(TPhoto.tlog_id).filter(TPhoto.deleted_ind != "Y").distinct().subquery()
    )

    # Subquery to find duplicate groups (logs with same user, trig, date, no photos)
    # Duplicates are detected by user_id + trig_id + date only
    duplicate_groups = (
        db.query(
            TLog.user_id,
            TLog.trig_id,
            TLog.date,
            func.count(TLog.id).label("cnt"),
        )
        .outerjoin(logs_with_photos, TLog.id == logs_with_photos.c.tlog_id)
        .filter(logs_with_photos.c.tlog_id.is_(None))  # No photos
        .group_by(
            TLog.user_id,
            TLog.trig_id,
            TLog.date,
        )
        .having(func.count(TLog.id) > 1)
        .subquery()
    )

    # Sum up (count - 1) for each duplicate group to get total deletable
    result = db.query(func.sum(duplicate_groups.c.cnt - 1)).scalar()
    return int(result) if result else 0


def get_orphaned_logs(
    db: Session, skip: int = 0, limit: int = 100
) -> List[Tuple[TLog, Optional[str]]]:
    """
    Get logs that reference deleted trigpoints.

    Returns list of tuples (TLog, user_name).
    """
    rows = (
        db.query(TLog, User.name)
        .outerjoin(Trig, TLog.trig_id == Trig.id)
        .outerjoin(User, TLog.user_id == User.id)
        .filter(Trig.id.is_(None))
        .order_by(desc(TLog.date), desc(TLog.time), desc(TLog.id))
        .offset(skip)
        .limit(limit)
        .all()
    )
    return [(log, user_name) for log, user_name in rows]


def get_duplicate_logs(
    db: Session, skip: int = 0, limit: int = 100
) -> List[Tuple[TLog, Optional[str], Optional[str], Optional[str], int]]:
    """
    Get duplicate log entries where user_id, trig_id, and date are identical
    and no photos have been uploaded.

    Duplicates are detected by user_id + trig_id + date only.

    Returns only one log from each duplicate group (the one to delete).
    Returns list of tuples (TLog, trig_name, trig_waypoint, user_name, duplicate_count).
    """
    from api.models.tphoto import TPhoto

    # Subquery to find logs with photos
    logs_with_photos = (
        db.query(TPhoto.tlog_id).filter(TPhoto.deleted_ind != "Y").distinct().subquery()
    )

    # Find all duplicate groups with their counts
    # Duplicates are detected by user_id + trig_id + date only
    duplicate_groups = (
        db.query(
            TLog.user_id,
            TLog.trig_id,
            TLog.date,
            func.count(TLog.id).label("cnt"),
            func.max(TLog.id).label("max_id"),  # Keep the latest, delete earlier ones
        )
        .outerjoin(logs_with_photos, TLog.id == logs_with_photos.c.tlog_id)
        .filter(logs_with_photos.c.tlog_id.is_(None))  # No photos
        .group_by(
            TLog.user_id,
            TLog.trig_id,
            TLog.date,
        )
        .having(func.count(TLog.id) > 1)
        .subquery()
    )

    # Get one log from each duplicate group (not the max_id, so it can be deleted)
    # Join back to get log details
    rows = (
        db.query(TLog, Trig.name, Trig.waypoint, User.name, duplicate_groups.c.cnt)
        .join(
            duplicate_groups,
            (TLog.user_id == duplicate_groups.c.user_id)
            & (TLog.trig_id == duplicate_groups.c.trig_id)
            & (TLog.date == duplicate_groups.c.date)
            & (TLog.id != duplicate_groups.c.max_id),  # Not the one to keep
        )
        .outerjoin(Trig, TLog.trig_id == Trig.id)
        .outerjoin(User, TLog.user_id == User.id)
        .order_by(desc(TLog.date), desc(TLog.time), desc(TLog.id))
        .offset(skip)
        .limit(limit)
        .all()
    )

    return [
        (log, trig_name, trig_waypoint, user_name, int(cnt))
        for log, trig_name, trig_waypoint, user_name, cnt in rows
    ]


def get_duplicate_log_groups(
    db: Session, skip: int = 0, limit: int = 100
) -> list[dict]:
    """
    Get duplicate log groups where user_id, trig_id, and date are identical and
    *all returned logs have no photos*.

    Duplicates are detected by user_id + trig_id + date only.

    Returns a list of dicts:
      {
        "user_id": int | None,
        "user_name": str | None,
        "trig_id": int | None,
        "trig_name": str | None,
        "trig_waypoint": str | None,
        "date": date | None,
        "duplicate_count": int,
        "logs": list[TLog],
      }
    """
    from api.models.tphoto import TPhoto

    # Subquery to find logs with photos
    logs_with_photos = (
        db.query(TPhoto.tlog_id).filter(TPhoto.deleted_ind != "Y").distinct().subquery()
    )

    # Find duplicate groups (no-photos only)
    duplicate_groups = (
        db.query(
            TLog.user_id.label("user_id"),
            TLog.trig_id.label("trig_id"),
            TLog.date.label("date"),
            func.count(TLog.id).label("cnt"),
        )
        .outerjoin(logs_with_photos, TLog.id == logs_with_photos.c.tlog_id)
        .filter(logs_with_photos.c.tlog_id.is_(None))  # No photos
        .group_by(TLog.user_id, TLog.trig_id, TLog.date)
        .having(func.count(TLog.id) > 1)
        .subquery()
    )

    # Fetch all logs belonging to those groups (again: no-photos only)
    rows = (
        db.query(
            TLog,
            Trig.name,
            Trig.waypoint,
            User.name,
            duplicate_groups.c.cnt,
        )
        .join(
            duplicate_groups,
            (TLog.user_id == duplicate_groups.c.user_id)
            & (TLog.trig_id == duplicate_groups.c.trig_id)
            & (TLog.date == duplicate_groups.c.date),
        )
        .outerjoin(logs_with_photos, TLog.id == logs_with_photos.c.tlog_id)
        .filter(logs_with_photos.c.tlog_id.is_(None))  # No photos
        .outerjoin(Trig, TLog.trig_id == Trig.id)
        .outerjoin(User, TLog.user_id == User.id)
        .order_by(desc(TLog.date), desc(TLog.time), desc(TLog.id))
        .offset(skip)
        .limit(limit)
        .all()
    )

    # Group in Python
    grouped: dict[tuple, dict] = {}
    for log, trig_name, trig_waypoint, user_name, cnt in rows:
        key = (log.user_id, log.trig_id, log.date)
        if key not in grouped:
            grouped[key] = {
                "user_id": int(log.user_id) if log.user_id is not None else None,
                "user_name": user_name,
                "trig_id": int(log.trig_id) if log.trig_id is not None else None,
                "trig_name": trig_name,
                "trig_waypoint": trig_waypoint,
                "date": log.date,
                "duplicate_count": int(cnt),
                "logs": [],
            }
        grouped[key]["logs"].append(log)

    # Preserve query ordering: already sorted newest-first. Convert to list.
    return list(grouped.values())


def get_logs_needing_attention_summary(db: Session) -> dict:
    """
    Get summary statistics for logs needing attention.
    """
    return {
        "orphaned_count": get_orphaned_logs_count(db),
        "duplicate_count": get_duplicate_logs_count(db),
    }


def delete_orphaned_log(db: Session, log_id: int) -> bool:
    """
    Delete an orphaned log (log referencing a deleted trigpoint).

    Returns True if deleted, False if not found or not orphaned.
    """
    # Verify it's actually orphaned
    log = db.query(TLog).filter(TLog.id == log_id).first()
    if not log:
        return False

    # Check that trig doesn't exist
    trig_exists = db.query(Trig).filter(Trig.id == log.trig_id).first()
    if trig_exists:
        return False  # Not orphaned

    # Store user_id for cache invalidation
    user_id = int(log.user_id) if log.user_id else None

    db.delete(log)
    db.commit()

    # Invalidate caches
    if user_id:
        invalidate_log_caches(trig_id=0, user_id=user_id, log_id=log_id)

    return True


def delete_duplicate_log(db: Session, log_id: int) -> bool:
    """
    Delete a duplicate log entry.

    Verifies that this log is actually part of a duplicate set before deleting.
    Returns True if deleted, False if not found or not a duplicate.
    """
    log = db.query(TLog).filter(TLog.id == log_id).first()
    if not log:
        return False

    from api.models.tphoto import TPhoto

    # Subquery to find logs with photos
    logs_with_photos = (
        db.query(TPhoto.tlog_id).filter(TPhoto.deleted_ind != "Y").distinct().subquery()
    )

    # Check that this log has no photos
    has_photos = (
        db.query(logs_with_photos.c.tlog_id)
        .filter(logs_with_photos.c.tlog_id == log_id)
        .first()
    )
    if has_photos:
        return False  # Has photos, shouldn't be deleted

    # Build filter for checking duplicates
    # Duplicates are detected by user_id + trig_id + date only
    filters = [
        TLog.user_id == log.user_id,
        TLog.trig_id == log.trig_id,
        TLog.date == log.date,
        TLog.id != log_id,
    ]

    # Check that there's at least one other identical log *without photos*.
    # This also prevents deleting the last remaining log in a duplicate set.
    duplicate_count = (
        db.query(func.count(TLog.id))
        .outerjoin(logs_with_photos, TLog.id == logs_with_photos.c.tlog_id)
        .filter(logs_with_photos.c.tlog_id.is_(None))  # No photos
        .filter(*filters)
        .scalar()
        or 0
    )

    if duplicate_count == 0:
        return False  # Not a duplicate

    # Store IDs for cache invalidation
    trig_id = int(log.trig_id) if log.trig_id else 0
    user_id = int(log.user_id) if log.user_id else 0

    db.delete(log)
    db.commit()

    # Invalidate caches
    invalidate_log_caches(trig_id=trig_id, user_id=user_id, log_id=log_id)

    return True


# ============================================================================
# Draft Log Functions
# ============================================================================


def create_draft_log(
    db: Session,
    *,
    trig_id: int,
    user_id: int,
    ip_addr: Optional[str] = None,
) -> TLog:
    """Create a minimal draft log record for photo uploads.

    Draft logs have status='D' and minimal required fields.
    They are not visible in normal listings until published.

    Args:
        db: Database session
        trig_id: ID of the trigpoint
        user_id: ID of the user creating the draft
        ip_addr: Optional IP address of the client

    Returns:
        The created draft TLog record
    """
    log = TLog(
        trig_id=trig_id,
        user_id=user_id,
        status="D",
        ip_addr=ip_addr,
        source="W",  # Web source
    )
    db.add(log)
    db.commit()
    db.refresh(log)

    # Note: We don't invalidate caches or update trigstats for drafts
    # since they're not visible in normal listings

    return log


def get_user_draft_for_trig(
    db: Session,
    *,
    user_id: int,
    trig_id: int,
) -> Optional[TLog]:
    """Check if user has an existing draft for this trig.

    Args:
        db: Database session
        user_id: ID of the user
        trig_id: ID of the trigpoint

    Returns:
        The draft TLog if found, None otherwise
    """
    return (
        db.query(TLog)
        .filter(
            TLog.user_id == user_id,
            TLog.trig_id == trig_id,
            TLog.status == "D",
        )
        .first()
    )


def publish_draft_log(
    db: Session,
    *,
    log_id: int,
    updates: dict,
) -> Optional[TLog]:
    """Publish a draft log by updating its status and setting all fields.

    Args:
        db: Database session
        log_id: ID of the draft log to publish
        updates: Dictionary of field values to set (from TLogCreate)

    Returns:
        The published TLog if successful, None if not found or not a draft
    """
    log = db.query(TLog).filter(TLog.id == log_id).first()
    if not log:
        return None

    # Verify it's a draft
    if log.status != "D":
        return None

    # Update all fields from the payload
    for key, value in updates.items():
        if hasattr(log, key) and key not in ("trig_id", "user_id", "status"):
            setattr(log, key, value)

    # Set status to published
    log.status = "P"  # type: ignore[assignment]

    db.add(log)

    # Check if trig condition should be updated based on log condition
    tlog_condition = updates.get("condition")
    if tlog_condition and log.trig_id:
        maybe_update_trig_condition(
            db, trig_id=int(log.trig_id), tlog_condition=tlog_condition
        )

    db.commit()
    db.refresh(log)

    # Now that it's published, invalidate caches and update stats
    if log.trig_id and log.user_id:
        invalidate_log_caches(
            trig_id=int(log.trig_id),
            user_id=int(log.user_id),
            log_id=log_id,
        )
        _get_trigstats_crud().update_trigstats(db, int(log.trig_id))

    return log


def delete_abandoned_drafts(
    db: Session,
    *,
    older_than_hours: int = 24,
) -> int:
    """Delete draft logs older than the specified threshold.

    This is typically called by a scheduled job to clean up abandoned drafts.
    Photos attached to the draft are soft-deleted first.

    Args:
        db: Database session
        older_than_hours: Delete drafts older than this many hours

    Returns:
        Count of drafts deleted
    """
    from datetime import UTC, datetime, timedelta

    cutoff = datetime.now(UTC) - timedelta(hours=older_than_hours)

    # Find all abandoned drafts
    drafts = (
        db.query(TLog)
        .filter(
            TLog.status == "D",
            TLog.upd_timestamp < cutoff,
        )
        .all()
    )

    count = 0
    for draft in drafts:
        # Soft-delete any photos attached to this draft
        soft_delete_photos_for_log(db, log_id=int(draft.id))

        # Hard-delete the draft
        db.delete(draft)
        count += 1

    if count > 0:
        db.commit()

    return count
