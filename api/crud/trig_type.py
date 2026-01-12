"""
CRUD operations for trig_type and trig_type_group tables.
"""

from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from api.models.trig_type import TrigType, TrigTypeGroup


def get_all_groups(db: Session) -> list[TrigTypeGroup]:
    """Get all trig type groups ordered by sort_order."""
    return db.query(TrigTypeGroup).order_by(TrigTypeGroup.sort_order).all()


def get_group_by_id(db: Session, group_id: int) -> Optional[TrigTypeGroup]:
    """Get a trig type group by ID."""
    return db.query(TrigTypeGroup).filter(TrigTypeGroup.id == group_id).first()


def get_group_by_code(db: Session, code: str) -> Optional[TrigTypeGroup]:
    """Get a trig type group by code (case-insensitive)."""
    return (
        db.query(TrigTypeGroup)
        .filter(func.upper(TrigTypeGroup.code) == code.upper())
        .first()
    )


def get_groups_by_max_sort_order(
    db: Session, max_sort_order: int
) -> list[TrigTypeGroup]:
    """Get all groups with sort_order <= max_sort_order."""
    return (
        db.query(TrigTypeGroup)
        .filter(TrigTypeGroup.sort_order <= max_sort_order)
        .order_by(TrigTypeGroup.sort_order)
        .all()
    )


def get_all_types(db: Session) -> list[TrigType]:
    """Get all trig types with their groups, ordered by group then type sort_order."""
    return (
        db.query(TrigType)
        .options(joinedload(TrigType.group))
        .join(TrigTypeGroup)
        .order_by(TrigTypeGroup.sort_order, TrigType.sort_order)
        .all()
    )


def get_types_by_group_id(db: Session, group_id: int) -> list[TrigType]:
    """Get all types in a specific group."""
    return (
        db.query(TrigType)
        .filter(TrigType.group_id == group_id)
        .order_by(TrigType.sort_order)
        .all()
    )


def get_type_by_id(db: Session, type_id: int) -> Optional[TrigType]:
    """Get a trig type by ID."""
    return (
        db.query(TrigType)
        .options(joinedload(TrigType.group))
        .filter(TrigType.id == type_id)
        .first()
    )


def get_type_by_code(db: Session, code: str) -> Optional[TrigType]:
    """Get a trig type by code (case-insensitive)."""
    return (
        db.query(TrigType)
        .options(joinedload(TrigType.group))
        .filter(func.upper(TrigType.code) == code.upper())
        .first()
    )


def get_types_by_codes(db: Session, codes: list[str]) -> list[TrigType]:
    """Get multiple trig types by codes (case-insensitive)."""
    upper_codes = [c.upper() for c in codes]
    return (
        db.query(TrigType)
        .options(joinedload(TrigType.group))
        .filter(func.upper(TrigType.code).in_(upper_codes))
        .all()
    )


def get_type_ids_by_group_codes(db: Session, group_codes: list[str]) -> list[int]:
    """Get all type IDs for types in the specified groups."""
    upper_codes = [c.upper() for c in group_codes]
    result = (
        db.query(TrigType.id)
        .join(TrigTypeGroup)
        .filter(func.upper(TrigTypeGroup.code).in_(upper_codes))
        .all()
    )
    return [r[0] for r in result]


def get_type_ids_by_max_group_sort_order(db: Session, max_sort_order: int) -> list[int]:
    """Get all type IDs for types in groups with sort_order <= max_sort_order."""
    result = (
        db.query(TrigType.id)
        .join(TrigTypeGroup)
        .filter(TrigTypeGroup.sort_order <= max_sort_order)
        .all()
    )
    return [r[0] for r in result]


def get_groups_with_types(db: Session) -> list[TrigTypeGroup]:
    """Get all groups with their types eagerly loaded."""
    return (
        db.query(TrigTypeGroup)
        .options(joinedload(TrigTypeGroup.types))
        .order_by(TrigTypeGroup.sort_order)
        .all()
    )
