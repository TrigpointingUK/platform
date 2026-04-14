"""
CRUD operations for tphoto table.
"""

from typing import Dict, List, Optional

from sqlalchemy import func
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from api.models.tphoto import TPhoto
from api.models.user import TLog, TPhotoVote
from api.services.cache_invalidator import invalidate_photo_caches

# Import update_trigstats lazily to avoid circular imports
_trigstats_crud = None


def _get_trigstats_crud():
    """Lazy import of trigstats crud to avoid circular imports."""
    global _trigstats_crud
    if _trigstats_crud is None:
        from api.crud import trigstats as trigstats_crud

        _trigstats_crud = trigstats_crud
    return _trigstats_crud


def get_photo_by_id(db: Session, photo_id: int) -> Optional[TPhoto]:
    """Fetch a photo by primary key, excluding soft-deleted rows by default."""
    return (
        db.query(TPhoto)
        .filter(TPhoto.id == photo_id, TPhoto.deleted_ind != "Y")
        .first()
    )


def update_photo(db: Session, photo_id: int, updates: dict) -> Optional[TPhoto]:
    """Update mutable fields on a photo and return the updated row."""
    photo = db.query(TPhoto).filter(TPhoto.id == photo_id).first()
    if not photo:
        return None

    # Get related IDs for cache invalidation before update
    log_id = int(photo.tlog_id)
    tlog = db.query(TLog).filter(TLog.id == log_id).first()

    for key, value in updates.items():
        if hasattr(photo, key):
            setattr(photo, key, value)

    db.add(photo)
    db.commit()
    db.refresh(photo)

    # Invalidate related caches
    if tlog:
        invalidate_photo_caches(
            trig_id=int(tlog.trig_id),
            user_id=int(tlog.user_id),
            log_id=log_id,
            photo_id=photo_id,
        )

    return photo


def delete_photo(db: Session, photo_id: int, soft: bool = True) -> bool:
    """Delete a photo.

    Soft delete (default) sets deleted_ind='Y'.
    Hard delete removes the row and explicitly deletes associated tphotovote
    rows first to maintain referential integrity (the FK CASCADE constraint
    serves as a safety net, not the primary mechanism).
    """
    photo = db.query(TPhoto).filter(TPhoto.id == photo_id).first()
    if not photo:
        return False

    # Get related IDs for cache invalidation before delete
    log_id = int(photo.tlog_id) if photo.tlog_id else None
    tlog = db.query(TLog).filter(TLog.id == log_id).first() if log_id else None

    if soft:
        # Use setattr to avoid mypy Column type inference issues
        setattr(photo, "deleted_ind", "Y")
        db.add(photo)
    else:
        # Explicitly delete associated votes before deleting the photo
        # This maintains referential integrity at the application level;
        # the FK CASCADE constraint is a safety net, not the primary mechanism.
        db.query(TPhotoVote).filter(TPhotoVote.tphoto_id == photo_id).delete(
            synchronize_session=False
        )
        db.delete(photo)

    db.commit()

    # Invalidate related caches
    if tlog and log_id is not None:
        invalidate_photo_caches(
            trig_id=int(tlog.trig_id),
            user_id=int(tlog.user_id),
            log_id=log_id,
            photo_id=photo_id,
        )
        # Update trigstats for this trig (photo_count changed)
        _get_trigstats_crud().update_trigstats(db, int(tlog.trig_id))

    return True


def list_photos_filtered(
    db: Session,
    *,
    trig_id: Optional[int] = None,
    log_id: Optional[int] = None,
    user_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 10,
) -> List[TPhoto]:
    q = db.query(TPhoto).filter(TPhoto.deleted_ind != "Y", TPhoto.tlog_id.isnot(None))
    if log_id is not None:
        q = q.filter(TPhoto.tlog_id == log_id)
    if user_id is not None:
        q = q.join(TLog, TLog.id == TPhoto.tlog_id).filter(TLog.user_id == user_id)
    if trig_id is not None:
        q = q.join(TLog, TLog.id == TPhoto.tlog_id).filter(TLog.trig_id == trig_id)

    # Default newest first by id
    q = q.order_by(TPhoto.id.desc())
    return q.offset(skip).limit(limit).all()


def list_all_photos_for_log(db: Session, *, log_id: int) -> List[TPhoto]:
    """Return all non-deleted photos for a given tlog without pagination."""
    return (
        db.query(TPhoto)
        .filter(TPhoto.tlog_id == log_id, TPhoto.deleted_ind != "Y")
        .order_by(TPhoto.id.desc())
        .all()
    )


def create_photo(
    db: Session,
    *,
    log_id: int,
    values: dict,
) -> TPhoto:
    photo = TPhoto(tlog_id=log_id, **values)
    db.add(photo)
    db.commit()
    db.refresh(photo)

    # Invalidate related caches
    tlog = db.query(TLog).filter(TLog.id == log_id).first()
    if tlog:
        invalidate_photo_caches(
            trig_id=int(tlog.trig_id),
            user_id=int(tlog.user_id),
            log_id=log_id,
            photo_id=int(photo.id),
        )
        # Update trigstats for this trig (photo_count changed)
        _get_trigstats_crud().update_trigstats(db, int(tlog.trig_id))

    return photo


# ---------------------------------------------------------------------------
# Photo rating CRUD
# ---------------------------------------------------------------------------

# Only new-scale votes (1-10) are included in aggregates; legacy data used a
# different range and is excluded until explicitly migrated.
_VALID_SCORE_MIN = 1
_VALID_SCORE_MAX = 10


def get_photo_rating(
    db: Session,
    photo_id: int,
    user_id: Optional[int] = None,
) -> dict:
    """Return aggregate rating for a photo and optionally the caller's score."""
    row = (
        db.query(
            func.avg(TPhotoVote.score).label("avg"),
            func.count(TPhotoVote.id).label("cnt"),
        )
        .filter(
            TPhotoVote.tphoto_id == photo_id,
            TPhotoVote.score >= _VALID_SCORE_MIN,
            TPhotoVote.score <= _VALID_SCORE_MAX,
        )
        .one()
    )

    user_score: Optional[int] = None
    if user_id is not None:
        vote = (
            db.query(TPhotoVote.score)
            .filter(
                TPhotoVote.tphoto_id == photo_id,
                TPhotoVote.user_id == user_id,
            )
            .first()
        )
        if vote:
            user_score = int(vote.score)

    avg_val = round(float(row.avg), 1) if row.avg is not None else None
    return {
        "average_score": avg_val,
        "vote_count": int(row.cnt),
        "user_score": user_score,
    }


def upsert_photo_rating(
    db: Session,
    photo_id: int,
    user_id: int,
    score: int,
) -> dict:
    """Create or update a user's rating for a photo. Returns updated aggregate."""
    stmt = pg_insert(TPhotoVote).values(
        tphoto_id=photo_id,
        user_id=user_id,
        score=score,
    )
    stmt = stmt.on_conflict_do_update(
        constraint="uq_tphotovote_photo_user",
        set_={"score": score},
    )
    db.execute(stmt)
    db.commit()
    return get_photo_rating(db, photo_id, user_id=user_id)


def delete_photo_rating(
    db: Session,
    photo_id: int,
    user_id: int,
) -> dict:
    """Remove a user's rating for a photo. Returns updated aggregate."""
    db.query(TPhotoVote).filter(
        TPhotoVote.tphoto_id == photo_id,
        TPhotoVote.user_id == user_id,
    ).delete(synchronize_session=False)
    db.commit()
    return get_photo_rating(db, photo_id, user_id=user_id)


def get_photo_ratings_batch(
    db: Session,
    photo_ids: List[int],
) -> Dict[int, dict]:
    """Fetch aggregate ratings for multiple photos in a single query."""
    rows = (
        db.query(
            TPhotoVote.tphoto_id,
            func.avg(TPhotoVote.score).label("avg"),
            func.count(TPhotoVote.id).label("cnt"),
        )
        .filter(
            TPhotoVote.tphoto_id.in_(photo_ids),
            TPhotoVote.score >= _VALID_SCORE_MIN,
            TPhotoVote.score <= _VALID_SCORE_MAX,
        )
        .group_by(TPhotoVote.tphoto_id)
        .all()
    )

    result: Dict[int, dict] = {}
    for row in rows:
        pid = int(row.tphoto_id)
        result[pid] = {
            "average_score": round(float(row.avg), 1) if row.avg is not None else None,
            "vote_count": int(row.cnt),
            "user_score": None,
        }

    for pid in photo_ids:
        if pid not in result:
            result[pid] = {"average_score": None, "vote_count": 0, "user_score": None}

    return result
