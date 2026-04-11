"""
CRUD operations for user merge functionality.
"""

from datetime import date, datetime, time
from typing import Dict, List, Optional, Tuple

from sqlalchemy import func
from sqlalchemy.orm import Session

from api.core.logging import get_logger
from api.models.tphoto import TPhoto
from api.models.user import TLog, TPhotoVote, User

logger = get_logger(__name__)


def _combine_crt(crt_date: Optional[date], crt_time: Optional[time]) -> datetime:
    """Combine crt_date and crt_time into a single datetime for comparison."""
    d = crt_date if crt_date else date(1900, 1, 1)
    t = crt_time if crt_time else time(0, 0, 0)
    return datetime.combine(d, t)


def find_users_by_email(db: Session, email: str) -> List[User]:
    """
    Find all users with a specific email address (case-insensitive).

    Args:
        db: Database session
        email: Email address to search for

    Returns:
        List of User objects with matching email
    """
    return db.query(User).filter(func.lower(User.email) == email.lower()).all()


def get_user_last_activity(db: Session, user_id: int) -> Optional[datetime]:
    """
    Get the most recent activity timestamp for a user across all activity tables.

    Checks: tlog, tphoto (via tlog_id), tphotovote

    Args:
        db: Database session
        user_id: User ID to check

    Returns:
        Most recent activity datetime or None if no activity found
    """
    timestamps: List[Optional[datetime]] = []

    # Check tlog
    tlog_latest = (
        db.query(func.max(TLog.upd_timestamp)).filter(TLog.user_id == user_id).scalar()
    )
    if tlog_latest:
        timestamps.append(tlog_latest)

    # Check tphoto via tlog join
    tphoto_latest = (
        db.query(func.max(TPhoto.crt_timestamp))
        .join(TLog, TPhoto.tlog_id == TLog.id)
        .filter(TLog.user_id == user_id)
        .scalar()
    )
    if tphoto_latest:
        timestamps.append(tphoto_latest)

    # Check tphotovote
    tphotovote_latest = (
        db.query(func.max(TPhotoVote.upd_timestamp))
        .filter(TPhotoVote.user_id == user_id)
        .scalar()
    )
    if tphotovote_latest:
        timestamps.append(tphotovote_latest)

    # Return the most recent timestamp
    if timestamps:
        return max([t for t in timestamps if t is not None], default=None)
    return None


def get_user_activity_counts(db: Session, user_id: int) -> Dict[str, int]:
    """
    Get activity counts for a user across all activity tables.

    Args:
        db: Database session
        user_id: User ID to check

    Returns:
        Dictionary with activity counts by type
    """
    counts = {}

    # Count logs
    counts["logs"] = db.query(TLog).filter(TLog.user_id == user_id).count()

    # Count photos via tlog
    counts["photos"] = (
        db.query(TPhoto)
        .join(TLog, TPhoto.tlog_id == TLog.id)
        .filter(TLog.user_id == user_id)
        .count()
    )

    # Count photo votes
    counts["photo_votes"] = (
        db.query(TPhotoVote).filter(TPhotoVote.user_id == user_id).count()
    )

    return counts


def get_email_duplicates_summary(
    db: Session, email_filter: Optional[str] = None
) -> List[Tuple[str, List[User]]]:
    """
    Get summary of all emails with duplicate users.

    Args:
        db: Database session
        email_filter: Optional specific email to filter for

    Returns:
        List of tuples (email, [users]) sorted by number of users descending
    """
    # Build query for emails with multiple users
    query = db.query(User.email, func.count(User.id).label("user_count"))

    if email_filter:
        query = query.filter(func.lower(User.email) == email_filter.lower())

    # Filter out empty emails and group by email
    query = (
        query.filter(User.email != "")
        .group_by(User.email)
        .having(func.count(User.id) > 1)
        .order_by(func.count(User.id).desc())
    )

    duplicate_emails = query.all()

    # Get users for each duplicate email
    result = []
    for email, count in duplicate_emails:
        users = find_users_by_email(db, str(email))
        result.append((str(email), users))

    return result


def count_records_for_user(db: Session, user_id: int) -> Dict[str, int]:
    """
    Count records for a specific user.

    Args:
        db: Database session
        user_id: User ID to count records for

    Returns:
        Dictionary with counts: tlog, tphoto, tphotovote
    """
    counts = {"tlog": 0, "tphoto": 0, "tphotovote": 0}

    # Count tlog records
    counts["tlog"] = db.query(TLog).filter(TLog.user_id == user_id).count()

    # Count tphoto records via tlog
    tlog_ids = [
        row[0] for row in db.query(TLog.id).filter(TLog.user_id == user_id).all()
    ]
    if tlog_ids:
        counts["tphoto"] = db.query(TPhoto).filter(TPhoto.tlog_id.in_(tlog_ids)).count()

    # Count tphotovote records
    counts["tphotovote"] = (
        db.query(TPhotoVote).filter(TPhotoVote.user_id == user_id).count()
    )

    return counts


def merge_users_admin(
    db: Session,
    target_user_id: int,
    source_user_id: int,
    dry_run: bool = True,
) -> Dict:
    """
    Merge source user into target user for admin operations.

    Args:
        db: Database session
        target_user_id: ID of user to keep
        source_user_id: ID of user to merge and delete
        dry_run: If True, only preview changes without executing

    Returns:
        Dictionary with merge results or preview

    Raises:
        ValueError: If users not found or validation fails
    """
    # Validate users exist
    target_user = db.query(User).filter(User.id == target_user_id).first()
    if not target_user:
        raise ValueError(f"Target user {target_user_id} not found")

    source_user = db.query(User).filter(User.id == source_user_id).first()
    if not source_user:
        raise ValueError(f"Source user {source_user_id} not found")

    if target_user_id == source_user_id:
        raise ValueError("Target and source users must be different")

    # Count records
    source_counts = count_records_for_user(db, source_user_id)

    # Determine profile updates
    profile_fields = [
        "firstname",
        "surname",
        "email",
        "homepage",
        "about",
        "auth0_user_id",
    ]
    profile_updates = {}
    auth0_will_update = False

    for field in profile_fields:
        target_value = getattr(target_user, field)
        source_value = getattr(source_user, field)

        # Only copy if target is blank/empty
        if not target_value or str(target_value).strip() == "":
            if source_value and str(source_value).strip():
                profile_updates[field] = str(source_value)
                if field == "auth0_user_id":
                    auth0_will_update = True

    # Determine the earliest member-since datetime
    target_crt = _combine_crt(target_user.crt_date, target_user.crt_time)  # type: ignore[arg-type]
    source_crt = _combine_crt(source_user.crt_date, source_user.crt_time)  # type: ignore[arg-type]
    earliest_crt = min(target_crt, source_crt)

    # If dry run, return preview
    if dry_run:
        return {
            "dry_run": True,
            "target_user": {
                "id": int(target_user.id),
                "name": str(target_user.name),
                "email": str(target_user.email) if target_user.email else "",
                "auth0_user_id": (
                    str(target_user.auth0_user_id)
                    if target_user.auth0_user_id
                    else None
                ),
                "firstname": (
                    str(target_user.firstname) if target_user.firstname else ""
                ),
                "surname": str(target_user.surname) if target_user.surname else "",
                "homepage": str(target_user.homepage) if target_user.homepage else "",
                "about": str(target_user.about) if target_user.about else "",
                "crt_date": str(target_user.crt_date) if target_user.crt_date else None,
                "crt_time": str(target_user.crt_time) if target_user.crt_time else None,
            },
            "source_user": {
                "id": int(source_user.id),
                "name": str(source_user.name),
                "email": str(source_user.email) if source_user.email else "",
                "auth0_user_id": (
                    str(source_user.auth0_user_id)
                    if source_user.auth0_user_id
                    else None
                ),
                "firstname": (
                    str(source_user.firstname) if source_user.firstname else ""
                ),
                "surname": str(source_user.surname) if source_user.surname else "",
                "homepage": str(source_user.homepage) if source_user.homepage else "",
                "about": str(source_user.about) if source_user.about else "",
                "crt_date": str(source_user.crt_date) if source_user.crt_date else None,
                "crt_time": str(source_user.crt_time) if source_user.crt_time else None,
            },
            "estimated_records": source_counts,
            "profile_updates": profile_updates,
            "auth0_will_update": auth0_will_update,
            "member_since": str(earliest_crt),
        }

    # Execute the merge
    logger.info(
        f"Starting admin merge of user {source_user_id} into user {target_user_id}"
    )

    updated_counts = {"tlog": 0, "tphoto": source_counts["tphoto"], "tphotovote": 0}

    # Update tlog records
    tlog_count = (
        db.query(TLog)
        .filter(TLog.user_id == source_user_id)
        .update({TLog.user_id: target_user_id}, synchronize_session=False)
    )
    updated_counts["tlog"] = tlog_count
    logger.info(f"Updated {tlog_count} tlog records")

    # Update tphotovote records
    tphotovote_count = (
        db.query(TPhotoVote)
        .filter(TPhotoVote.user_id == source_user_id)
        .update({TPhotoVote.user_id: target_user_id}, synchronize_session=False)
    )
    updated_counts["tphotovote"] = tphotovote_count
    logger.info(f"Updated {tphotovote_count} tphotovote records")

    # Note: tphoto records are linked via tlog_id, so they're automatically
    # reassigned when we update the tlog records above

    # Update target user crt_date/crt_time to the earliest of the two accounts
    if earliest_crt < target_crt:
        target_user.crt_date = earliest_crt.date()  # type: ignore[assignment]
        target_user.crt_time = earliest_crt.time()  # type: ignore[assignment]
        logger.info(f"Updated target user crt_date/crt_time to {earliest_crt}")

    # Update target user profile with source values (only if target is blank)
    profile_updated = False
    auth0_transferred = False

    for field, value in profile_updates.items():
        if value:
            setattr(target_user, field, value)
            profile_updated = True
            if field == "auth0_user_id":
                auth0_transferred = True
            logger.info(f"Updated target user {field}")

    if profile_updated or earliest_crt < target_crt:
        db.add(target_user)

    # Delete source user
    db.query(User).filter(User.id == source_user_id).delete(synchronize_session=False)
    logger.info(f"Deleted source user {source_user_id}")

    # Commit the transaction
    db.commit()

    return {
        "success": True,
        "target_user_id": target_user_id,
        "source_user_id": source_user_id,
        "updated_records": updated_counts,
        "profile_updated": profile_updated,
        "auth0_transferred": auth0_transferred,
    }
