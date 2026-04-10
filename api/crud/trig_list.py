"""
CRUD operations for trig_list and trig_list_item tables.
"""

from datetime import datetime, timezone
from typing import List, Optional, Sequence, Tuple

from sqlalchemy import func
from sqlalchemy.orm import Session

from api.models.status import Status
from api.models.trig import Trig
from api.models.trig_list import TrigList, TrigListItem
from api.models.trig_type import TrigCategory, TrigType
from api.models.user import User

MAX_LISTS_PER_USER = 10
MAX_ITEMS_PER_LIST = 1000
POSITION_GAP = 1000


# ---------------------------------------------------------------------------
# List CRUD
# ---------------------------------------------------------------------------


def get_user_lists(db: Session, user_id: int) -> List[TrigList]:
    return (
        db.query(TrigList)
        .filter(TrigList.owner_id == user_id)
        .order_by(TrigList.position)
        .all()
    )


def get_user_list_count(db: Session, user_id: int) -> int:
    return (
        db.query(func.count(TrigList.id)).filter(TrigList.owner_id == user_id).scalar()
        or 0
    )


def get_list(db: Session, list_id: int) -> Optional[TrigList]:
    return db.query(TrigList).filter(TrigList.id == list_id).first()


def get_list_item_count(db: Session, list_id: int) -> int:
    return (
        db.query(func.count(TrigListItem.id))
        .filter(TrigListItem.list_id == list_id)
        .scalar()
        or 0
    )


def create_list(
    db: Session,
    owner_id: int,
    name: str,
    description: Optional[str] = None,
    metadata: Optional[dict] = None,
    visibility: str = "private",
    editability: str = "private",
) -> TrigList:
    current_count = get_user_list_count(db, owner_id)
    if current_count >= MAX_LISTS_PER_USER:
        raise ValueError(f"Maximum of {MAX_LISTS_PER_USER} lists per user reached")

    max_pos = (
        db.query(func.max(TrigList.position))
        .filter(TrigList.owner_id == owner_id)
        .scalar()
    )
    next_pos = (max_pos or 0) + POSITION_GAP

    trig_list = TrigList(
        owner_id=owner_id,
        name=name,
        description=description,
        metadata_=metadata or {},
        visibility=visibility,
        editability=editability,
        position=next_pos,
    )
    db.add(trig_list)
    db.flush()
    return trig_list


def update_list(
    db: Session,
    trig_list: TrigList,
    name: Optional[str] = None,
    description: Optional[str] = ...,  # type: ignore[assignment]
    metadata: Optional[dict] = ...,  # type: ignore[assignment]
    visibility: Optional[str] = None,
    editability: Optional[str] = None,
) -> TrigList:
    if name is not None:
        trig_list.name = name  # type: ignore[assignment]
    if description is not ...:
        trig_list.description = description  # type: ignore[assignment]
    if metadata is not ...:
        trig_list.metadata_ = metadata  # type: ignore[assignment]
    if visibility is not None:
        trig_list.visibility = visibility  # type: ignore[assignment]
    if editability is not None:
        trig_list.editability = editability  # type: ignore[assignment]
    trig_list.updated_at = datetime.now(timezone.utc)  # type: ignore[assignment]
    db.flush()
    return trig_list


def delete_list(db: Session, trig_list: TrigList) -> None:
    owner_id = trig_list.owner_id
    list_id = trig_list.id
    db.delete(trig_list)
    # Clear default_list_id if this was the user's default
    db.query(User).filter(User.id == owner_id, User.default_list_id == list_id).update(
        {"default_list_id": None}
    )
    db.flush()


def reorder_lists(db: Session, owner_id: int, ordering: List[dict]) -> None:
    for entry in ordering:
        db.query(TrigList).filter(
            TrigList.id == entry["list_id"],
            TrigList.owner_id == owner_id,
        ).update({"position": entry["position"]})
    db.flush()


# ---------------------------------------------------------------------------
# Default list helpers
# ---------------------------------------------------------------------------


def ensure_default_list(db: Session, user_id: int) -> TrigList:
    """Return the user's default list, creating one named 'Marked' if needed."""
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise ValueError("User not found")

    if user.default_list_id is not None:
        existing = get_list(db, user.default_list_id)  # type: ignore[arg-type]
        if existing is not None:
            return existing

    trig_list = create_list(db, user_id, name="Marked")
    user.default_list_id = trig_list.id  # type: ignore[assignment]
    db.flush()
    return trig_list


# ---------------------------------------------------------------------------
# Item CRUD
# ---------------------------------------------------------------------------


def get_list_items(
    db: Session, list_id: int, skip: int = 0, limit: int = 50
) -> Tuple[Sequence, int]:
    """Return (items_with_trig_data, total_count) for a list."""
    base = (
        db.query(
            TrigListItem,
            Trig.waypoint,
            Trig.name.label("trig_name"),
            Trig.condition,
            Trig.osgb_gridref,
            Trig.wgs_lat,
            Trig.wgs_long,
            Trig.wgs_height,
            TrigType.code.label("type_code"),
            TrigType.name.label("type_name"),
            TrigCategory.code.label("category_code"),
            TrigCategory.name.label("category_name"),
            Status.name.label("status_name"),
        )
        .join(Trig, TrigListItem.trig_id == Trig.id)
        .outerjoin(TrigType, Trig.type_id == TrigType.id)
        .outerjoin(TrigCategory, TrigType.category_id == TrigCategory.id)
        .outerjoin(Status, Trig.status_id == Status.id)
        .filter(TrigListItem.list_id == list_id)
    )

    total = base.count()
    rows = base.order_by(TrigListItem.position).offset(skip).limit(limit).all()
    return rows, total


def add_item(
    db: Session,
    list_id: int,
    trig_id: int,
    user_id: int,
    name: Optional[str] = None,
    description: Optional[str] = None,
    metadata: Optional[dict] = None,
) -> TrigListItem:
    current_count = get_list_item_count(db, list_id)
    if current_count >= MAX_ITEMS_PER_LIST:
        raise ValueError(f"Maximum of {MAX_ITEMS_PER_LIST} items per list reached")

    max_pos = (
        db.query(func.max(TrigListItem.position))
        .filter(TrigListItem.list_id == list_id)
        .scalar()
    )
    next_pos = (max_pos or 0) + POSITION_GAP

    existing = get_item_by_list_and_trig(db, list_id, trig_id)
    if existing is not None:
        return existing

    item = TrigListItem(
        list_id=list_id,
        trig_id=trig_id,
        created_by=user_id,
        name=name,
        description=description,
        metadata_=metadata or {},
        position=next_pos,
    )
    db.add(item)
    db.flush()
    return item


def get_item(db: Session, item_id: int) -> Optional[TrigListItem]:
    return db.query(TrigListItem).filter(TrigListItem.id == item_id).first()


def get_item_by_list_and_trig(
    db: Session, list_id: int, trig_id: int
) -> Optional[TrigListItem]:
    return (
        db.query(TrigListItem)
        .filter(
            TrigListItem.list_id == list_id,
            TrigListItem.trig_id == trig_id,
        )
        .first()
    )


def remove_item(db: Session, item: TrigListItem) -> None:
    db.delete(item)
    db.flush()


def update_item(
    db: Session,
    item: TrigListItem,
    user_id: int,
    name: Optional[str] = ...,  # type: ignore[assignment]
    description: Optional[str] = ...,  # type: ignore[assignment]
    metadata: Optional[dict] = ...,  # type: ignore[assignment]
    position: Optional[int] = None,
) -> TrigListItem:
    if name is not ...:
        item.name = name  # type: ignore[assignment]
    if description is not ...:
        item.description = description  # type: ignore[assignment]
    if metadata is not ...:
        item.metadata_ = metadata  # type: ignore[assignment]
    if position is not None:
        item.position = position  # type: ignore[assignment]
    item.updated_by = user_id  # type: ignore[assignment]
    item.updated_at = datetime.now(timezone.utc)  # type: ignore[assignment]
    db.flush()
    return item


def reorder_items(db: Session, list_id: int, ordering: List[dict]) -> None:
    for entry in ordering:
        db.query(TrigListItem).filter(
            TrigListItem.id == entry["item_id"],
            TrigListItem.list_id == list_id,
        ).update(
            {
                "position": entry["position"],
                "updated_at": datetime.now(timezone.utc),
            }
        )
    db.flush()


# ---------------------------------------------------------------------------
# Batch membership query
# ---------------------------------------------------------------------------


def get_trig_list_membership(db: Session, user_id: int, trig_ids: List[int]) -> list:
    """Return list of (trig_id, list_id) pairs for trigs owned by this user."""
    if not trig_ids:
        return []
    return (
        db.query(TrigListItem.trig_id, TrigListItem.list_id)
        .join(TrigList, TrigListItem.list_id == TrigList.id)
        .filter(
            TrigList.owner_id == user_id,
            TrigListItem.trig_id.in_(trig_ids),
        )
        .all()
    )
