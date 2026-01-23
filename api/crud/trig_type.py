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


# ============================================================================
# Category CRUD operations
# ============================================================================


def create_category(
    db: Session,
    code: str,
    name: str,
    sort_order: int,
    description: Optional[str] = None,
    wiki_url: Optional[str] = None,
) -> TrigCategory:
    """Create a new trig type category."""
    category = TrigCategory(
        code=code.upper(),
        name=name,
        description=description,
        wiki_url=wiki_url,
        sort_order=sort_order,
    )
    db.add(category)
    db.commit()
    db.refresh(category)
    return category


def update_category(
    db: Session,
    category_id: int,
    code: Optional[str] = None,
    name: Optional[str] = None,
    description: Optional[str] = None,
    wiki_url: Optional[str] = None,
    sort_order: Optional[int] = None,
) -> Optional[TrigCategory]:
    """Update an existing trig type category."""
    category = get_category_by_id(db, category_id)
    if not category:
        return None

    if code is not None:
        category.code = code.upper()  # type: ignore[assignment]
    if name is not None:
        category.name = name  # type: ignore[assignment]
    if description is not None:
        category.description = description if description else None  # type: ignore[assignment]
    if wiki_url is not None:
        category.wiki_url = wiki_url if wiki_url else None  # type: ignore[assignment]
    if sort_order is not None:
        category.sort_order = sort_order  # type: ignore[assignment]

    db.commit()
    db.refresh(category)
    return category


def delete_category(db: Session, category_id: int) -> bool:
    """
    Delete a trig type category.

    Returns True if deleted, False if not found.
    Raises an exception if the category has types assigned to it.
    """
    category = get_category_by_id(db, category_id)
    if not category:
        return False

    # Check if any types are in this category
    types_count = db.query(TrigType).filter(TrigType.category_id == category_id).count()
    if types_count > 0:
        raise ValueError(
            f"Cannot delete category: {types_count} types are assigned to it"
        )

    db.delete(category)
    db.commit()
    return True


def reorder_categories(db: Session, category_order: list[int]) -> list[TrigCategory]:
    """
    Reorder categories by swapping sort_order values among the given categories.

    This preserves the existing sort_order values and just reassigns them,
    avoiding conflicts with categories not being reordered.

    Uses a two-phase update to avoid unique constraint violations:
    1. Set all to negative temporary values
    2. Assign the original sort_order values in new order

    Args:
        category_order: List of category IDs in desired order

    Returns:
        Updated list of categories
    """
    # Get current sort_orders for categories being reordered
    existing_orders = []
    for category_id in category_order:
        cat = db.query(TrigCategory).filter(TrigCategory.id == category_id).first()
        if cat:
            existing_orders.append(cat.sort_order)

    # Sort the existing orders so we assign them in ascending order
    existing_orders.sort()

    # Phase 1: Set to negative temporary values to avoid conflicts
    for index, category_id in enumerate(category_order):
        db.query(TrigCategory).filter(TrigCategory.id == category_id).update(
            {"sort_order": -(index + 1)}
        )
    db.flush()

    # Phase 2: Assign sorted order values to categories in new order
    for index, category_id in enumerate(category_order):
        new_order = (
            existing_orders[index] if index < len(existing_orders) else index + 1
        )
        db.query(TrigCategory).filter(TrigCategory.id == category_id).update(
            {"sort_order": new_order}
        )
    db.commit()
    return get_all_categories(db)


def get_next_category_sort_order(db: Session) -> int:
    """Get the next available sort_order for a new category."""
    max_order = db.query(func.max(TrigCategory.sort_order)).scalar()
    return (max_order or 0) + 1


# ============================================================================
# Type CRUD operations
# ============================================================================


def create_type(
    db: Session,
    category_id: int,
    code: str,
    name: str,
    sort_order: int,
    description: Optional[str] = None,
    wiki_url: Optional[str] = None,
    legacy_physical_type: Optional[str] = None,
) -> TrigType:
    """Create a new trig type."""
    trig_type = TrigType(
        category_id=category_id,
        code=code.upper(),
        name=name,
        description=description,
        wiki_url=wiki_url,
        sort_order=sort_order,
        legacy_physical_type=legacy_physical_type,
    )
    db.add(trig_type)
    db.commit()
    db.refresh(trig_type)
    return trig_type


def update_type(
    db: Session,
    type_id: int,
    category_id: Optional[int] = None,
    code: Optional[str] = None,
    name: Optional[str] = None,
    description: Optional[str] = None,
    wiki_url: Optional[str] = None,
    sort_order: Optional[int] = None,
    legacy_physical_type: Optional[str] = None,
) -> Optional[TrigType]:
    """Update an existing trig type."""
    trig_type = get_type_by_id(db, type_id)
    if not trig_type:
        return None

    if category_id is not None and category_id != trig_type.category_id:
        # When moving to a new category, auto-assign sort_order to avoid conflicts
        new_sort_order = get_next_type_sort_order(db, category_id)
        trig_type.sort_order = new_sort_order  # type: ignore[assignment]
        trig_type.category_id = category_id  # type: ignore[assignment]
    elif category_id is not None:
        trig_type.category_id = category_id  # type: ignore[assignment]
    if code is not None:
        trig_type.code = code.upper()  # type: ignore[assignment]
    if name is not None:
        trig_type.name = name  # type: ignore[assignment]
    if description is not None:
        trig_type.description = description if description else None  # type: ignore[assignment]
    if wiki_url is not None:
        trig_type.wiki_url = wiki_url if wiki_url else None  # type: ignore[assignment]
    if sort_order is not None:
        trig_type.sort_order = sort_order  # type: ignore[assignment]
    if legacy_physical_type is not None:
        trig_type.legacy_physical_type = legacy_physical_type if legacy_physical_type else None  # type: ignore[assignment]

    db.commit()
    db.refresh(trig_type)
    return trig_type


def delete_type(db: Session, type_id: int) -> bool:
    """
    Delete a trig type.

    Returns True if deleted, False if not found.
    Note: This does not check if trigs are using this type - caller should handle that.
    """
    trig_type = get_type_by_id(db, type_id)
    if not trig_type:
        return False

    db.delete(trig_type)
    db.commit()
    return True


def reorder_types(
    db: Session, category_id: int, type_order: list[int]
) -> list[TrigType]:
    """
    Reorder types within a category by setting sort_order based on list position.

    Uses a two-phase update to avoid unique constraint violations:
    1. Set all to negative temporary values
    2. Set final positive values

    Args:
        category_id: The category containing the types
        type_order: List of type IDs in desired order

    Returns:
        Updated list of types in the category
    """
    # Phase 1: Set to negative temporary values to avoid conflicts
    for index, type_id in enumerate(type_order):
        db.query(TrigType).filter(
            TrigType.id == type_id, TrigType.category_id == category_id
        ).update({"sort_order": -(index + 1)})
    db.flush()

    # Phase 2: Set final positive values
    for index, type_id in enumerate(type_order):
        db.query(TrigType).filter(
            TrigType.id == type_id, TrigType.category_id == category_id
        ).update({"sort_order": index + 1})
    db.commit()
    return get_types_by_category_id(db, category_id)


def get_next_type_sort_order(db: Session, category_id: int) -> int:
    """Get the next available sort_order for a new type in a category."""
    max_order = (
        db.query(func.max(TrigType.sort_order))
        .filter(TrigType.category_id == category_id)
        .scalar()
    )
    return (max_order or 0) + 1


def get_type_usage_count(db: Session, type_id: int) -> int:
    """Get the number of trigs using this type."""
    from api.models.trig import Trig

    return db.query(Trig).filter(Trig.type_id == type_id).count()
