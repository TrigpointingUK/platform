"""
CRUD helpers for the trig_variant lookup.

Groups have no table of their own: each variant row carries its group's code
and name, so a group exists while it has values and renaming one updates
every row in it.
"""

from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from api.models.trig import Trig
from api.models.trig_type import TrigType
from api.models.trig_variant import TrigVariant


def get_all(db: Session) -> list[TrigVariant]:
    """Every variant, by group then display order."""
    return (
        db.query(TrigVariant)
        .order_by(TrigVariant.group_name, TrigVariant.sort_order, TrigVariant.name)
        .all()
    )


def get_by_id(db: Session, variant_id: int) -> Optional[TrigVariant]:
    return db.query(TrigVariant).filter(TrigVariant.id == variant_id).first()


def get_by_code(db: Session, code: str) -> Optional[TrigVariant]:
    return db.query(TrigVariant).filter(TrigVariant.code == code).first()


def get_group(db: Session, group_code: str) -> list[TrigVariant]:
    """The variants in a group (empty if there's no such group)."""
    return db.query(TrigVariant).filter(TrigVariant.group_code == group_code).all()


def get_group_names(db: Session) -> dict[str, str]:
    """Group code -> group name, for every group."""
    rows = db.query(TrigVariant.group_code, TrigVariant.group_name).distinct().all()
    return {str(code): str(name) for code, name in rows}


def get_trig_counts(db: Session) -> dict[int, int]:
    """Variant ID -> number of trigs (including deleted ones) recording it."""
    rows = (
        db.query(Trig.variant_id, func.count(Trig.id))
        .filter(Trig.variant_id.isnot(None))
        .group_by(Trig.variant_id)
        .all()
    )
    return {int(variant_id): int(count) for variant_id, count in rows}


def get_usage_count(db: Session, variant_id: int) -> int:
    """Number of trigs (including deleted ones) recording this variant."""
    return db.query(Trig).filter(Trig.variant_id == variant_id).count()


def get_type_names(db: Session) -> dict[str, list[str]]:
    """Group code -> names of the types that offer it, in type order."""
    rows = (
        db.query(TrigType.variant_group, TrigType.name)
        .filter(TrigType.variant_group.isnot(None))
        .order_by(TrigType.sort_order, TrigType.name)
        .all()
    )
    names: dict[str, list[str]] = {}
    for group_code, name in rows:
        names.setdefault(str(group_code), []).append(str(name))
    return names


def create(
    db: Session,
    group_code: str,
    group_name: str,
    code: str,
    name: str,
    sort_order: int,
) -> TrigVariant:
    variant = TrigVariant(
        group_code=group_code,
        group_name=group_name,
        code=code,
        name=name,
        sort_order=sort_order,
    )
    db.add(variant)
    db.commit()
    db.refresh(variant)
    return variant


def update(
    db: Session,
    variant_id: int,
    name: Optional[str] = None,
    sort_order: Optional[int] = None,
) -> Optional[TrigVariant]:
    """Update a variant's name and/or order. None if not found."""
    variant = get_by_id(db, variant_id)
    if not variant:
        return None
    if name is not None:
        variant.name = name  # type: ignore[assignment]
    if sort_order is not None:
        variant.sort_order = sort_order  # type: ignore[assignment]
    db.commit()
    db.refresh(variant)
    return variant


def rename_group(db: Session, group_code: str, name: str) -> int:
    """Rename a group on every one of its rows. Returns the rows updated."""
    updated = (
        db.query(TrigVariant)
        .filter(TrigVariant.group_code == group_code)
        .update({TrigVariant.group_name: name}, synchronize_session=False)
    )
    db.commit()
    return int(updated)


def delete(db: Session, variant_id: int) -> bool:
    variant = get_by_id(db, variant_id)
    if not variant:
        return False
    db.delete(variant)
    db.commit()
    return True
