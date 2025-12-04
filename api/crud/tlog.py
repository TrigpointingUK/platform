"""
CRUD operations for tlog table.
"""

from datetime import date as DateType
from typing import Iterable, List, Optional, Tuple

from sqlalchemy import asc, desc, func
from sqlalchemy.orm import Session

from api.models.tphoto import TPhoto
from api.models.trig import Trig
from api.models.user import TLog, User
from api.services.cache_invalidator import (
    invalidate_log_caches,
    invalidate_photo_caches,
)


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
    """Check if user already has a log for this trig on this date."""
    q = db.query(TLog).filter(
        TLog.user_id == user_id,
        TLog.trig_id == trig_id,
        TLog.date == date,
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
) -> List[TLog]:
    q = db.query(TLog)
    if trig_id is not None:
        q = q.filter(TLog.trig_id == trig_id)
    if user_id is not None:
        q = q.filter(TLog.user_id == user_id)

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


def count_logs_filtered(
    db: Session, *, trig_id: Optional[int] = None, user_id: Optional[int] = None
) -> int:
    q = db.query(func.count(TLog.id))
    if trig_id is not None:
        q = q.filter(TLog.trig_id == trig_id)
    if user_id is not None:
        q = q.filter(TLog.user_id == user_id)
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
    db.commit()
    db.refresh(log)

    # Invalidate related caches
    invalidate_log_caches(trig_id=trig_id, user_id=user_id, log_id=int(log.id))

    return log


def update_log(db: Session, *, log_id: int, updates: dict) -> Optional[TLog]:
    log = db.query(TLog).filter(TLog.id == log_id).first()
    if not log:
        return None
    for key, value in updates.items():
        if hasattr(log, key):
            setattr(log, key, value)
    db.add(log)
    db.commit()
    db.refresh(log)

    # Invalidate related caches
    invalidate_log_caches(
        trig_id=int(log.trig_id), user_id=int(log.user_id), log_id=log_id
    )

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

    return True


def soft_delete_photos_for_log(db: Session, *, log_id: int) -> int:
    """Soft delete all photos for a given tlog by setting deleted_ind='Y'. Returns count."""
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
        db.add(p)
        count += 1
    db.commit()

    # Invalidate photo-related caches if any photos were deleted
    if count > 0 and log:
        invalidate_photo_caches(
            trig_id=int(log.trig_id), user_id=int(log.user_id), log_id=log_id
        )

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
        regex_pattern: Regex pattern to search for (MySQL REGEXP)
        skip: Number of records to skip
        limit: Maximum number of records to return

    Returns:
        List of TLog objects
    """
    # MySQL REGEXP operator
    return (
        db.query(TLog)
        .filter(TLog.comment.op("REGEXP")(regex_pattern))
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
        regex_pattern: Regex pattern to search for (MySQL REGEXP)

    Returns:
        Count of matching logs
    """
    # MySQL REGEXP operator
    return (
        db.query(func.count(TLog.id))
        .filter(TLog.comment.op("REGEXP")(regex_pattern))
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
        regex_pattern: Regex pattern to search for (MySQL REGEXP)
        skip: Number of results to skip
        limit: Maximum number of results to return

    Returns:
        List of tuples (TLog, trig_name, user_name)
    """
    rows = (
        db.query(TLog, Trig.name, User.name)
        .outerjoin(Trig, TLog.trig_id == Trig.id)
        .outerjoin(User, TLog.user_id == User.id)
        .filter(TLog.comment.op("REGEXP")(regex_pattern))
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

    # Subquery to find duplicate groups (logs with same key fields, no photos)
    duplicate_groups = (
        db.query(
            TLog.user_id,
            TLog.trig_id,
            TLog.date,
            TLog.time,
            TLog.condition,
            TLog.comment,
            func.count(TLog.id).label("cnt"),
        )
        .outerjoin(logs_with_photos, TLog.id == logs_with_photos.c.tlog_id)
        .filter(logs_with_photos.c.tlog_id.is_(None))  # No photos
        .group_by(
            TLog.user_id,
            TLog.trig_id,
            TLog.date,
            TLog.time,
            TLog.condition,
            TLog.comment,
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
    Get duplicate log entries where user_id, trig_id, date, time, condition, comment
    are identical and no photos have been uploaded.

    Returns only one log from each duplicate group (the one to delete).
    Returns list of tuples (TLog, trig_name, trig_waypoint, user_name, duplicate_count).
    """
    from api.models.tphoto import TPhoto

    # Subquery to find logs with photos
    logs_with_photos = (
        db.query(TPhoto.tlog_id).filter(TPhoto.deleted_ind != "Y").distinct().subquery()
    )

    # Find all duplicate groups with their counts
    duplicate_groups = (
        db.query(
            TLog.user_id,
            TLog.trig_id,
            TLog.date,
            TLog.time,
            TLog.condition,
            TLog.comment,
            func.count(TLog.id).label("cnt"),
            func.max(TLog.id).label("max_id"),  # Keep the latest, delete earlier ones
        )
        .outerjoin(logs_with_photos, TLog.id == logs_with_photos.c.tlog_id)
        .filter(logs_with_photos.c.tlog_id.is_(None))  # No photos
        .group_by(
            TLog.user_id,
            TLog.trig_id,
            TLog.date,
            TLog.time,
            TLog.condition,
            TLog.comment,
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
            & (TLog.time == duplicate_groups.c.time)
            & (
                (TLog.condition == duplicate_groups.c.condition)
                | (TLog.condition.is_(None) & duplicate_groups.c.condition.is_(None))
            )
            & (
                (TLog.comment == duplicate_groups.c.comment)
                | (TLog.comment.is_(None) & duplicate_groups.c.comment.is_(None))
            )
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
    from api.models.tphoto import TPhoto

    log = db.query(TLog).filter(TLog.id == log_id).first()
    if not log:
        return False

    # Check that this log has no photos
    has_photos = (
        db.query(TPhoto)
        .filter(TPhoto.tlog_id == log_id, TPhoto.deleted_ind != "Y")
        .first()
    )
    if has_photos:
        return False  # Has photos, shouldn't be deleted

    # Build filter for checking duplicates
    # Must match user_id, trig_id, date, time, condition, comment
    filters = [
        TLog.user_id == log.user_id,
        TLog.trig_id == log.trig_id,
        TLog.date == log.date,
        TLog.time == log.time,
        TLog.id != log_id,
    ]

    # Handle nullable condition field
    if log.condition:
        filters.append(TLog.condition == log.condition)
    else:
        filters.append(TLog.condition.is_(None))

    # Handle nullable comment field
    if log.comment:
        filters.append(TLog.comment == log.comment)
    else:
        filters.append(TLog.comment.is_(None))

    # Check that there's at least one other identical log
    duplicate_count = db.query(func.count(TLog.id)).filter(*filters).scalar() or 0

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
