"""
CRUD operations for users with Unix crypt authentication.
"""

import crypt as unix_crypt
import secrets
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from api.core.logging import get_logger
from api.models.user import TLog, User
from api.services.auth0_service import auth0_service
from api.services.cache_invalidator import invalidate_user_caches

logger = get_logger(__name__)


def get_user_by_id(db: Session, user_id: int) -> Optional[User]:
    """
    Get a user by ID.

    Args:
        db: Database session
        user_id: User ID

    Returns:
        User object or None if not found
    """
    return db.query(User).filter(User.id == user_id).first()


def get_user_by_email(db: Session, email: str) -> Optional[User]:
    """
    Get a user by email.

    Args:
        db: Database session
        email: Email address

    Returns:
        User object or None if not found
    """
    return db.query(User).filter(User.email == email).first()


def get_user_by_name(db: Session, name: str) -> Optional[User]:
    """
    Get a user by username.

    Args:
        db: Database session
        name: Username

    Returns:
        User object or None if not found
    """
    return db.query(User).filter(User.name == name).first()


def verify_password(plain_password: str, cryptpw: str) -> bool:
    """
    Verify a password against Unix crypt hash.

    This matches the PHP logic: crypt($_POST['loginpw'], $cryptpw) == $cryptpw

    Args:
        plain_password: Plain text password
        cryptpw: Unix crypt hash from database

    Returns:
        True if password matches, False otherwise
    """
    try:
        if not cryptpw:
            return False
        # Use legacy Unix crypt verification: crypt(input, stored) == stored
        computed = unix_crypt.crypt(plain_password, cryptpw)
        return computed == cryptpw
    except Exception:
        return False


def authenticate_user(db: Session, email: str, password: str) -> Optional[User]:
    """
    Authenticate a user with email and password (legacy function for compatibility).

    Args:
        db: Database session
        email: Email address
        password: Plain text password

    Returns:
        User object if authentication successful, None otherwise
    """
    user = get_user_by_email(db, email)
    if not user:
        return None
    if not verify_password(password, str(user.cryptpw)):
        return None
    return user


def authenticate_user_flexible(
    db: Session, identifier: str, password: str
) -> Optional[User]:
    """
    Authenticate a user with either email or username.

    Auto-detects the identifier type:
    - Contains '@' -> treated as email
    - No '@' -> treated as username
    - Falls back to alternate method if first fails

    After successful authentication, syncs the user to Auth0 if enabled.

    Args:
        db: Database session
        identifier: Email address or username
        password: Plain text password

    Returns:
        User object if authentication successful, None otherwise
    """
    logger.info(
        "authenticate_user_flexible called",
        extra={
            "identifier": identifier,
            "password_provided": bool(password),
            "password_length": len(password) if password else 0,
        },
    )
    user = None

    # Primary detection: email vs username
    if "@" in identifier:
        # Looks like email - try email first, then username fallback
        user = get_user_by_email(db, identifier)
        if not user:
            # Fallback: maybe it's a username that contains @
            user = get_user_by_name(db, identifier)
    else:
        # Looks like username - try username first, then email fallback
        user = get_user_by_name(db, identifier)
        if not user:
            # Fallback: maybe it's an email without obvious @ structure
            user = get_user_by_email(db, identifier)

    # Verify password if user found
    if not user:
        logger.info(
            "User not found in database",
            extra={"identifier": identifier},
        )
        return None
    if not verify_password(password, str(user.cryptpw)):
        logger.info(
            "Password verification failed",
            extra={"identifier": identifier, "user_id": user.id},
        )
        return None

    logger.info(
        "User authentication successful",
        extra={
            "identifier": identifier,
            "user_id": user.id,
            "username": user.name,
            "email": user.email,
        },
    )

    # Always sync user to Auth0 after successful authentication
    try:
        logger.info(
            "Starting Auth0 sync for user",
            extra={
                "user_id": user.id,
                "username": user.name,
                "email": user.email,
                "has_auth0_user_id": bool(user.auth0_user_id),
            },
        )
        auth0_user = auth0_service.sync_user_to_auth0(
            username=str(user.name),
            email=str(user.email) if user.email else None,
            name=str(user.name),
            password=password,  # Use the plaintext password from the login request
            user_id=int(user.id),
            firstname=str(user.firstname) if user.firstname else None,
            surname=str(user.surname) if user.surname else None,
        )

        # Store/update the Auth0 mapping if sync succeeded
        if auth0_user and auth0_user.get("user_id"):
            auth0_user_id_str = str(auth0_user.get("user_id"))
            update_user_auth0_mapping(
                db=db,
                user_id=int(user.id),
                auth0_user_id=auth0_user_id_str,
            )
            # Update the user object to reflect the database change
            user.auth0_user_id = auth0_user_id_str  # type: ignore
            logger.info(
                "Auth0 sync completed and mapping stored",
                extra={
                    "user_id": user.id,
                    "auth0_user_id": auth0_user_id_str,
                },
            )
    except Exception as e:
        # Log the error but don't fail authentication
        logger.error(
            "Auth0 sync failed during authentication",
            extra={
                "user_id": user.id,
                "username": user.name,
                "email": user.email,
                "error": str(e),
            },
        )

    return user


def is_admin(user: User) -> bool:
    """
    Check if user has admin privileges.

    Args:
        user: User object

    Returns:
        True if user is admin, False otherwise
    """
    # admin_ind field removed - admin functionality now handled via Auth0 roles/scopes
    return False


def is_public_profile(user: User) -> bool:
    """
    Check if user has a public profile.

    Args:
        user: User object

    Returns:
        True if profile is public, False otherwise
    """
    return str(user.public_ind) == "Y"


def search_users_by_name(
    db: Session, name_pattern: str, skip: int = 0, limit: int = 100
) -> list[User]:
    """
    Search users by name pattern.

    Args:
        db: Database session
        name_pattern: Name pattern to search for (case-insensitive)
        skip: Number of records to skip
        limit: Maximum number of records to return

    Returns:
        List of User objects
    """
    return (
        db.query(User)
        .filter(User.name.ilike(f"%{name_pattern}%"))
        .offset(skip)
        .limit(limit)
        .all()
    )


def search_users_by_name_or_email(
    db: Session, query: str, limit: int = 20
) -> List[User]:
    """
    Search users by partial match on username or email address.

    Args:
        db: Database session
        query: Fragment of username or email address to search for
        limit: Maximum number of results to return (default: 20)

    Returns:
        List of User objects ordered by username
    """
    pattern = f"%{query.strip()}%"
    return (
        db.query(User)
        .filter(
            or_(
                User.name.ilike(pattern),
                User.email.ilike(pattern),
            )
        )
        .order_by(func.lower(User.name))
        .limit(limit)
        .all()
    )


def get_users_count(db: Session) -> int:
    """
    Get total number of users.

    Args:
        db: Database session

    Returns:
        Total count of users
    """
    return db.query(User).count()


def is_cacher(user: User) -> bool:
    """
    Check if user is a geocacher.

    Args:
        user: User object

    Returns:
        True if user is a geocacher, False otherwise
    """
    return str(user.cacher_ind) == "Y"


def is_trigger(user: User) -> bool:
    """
    Check if user is a trigger.

    Args:
        user: User object

    Returns:
        True if user is a trigger, False otherwise
    """
    return str(user.trigger_ind) == "Y"


def is_email_validated(user: User) -> bool:
    """
    Check if user's email is validated.

    Args:
        user: User object

    Returns:
        True if email is validated, False otherwise
    """
    return str(user.email_valid) == "Y"


def has_gc_auth(user: User) -> bool:
    """
    Check if user has Geocaching.com authentication.

    Args:
        user: User object

    Returns:
        True if user has GC auth, False otherwise
    """
    return str(user.gc_auth_ind) == "Y"


def has_gc_premium(user: User) -> bool:
    """
    Check if user has Geocaching.com premium status.

    Args:
        user: User object

    Returns:
        True if user has GC premium, False otherwise
    """
    return str(user.gc_premium_ind) == "Y"


def get_all_usernames(db: Session) -> List[str]:
    """
    Get all usernames from the legacy database.

    Args:
        db: Database session

    Returns:
        List of all usernames in the database
    """
    users = db.query(User).all()
    return [str(user.name) for user in users if user.name]


def get_user_log_stats(db: Session, user_ids: List[int]) -> Dict[int, Dict[str, Any]]:
    """
    Get log statistics for a list of user IDs.
    Returns a dictionary mapping user_id to log count and latest log timestamp.

    Args:
        db: Database session
        user_ids: List of user IDs to get log stats for

    Returns:
        Dictionary mapping user_id to log statistics
    """
    if not user_ids:
        return {}

    # Get log count and latest log timestamp for each user
    log_stats = (
        db.query(
            TLog.user_id,
            func.count(TLog.id).label("log_count"),
            func.max(func.concat(TLog.date, " ", TLog.time)).label(
                "latest_log_timestamp"
            ),
        )
        .filter(TLog.user_id.in_(user_ids))
        .group_by(TLog.user_id)
        .all()
    )

    # Convert to dictionary
    result = {}
    for user_id, log_count, latest_log_timestamp in log_stats:
        result[user_id] = {
            "log_count": log_count,
            "latest_log_timestamp": latest_log_timestamp,
        }

    return result


def get_all_emails(db: Session) -> List[str]:
    """
    Get all email addresses from the legacy database.

    Args:
        db: Database session

    Returns:
        List of all email addresses in the database
    """
    users = db.query(User).all()
    return [str(user.email) for user in users if user.email]


def find_duplicate_emails(emails: List[str]) -> Dict[str, List[str]]:
    """
    Find duplicate email addresses (case-insensitive).

    Args:
        emails: List of email addresses

    Returns:
        Dictionary mapping email addresses to lists of original email addresses
        that are duplicates (case-insensitive). Only includes entries where
        multiple email addresses map to the same normalized email.
    """
    email_to_originals: Dict[str, List[str]] = {}

    for email in emails:
        if not email:
            continue
        # Normalize email to lowercase for comparison
        normalized = email.lower().strip()
        if normalized not in email_to_originals:
            email_to_originals[normalized] = []
        email_to_originals[normalized].append(email)

    # Return only duplicates
    duplicates = {
        normalized: originals
        for normalized, originals in email_to_originals.items()
        if len(originals) > 1
    }
    return duplicates


def get_users_by_email(db: Session, email: str) -> List[User]:
    """
    Get all users with a specific email address (case-insensitive).

    Args:
        db: Database session
        email: Email address to search for

    Returns:
        List of User objects with the specified email address
    """
    return db.query(User).filter(func.lower(User.email) == email.lower()).all()


def get_user_by_auth0_id(db: Session, auth0_user_id: str) -> Optional[User]:
    """
    Get a user by Auth0 user ID.

    Args:
        db: Database session
        auth0_user_id: Auth0 user ID

    Returns:
        User object or None if not found
    """
    return db.query(User).filter(User.auth0_user_id == auth0_user_id).first()


def create_user(db: Session, username: str, email: str, auth0_user_id: str) -> User:
    """
    Create a new user in the database (called from Auth0 webhook).

    This function creates a user with Auth0 as the authentication provider.
    The cryptpw field is set to a random string for legacy cookie compatibility.
    Firstname and surname are left empty for the user to fill in later.

    Args:
        db: Database session
        username: Username/nickname from Auth0
        email: Email address from Auth0
        auth0_user_id: Auth0 user ID

    Returns:
        Created User object

    Raises:
        ValueError: If username, email, or auth0_user_id already exists
    """
    # Validate uniqueness
    if get_user_by_name(db, username):
        raise ValueError(f"Username '{username}' already exists")

    if get_user_by_email(db, email):
        raise ValueError(f"Email '{email}' already exists")

    if get_user_by_auth0_id(db, auth0_user_id):
        raise ValueError(f"Auth0 user ID '{auth0_user_id}' already exists")

    # Generate random cryptpw for legacy cookie compatibility
    # User cannot log in with this via legacy auth
    random_cryptpw = secrets.token_urlsafe(32)

    # Get current date and time
    now = datetime.now()
    current_date = now.date()
    current_time = now.time()

    # Create new user with sensible defaults
    new_user = User(
        name=username,
        email=email,
        auth0_user_id=auth0_user_id,
        cryptpw=random_cryptpw,
        firstname="",  # Database-only field, user sets later
        surname="",  # Database-only field, user sets later
        email_valid="Y",  # Auth0 has verified the email
        email_ind="N",  # Default: don't send emails
        public_ind="N",  # Default: profile not public
        homepage="",
        distance_ind="K",  # Default: kilometres
        about="",
        status_max=0,
        crt_date=current_date,
        crt_time=current_time,
        upd_timestamp=now,
        online_map_type="",
        online_map_type2="lla",
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    logger.info(
        "User created via Auth0 webhook",
        extra={
            "user_id": new_user.id,
            "username": username,
            "email": email,
            "auth0_user_id": auth0_user_id,
        },
    )

    # Invalidate user-related caches
    invalidate_user_caches(user_id=int(new_user.id))

    return new_user


def update_user_auth0_id(db: Session, user_id: int, auth0_user_id: str) -> bool:
    """
    Update user's Auth0 user ID.

    Args:
        db: Database session
        user_id: Database user ID
        auth0_user_id: Auth0 user ID

    Returns:
        True if successful, False otherwise
    """
    user = get_user_by_id(db, user_id=user_id)
    if not user:
        return False  # pragma: no cover

    user.auth0_user_id = auth0_user_id  # type: ignore
    db.commit()

    return True


def update_user_auth0_mapping(db: Session, user_id: int, auth0_user_id: str) -> bool:
    """
    Update user's Auth0 mapping with user ID.

    Args:
        db: Database session
        user_id: Legacy database user ID
        auth0_user_id: Auth0 user ID (e.g. "auth0|abc123")

    Returns:
        True if update succeeded, False otherwise.
    """
    user = get_user_by_id(db, user_id=user_id)
    if not user:
        return False

    # Try to set the Auth0 user ID
    try:
        user.auth0_user_id = auth0_user_id  # type: ignore
        db.commit()
        return True
    except Exception as e:
        db.rollback()
        logger.error(  # pragma: no cover
            "Auth0 mapping update failed",
            extra={"user_id": user_id, "error": str(e)},
        )
        return False  # pragma: no cover


def get_user_auth0_id(db: Session, user_id: int) -> Optional[str]:
    """
    Get Auth0 user ID for a database user.

    Args:
        db: Database session
        user_id: Database user ID

    Returns:
        Auth0 user ID or None if not found
    """
    user = get_user_by_id(db, user_id=user_id)
    if not user:
        return None
    return user.auth0_user_id  # type: ignore


def update_user_email(db: Session, user_id: int, email: str) -> bool:
    """
    Update user's email address in the database and set email_valid to 'Y'.

    Args:
        db: Database session
        user_id: Database user ID
        email: New email address

    Returns:
        True if successful, False otherwise
    """
    user = get_user_by_id(db, user_id=user_id)
    if not user:
        return False

    try:
        user.email = email  # type: ignore
        user.email_valid = "Y"  # type: ignore
        db.commit()
        db.refresh(user)
        logger.info(
            "User email updated in database",
            extra={
                "user_id": user_id,
                "email": email,
                "email_valid": "Y",
            },
        )
        return True
    except Exception as e:
        db.rollback()
        logger.error(
            "Failed to update user email",
            extra={"user_id": user_id, "email": email, "error": str(e)},
        )
        return False


def get_users_for_migration(db: Session, limit: int) -> List[Dict[str, Any]]:
    """
    Get users for migration to Auth0.

    Selects the first <limit> unique user.email values where user.auth0_user_id is NULL
    and email is not empty. For each unique email, selects the user who has the most
    recent tlog.upd_timestamp.

    Args:
        db: Database session
        limit: Maximum number of unique email addresses to process

    Returns:
        List of dictionaries containing user info for migration
    """
    from sqlalchemy import and_, distinct

    # Step 1: Get unique email addresses (non-empty, no auth0_user_id)
    unique_emails_query = (
        db.query(distinct(User.email))
        .filter(
            and_(
                User.auth0_user_id.is_(None),
                User.email != "",
                User.email.isnot(None),
            )
        )
        .limit(limit)
    )

    unique_emails = [email for (email,) in unique_emails_query.all()]

    if not unique_emails:
        return []

    # Step 2: For each email, find the user with the most recent tlog.upd_timestamp
    results = []
    for email in unique_emails:
        # Get all users with this email (where auth0_user_id is NULL)
        users_with_email = (
            db.query(User)
            .filter(
                and_(
                    User.email == email,
                    User.auth0_user_id.is_(None),
                )
            )
            .all()
        )

        if not users_with_email:
            continue

        # Find the user with the most recent tlog
        user_with_latest_log = None
        latest_timestamp = None

        for user in users_with_email:
            # Get the most recent tlog for this user
            latest_log = (
                db.query(TLog)
                .filter(TLog.user_id == user.id)
                .order_by(TLog.upd_timestamp.desc())
                .first()
            )

            if latest_log:
                if (
                    latest_timestamp is None
                    or latest_log.upd_timestamp > latest_timestamp
                ):
                    latest_timestamp = latest_log.upd_timestamp
                    user_with_latest_log = user
            elif user_with_latest_log is None:
                # If no logs exist for any user with this email, pick the first one
                user_with_latest_log = user

        if user_with_latest_log:
            results.append(
                {
                    "email": str(user_with_latest_log.email),
                    "user_id": int(user_with_latest_log.id),
                    "username": str(user_with_latest_log.name),
                    "firstname": str(user_with_latest_log.firstname or ""),
                    "surname": str(user_with_latest_log.surname or ""),
                }
            )

    return results
