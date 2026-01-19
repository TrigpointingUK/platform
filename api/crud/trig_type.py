"""
CRUD operations for trig_type and trig_category tables.
"""

from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from api.models.trig_type import TrigCategory, TrigType


def get_all_categories(db: Session) -> list[TrigCategory]:
    """Get all trig type categories ordered by sort_order."""
    return db.query(TrigCategory).order_by(TrigCategory.sort_order).all()


def get_category_by_id(db: Session, category_id: int) -> Optional[TrigCategory]:
    """Get a trig type category by ID."""
    return db.query(TrigCategory).filter(TrigCategory.id == category_id).first()


def get_category_by_code(db: Session, code: str) -> Optional[TrigCategory]:
    """Get a trig type category by code (case-insensitive)."""
    return (
        db.query(TrigCategory)
        .filter(func.upper(TrigCategory.code) == code.upper())
        .first()
    )


def get_categories_by_max_sort_order(
    db: Session, max_sort_order: int
) -> list[TrigCategory]:
    """Get all categories with sort_order <= max_sort_order."""
    return (
        db.query(TrigCategory)
        .filter(TrigCategory.sort_order <= max_sort_order)
        .order_by(TrigCategory.sort_order)
        .all()
    )


def get_all_types(db: Session) -> list[TrigType]:
    """Get all trig types with their categories, ordered by category then type sort_order."""
    return (
        db.query(TrigType)
        .options(joinedload(TrigType.category))
        .join(TrigCategory)
        .order_by(TrigCategory.sort_order, TrigType.sort_order)
        .all()
    )


def get_types_by_category_id(db: Session, category_id: int) -> list[TrigType]:
    """Get all types in a specific category."""
    return (
        db.query(TrigType)
        .filter(TrigType.category_id == category_id)
        .order_by(TrigType.sort_order)
        .all()
    )


def get_type_by_id(db: Session, type_id: int) -> Optional[TrigType]:
    """Get a trig type by ID."""
    return (
        db.query(TrigType)
        .options(joinedload(TrigType.category))
        .filter(TrigType.id == type_id)
        .first()
    )


def get_type_by_code(db: Session, code: str) -> Optional[TrigType]:
    """Get a trig type by code (case-insensitive)."""
    return (
        db.query(TrigType)
        .options(joinedload(TrigType.category))
        .filter(func.upper(TrigType.code) == code.upper())
        .first()
    )


def get_types_by_codes(db: Session, codes: list[str]) -> list[TrigType]:
    """Get multiple trig types by codes (case-insensitive)."""
    upper_codes = [c.upper() for c in codes]
    return (
        db.query(TrigType)
        .options(joinedload(TrigType.category))
        .filter(func.upper(TrigType.code).in_(upper_codes))
        .all()
    )


def get_type_ids_by_category_codes(db: Session, category_codes: list[str]) -> list[int]:
    """Get all type IDs for types in the specified categories."""
    upper_codes = [c.upper() for c in category_codes]
    result = (
        db.query(TrigType.id)
        .join(TrigCategory)
        .filter(func.upper(TrigCategory.code).in_(upper_codes))
        .all()
    )
    return [r[0] for r in result]


def get_type_ids_by_max_category_sort_order(
    db: Session, max_sort_order: int
) -> list[int]:
    """Get all type IDs for types in categories with sort_order <= max_sort_order."""
    result = (
        db.query(TrigType.id)
        .join(TrigCategory)
        .filter(TrigCategory.sort_order <= max_sort_order)
        .all()
    )
    return [r[0] for r in result]


def get_categories_with_types(db: Session) -> list[TrigCategory]:
    """Get all categories with their types eagerly loaded."""
    return (
        db.query(TrigCategory)
        .options(joinedload(TrigCategory.types))
        .order_by(TrigCategory.sort_order)
        .all()
    )
