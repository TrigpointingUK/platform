"""
CRUD helpers for the historic use / recent use lookups.

Each kind pairs a lookup model with the trig column holding its value by
name. The functions take the kind so both lookups share one implementation.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional, Union

from sqlalchemy import Column
from sqlalchemy.orm import Session

from api.models.trig import Trig
from api.models.trig_use import CurrentUse, HistoricUse

TrigUseModel = Union[HistoricUse, CurrentUse]


class TrigUseKind(str, Enum):
    """Which lookup: trig.historic_use or trig.current_use."""

    HISTORIC = "historic"
    CURRENT = "current"


@dataclass(frozen=True)
class TrigUseConfig:
    # HistoricUse or CurrentUse; Any because mypy can't type queries on a union
    model: Any
    trig_column: Column
    max_length: int
    label: str
    cache_pattern: str


CONFIG: dict[TrigUseKind, TrigUseConfig] = {
    TrigUseKind.HISTORIC: TrigUseConfig(
        model=HistoricUse,
        trig_column=Trig.historic_use,  # type: ignore[arg-type]
        max_length=30,
        label="Historic use",
        cache_pattern="reference_historic_use*",
    ),
    TrigUseKind.CURRENT: TrigUseConfig(
        model=CurrentUse,
        trig_column=Trig.current_use,  # type: ignore[arg-type]
        max_length=25,
        label="Recent use",
        cache_pattern="reference_current_use*",
    ),
}


def get_all(db: Session, kind: TrigUseKind) -> list[TrigUseModel]:
    """All values of a kind in display order."""
    model = CONFIG[kind].model
    return db.query(model).order_by(model.sort_order, model.name).all()


def get_by_id(db: Session, kind: TrigUseKind, use_id: int) -> Optional[TrigUseModel]:
    model = CONFIG[kind].model
    return db.query(model).filter(model.id == use_id).first()


def get_by_name(db: Session, kind: TrigUseKind, name: str) -> Optional[TrigUseModel]:
    model = CONFIG[kind].model
    return db.query(model).filter(model.name == name).first()


def create(
    db: Session,
    kind: TrigUseKind,
    name: str,
    description: Optional[str],
    sort_order: int,
) -> TrigUseModel:
    value = CONFIG[kind].model(
        name=name.strip(),
        description=(description or "").strip() or None,
        sort_order=sort_order,
    )
    db.add(value)
    db.commit()
    db.refresh(value)
    return value


def update(
    db: Session,
    kind: TrigUseKind,
    use_id: int,
    name: Optional[str] = None,
    description: Optional[str] = None,
    sort_order: Optional[int] = None,
) -> tuple[Optional[TrigUseModel], int]:
    """
    Update a value. A rename is applied to the trigs using it in the same
    transaction.

    Returns the updated value (None if not found) and the number of trigs
    renamed.
    """
    value = get_by_id(db, kind, use_id)
    if not value:
        return None, 0

    renamed = 0
    if name is not None and name.strip() != value.name:
        new_name = name.strip()
        renamed = (
            db.query(Trig)
            .filter(CONFIG[kind].trig_column == value.name)
            .update({CONFIG[kind].trig_column: new_name}, synchronize_session=False)
        )
        value.name = new_name  # type: ignore[assignment]
    if description is not None:
        value.description = description.strip() or None  # type: ignore[assignment]
    if sort_order is not None:
        value.sort_order = sort_order  # type: ignore[assignment]

    db.commit()
    db.refresh(value)
    return value, renamed


def delete(db: Session, kind: TrigUseKind, use_id: int) -> bool:
    value = get_by_id(db, kind, use_id)
    if not value:
        return False
    db.delete(value)
    db.commit()
    return True


def get_usage_count(db: Session, kind: TrigUseKind, name: str) -> int:
    """Number of trigs (including deleted ones) with this value."""
    return db.query(Trig).filter(CONFIG[kind].trig_column == name).count()
