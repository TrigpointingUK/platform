"""
CRUD helpers for status lookup.
"""

from typing import Optional

from sqlalchemy.orm import Session

from api.models.status import Status


def get_status_name_by_id(db: Session, status_id: int) -> Optional[str]:
    # Return a plain string using scalar() to avoid ORM attribute types in typing
    return db.query(Status.name).filter(Status.id == status_id).scalar()


def get_all_statuses(db: Session) -> list[Status]:
    """
    Get all status records for dropdown population.

    Args:
        db: Database session

    Returns:
        List of all Status objects
    """
    return db.query(Status).order_by(Status.id).all()


def get_status_by_id(db: Session, status_id: int) -> Optional[Status]:
    """
    Get a status by its ID.

    Args:
        db: Database session
        status_id: The status ID

    Returns:
        Status object if found, None otherwise
    """
    return db.query(Status).filter(Status.id == status_id).first()


def create_status(
    db: Session,
    status_id: int,
    name: str,
    descr: str,
    limit_descr: str,
) -> Status:
    """
    Create a new status record.

    Args:
        db: Database session
        status_id: The status ID (primary key, manually assigned)
        name: Short name (max 20 chars)
        descr: Description (max 50 chars)
        limit_descr: Limit description (max 255 chars)

    Returns:
        Created Status object
    """
    status = Status(
        id=status_id,
        name=name.strip(),
        descr=descr.strip(),
        limit_descr=limit_descr.strip(),
    )
    db.add(status)
    db.commit()
    db.refresh(status)
    return status


def update_status(
    db: Session,
    status_id: int,
    name: Optional[str] = None,
    descr: Optional[str] = None,
    limit_descr: Optional[str] = None,
) -> Optional[Status]:
    """
    Update an existing status record.

    Args:
        db: Database session
        status_id: The status ID to update
        name: New name (optional)
        descr: New description (optional)
        limit_descr: New limit description (optional)

    Returns:
        Updated Status object if found, None otherwise
    """
    status = get_status_by_id(db, status_id)
    if not status:
        return None

    if name is not None:
        status.name = name.strip()  # type: ignore[assignment]
    if descr is not None:
        status.descr = descr.strip()  # type: ignore[assignment]
    if limit_descr is not None:
        status.limit_descr = limit_descr.strip()  # type: ignore[assignment]

    db.commit()
    db.refresh(status)
    return status


def delete_status(db: Session, status_id: int) -> bool:
    """
    Delete a status record.

    Args:
        db: Database session
        status_id: The status ID to delete

    Returns:
        True if deleted, False if not found
    """
    status = get_status_by_id(db, status_id)
    if not status:
        return False

    db.delete(status)
    db.commit()
    return True


def get_status_usage_count(db: Session, status_id: int) -> int:
    """
    Get the count of trigs using a specific status.

    Args:
        db: Database session
        status_id: The status ID to check

    Returns:
        Count of trigs using this status
    """
    from api.models.trig import Trig

    return db.query(Trig).filter(Trig.status_id == status_id).count()
