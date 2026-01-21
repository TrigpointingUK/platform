"""
CRUD helpers for condition lookup.
"""

from typing import Optional

from sqlalchemy.orm import Session

from api.models.condition import Condition


def get_condition_by_code(db: Session, code: str) -> Optional[Condition]:
    """
    Get a condition by its code.

    Args:
        db: Database session
        code: The condition code (single character)

    Returns:
        Condition object if found, None otherwise
    """
    return db.query(Condition).filter(Condition.code == code).first()


def get_condition_name_by_code(db: Session, code: str) -> Optional[str]:
    """
    Get a condition name by its code.

    Args:
        db: Database session
        code: The condition code (single character)

    Returns:
        Condition name if found, None otherwise
    """
    return db.query(Condition.name).filter(Condition.code == code).scalar()


def get_all_conditions(db: Session) -> list[Condition]:
    """
    Get all condition records ordered by sort_order.

    Args:
        db: Database session

    Returns:
        List of all Condition objects ordered by sort_order
    """
    return db.query(Condition).order_by(Condition.sort_order).all()


def create_condition(
    db: Session,
    code: str,
    name: str,
    sort_order: int,
    description: Optional[str] = None,
    icon_file: Optional[str] = None,
    trig_colour: Optional[str] = None,
    log_colour: Optional[str] = None,
    similar_codes: Optional[str] = None,
    wiki_url: Optional[str] = None,
) -> Condition:
    """
    Create a new condition record.

    Args:
        db: Database session
        code: The condition code (single character, primary key)
        name: Human-readable name (unique)
        sort_order: Display order
        description: Optional description
        icon_file: Optional icon filename
        trig_colour: Optional colour for trig display
        log_colour: Optional colour for log display
        similar_codes: Optional string of similar condition codes
        wiki_url: Optional URL to wiki page

    Returns:
        Created Condition object
    """
    condition = Condition(
        code=code.strip().upper(),
        name=name.strip(),
        sort_order=sort_order,
        description=description.strip() if description else None,
        icon_file=icon_file.strip() if icon_file else None,
        trig_colour=trig_colour.strip() if trig_colour else None,
        log_colour=log_colour.strip() if log_colour else None,
        similar_codes=similar_codes.strip().upper() if similar_codes else None,
        wiki_url=wiki_url.strip() if wiki_url else None,
    )
    db.add(condition)
    db.commit()
    db.refresh(condition)
    return condition


def update_condition(
    db: Session,
    code: str,
    name: Optional[str] = None,
    description: Optional[str] = None,
    icon_file: Optional[str] = None,
    trig_colour: Optional[str] = None,
    log_colour: Optional[str] = None,
    similar_codes: Optional[str] = None,
    wiki_url: Optional[str] = None,
    sort_order: Optional[int] = None,
) -> Optional[Condition]:
    """
    Update an existing condition record.

    Args:
        db: Database session
        code: The condition code to update
        name: New name (optional)
        description: New description (optional)
        icon_file: New icon filename (optional)
        trig_colour: New trig colour (optional)
        log_colour: New log colour (optional)
        similar_codes: New similar codes (optional)
        wiki_url: New wiki URL (optional)
        sort_order: New sort order (optional)

    Returns:
        Updated Condition object if found, None otherwise
    """
    condition = get_condition_by_code(db, code)
    if not condition:
        return None

    if name is not None:
        condition.name = name.strip()  # type: ignore[assignment]
    if description is not None:
        condition.description = description.strip() if description else None  # type: ignore[assignment]
    if icon_file is not None:
        condition.icon_file = icon_file.strip() if icon_file else None  # type: ignore[assignment]
    if trig_colour is not None:
        condition.trig_colour = trig_colour.strip() if trig_colour else None  # type: ignore[assignment]
    if log_colour is not None:
        condition.log_colour = log_colour.strip() if log_colour else None  # type: ignore[assignment]
    if similar_codes is not None:
        val = similar_codes.strip().upper() if similar_codes else None
        condition.similar_codes = val  # type: ignore[assignment]
    if wiki_url is not None:
        condition.wiki_url = wiki_url.strip() if wiki_url else None  # type: ignore[assignment]
    if sort_order is not None:
        condition.sort_order = sort_order  # type: ignore[assignment]

    db.commit()
    db.refresh(condition)
    return condition


def delete_condition(db: Session, code: str) -> bool:
    """
    Delete a condition record.

    Args:
        db: Database session
        code: The condition code to delete

    Returns:
        True if deleted, False if not found
    """
    condition = get_condition_by_code(db, code)
    if not condition:
        return False

    db.delete(condition)
    db.commit()
    return True


def get_condition_usage_count(db: Session, code: str) -> int:
    """
    Get the count of tlogs using a specific condition.

    Args:
        db: Database session
        code: The condition code to check

    Returns:
        Count of tlogs using this condition
    """
    from api.models.user import TLog

    return db.query(TLog).filter(TLog.condition == code).count()
