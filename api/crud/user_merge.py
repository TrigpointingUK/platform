"""
CRUD operations for user merge functionality.
"""

from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

from sqlalchemy import func
from sqlalchemy.orm import Session

from api.core.logging import get_logger
from api.models.tphoto import TPhoto
from api.models.user import TLog, TPhotoVote, TQuery, TQuizScores, User
from api.schemas.user_merge import ConflictingUser, RecordCounts

logger = get_logger(__name__)


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

    Checks: tlog, tphoto (via tlog_id), tphotovote, tquery, tquizscores

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

    # Check tquery
    tquery_latest = (
        db.query(func.max(TQuery.upd_timestamp))
        .filter(TQuery.user_id == user_id)
        .scalar()
    )
    if tquery_latest:
        timestamps.append(tquery_latest)

    # Check tquizscores
    tquizscores_latest = (
        db.query(func.max(TQuizScores.upd_timestamp))
        .filter(TQuizScores.user_id == user_id)
        .scalar()
    )
    if tquizscores_latest:
        timestamps.append(tquizscores_latest)

    # Return the most recent timestamp
    if timestamps:
        return max(timestamps)
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

    # Count queries
    counts["queries"] = db.query(TQuery).filter(TQuery.user_id == user_id).count()

    # Count quiz scores
    counts["quiz_scores"] = (
        db.query(TQuizScores).filter(TQuizScores.user_id == user_id).count()
    )

    return counts


def get_users_with_activity(
    db: Session, users: List[User]
) -> List[Tuple[User, Optional[datetime]]]:
    """
    Get users with their last activity timestamp.

    Args:
        db: Database session
        users: List of User objects

    Returns:
        List of tuples (User, last_activity_datetime) sorted by activity (most recent first)
    """
    users_with_activity = []
    for user in users:
        last_activity = get_user_last_activity(db, int(user.id))
        users_with_activity.append((user, last_activity))

    # Sort by last activity (most recent first, None values last)
    users_with_activity.sort(
        key=lambda x: (
            x[1] if x[1] is not None else datetime.min.replace(tzinfo=timezone.utc)
        ),
        reverse=True,
    )

    return users_with_activity


def check_merge_conflicts(
    db: Session,
    users_with_activity: List[Tuple[User, Optional[datetime]]],
    threshold_days: int,
) -> Tuple[Optional[User], List[ConflictingUser]]:
    """
    Check if merge can proceed based on activity threshold.

    Args:
        db: Database session
        users_with_activity: List of (User, last_activity) tuples sorted by activity
        threshold_days: Threshold in days for conflict detection

    Returns:
        Tuple of (primary_user, conflicting_users)
        primary_user is the user with most recent activity
        conflicting_users contains users with activity within threshold of primary
    """
    if not users_with_activity:
        return None, []

    primary_user, primary_activity = users_with_activity[0]
    conflicting_users = []

    # If primary user has no activity, use creation date as fallback
    if primary_activity is None:
        # Use user creation date as fallback
        primary_activity = datetime.combine(
            primary_user.crt_date, primary_user.crt_time
        ).replace(tzinfo=timezone.utc)

    for user, last_activity in users_with_activity[1:]:
        if last_activity is None:
            # User with no activity - use creation date
            last_activity = datetime.combine(user.crt_date, user.crt_time).replace(
                tzinfo=timezone.utc
            )

        # Calculate days difference
        days_diff = (primary_activity - last_activity).days

        if days_diff < threshold_days:
            conflicting_users.append(
                ConflictingUser(
                    user_id=int(user.id),
                    username=str(user.name),
                    last_activity=last_activity,
                    days_since_primary=float(days_diff),
                )
            )

    return primary_user, conflicting_users


def select_best_profile_values(
    db: Session, user_ids: List[int], fields: List[str]
) -> Dict[str, Optional[str]]:
    """
    Select best (most recent non-empty) values for profile fields.

    Args:
        db: Database session
        user_ids: List of user IDs to consider
        fields: List of field names to select from

    Returns:
        Dictionary mapping field names to selected values
    """
    users = db.query(User).filter(User.id.in_(user_ids)).all()

    # Sort by update timestamp (most recent first)
    users.sort(key=lambda u: u.upd_timestamp, reverse=True)

    result = {}
    for field in fields:
        result[field] = None
        for user in users:
            value = getattr(user, field, None)
            # Select first non-empty value
            if value and str(value).strip():
                result[field] = str(value)
                break

    return result


def count_records_for_users(db: Session, user_ids: List[int]) -> RecordCounts:
    """
    Count records that would be affected by merging users.

    Args:
        db: Database session
        user_ids: List of user IDs to count records for

    Returns:
        RecordCounts object with counts by table
    """
    counts = RecordCounts()

    if not user_ids:
        return counts

    # Count tlog records
    counts.tlog = db.query(TLog).filter(TLog.user_id.in_(user_ids)).count()

    # Count tphoto records via tlog
    tlog_ids = [
        row[0] for row in db.query(TLog.id).filter(TLog.user_id.in_(user_ids)).all()
    ]
    if tlog_ids:
        counts.tphoto = db.query(TPhoto).filter(TPhoto.tlog_id.in_(tlog_ids)).count()

    # Count tphotovote records
    counts.tphotovote = (
        db.query(TPhotoVote).filter(TPhotoVote.user_id.in_(user_ids)).count()
    )

    # Count tquery records
    counts.tquery = db.query(TQuery).filter(TQuery.user_id.in_(user_ids)).count()

    # Count tquizscores records
    counts.tquizscores = (
        db.query(TQuizScores).filter(TQuizScores.user_id.in_(user_ids)).count()
    )

    return counts


def merge_users(
    db: Session, primary_user_id: int, secondary_user_ids: List[int]
) -> RecordCounts:
    """
    Merge secondary users into primary user.

    Updates all activity records to point to primary user, updates profile fields,
    and deletes secondary users.

    Args:
        db: Database session
        primary_user_id: ID of user to keep
        secondary_user_ids: IDs of users to merge and delete

    Returns:
        RecordCounts with number of records updated

    Raises:
        ValueError: If primary user not found or any validation fails
    """
    if not secondary_user_ids:
        return RecordCounts()

    # Validate primary user exists
    primary_user = db.query(User).filter(User.id == primary_user_id).first()
    if not primary_user:
        raise ValueError(f"Primary user {primary_user_id} not found")

    logger.info(
        f"Starting merge of users {secondary_user_ids} into primary user {primary_user_id}"
    )

    counts = RecordCounts()

    # Update tlog records
    tlog_count = (
        db.query(TLog)
        .filter(TLog.user_id.in_(secondary_user_ids))
        .update({TLog.user_id: primary_user_id}, synchronize_session=False)
    )
    counts.tlog = tlog_count
    logger.info(f"Updated {tlog_count} tlog records")

    # Update tphotovote records
    tphotovote_count = (
        db.query(TPhotoVote)
        .filter(TPhotoVote.user_id.in_(secondary_user_ids))
        .update({TPhotoVote.user_id: primary_user_id}, synchronize_session=False)
    )
    counts.tphotovote = tphotovote_count
    logger.info(f"Updated {tphotovote_count} tphotovote records")

    # Update tquery records
    tquery_count = (
        db.query(TQuery)
        .filter(TQuery.user_id.in_(secondary_user_ids))
        .update({TQuery.user_id: primary_user_id}, synchronize_session=False)
    )
    counts.tquery = tquery_count
    logger.info(f"Updated {tquery_count} tquery records")

    # Update tquizscores records
    tquizscores_count = (
        db.query(TQuizScores)
        .filter(TQuizScores.user_id.in_(secondary_user_ids))
        .update({TQuizScores.user_id: primary_user_id}, synchronize_session=False)
    )
    counts.tquizscores = tquizscores_count
    logger.info(f"Updated {tquizscores_count} tquizscores records")

    # Note: tphoto records are linked via tlog_id, so they're automatically
    # reassigned when we update the tlog records above

    # Update primary user profile with best values
    all_user_ids = [primary_user_id] + secondary_user_ids
    profile_fields = ["firstname", "surname", "homepage", "about"]
    best_values = select_best_profile_values(db, all_user_ids, profile_fields)

    profile_updated = False
    for field, value in best_values.items():
        if value and value != getattr(primary_user, field):
            setattr(primary_user, field, value)
            profile_updated = True
            logger.info(f"Updated primary user {field} to: {value}")

    if profile_updated:
        primary_user.upd_timestamp = datetime.now()
        db.add(primary_user)

    # Delete secondary users
    deleted_count = (
        db.query(User)
        .filter(User.id.in_(secondary_user_ids))
        .delete(synchronize_session=False)
    )
    logger.info(f"Deleted {deleted_count} secondary users")

    # Commit the transaction
    db.commit()

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
