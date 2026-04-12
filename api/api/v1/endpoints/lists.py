"""
API endpoints for trig lists (user-curated collections of trigpoints).
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from api.api.deps import (
    get_current_user,
    get_current_user_optional,
    get_db,
    has_scope,
)
from api.crud import trig_list as trig_list_crud
from api.models.trig_list import TrigList
from api.models.user import User
from api.schemas.trig_list import (
    TrigListCreate,
    TrigListItemCreate,
    TrigListItemReorderRequest,
    TrigListItemResponse,
    TrigListItemsPage,
    TrigListItemUpdate,
    TrigListMembership,
    TrigListMembershipResponse,
    TrigListReorderRequest,
    TrigListResponse,
    TrigListSummary,
    TrigListUpdate,
    TrigSummary,
)

router = APIRouter()


# ---------------------------------------------------------------------------
# Permission helpers
# ---------------------------------------------------------------------------


def _token_payload(user: User) -> dict:
    return getattr(user, "_token_payload", {})


def _user_is_admin(user: User) -> bool:
    return has_scope(_token_payload(user), "api:admin")


def _can_view_list(trig_list: TrigList, user: Optional[User]) -> bool:
    if trig_list.visibility == "public":
        return True
    if user is None:
        return False
    if trig_list.owner_id == user.id:
        return True
    if trig_list.visibility == "admins" and _user_is_admin(user):
        return True
    return False


def _can_edit_list_items(trig_list: TrigList, user: User) -> bool:
    if trig_list.owner_id == user.id:
        return True
    if trig_list.editability == "public":
        return True
    if trig_list.editability == "admins" and _user_is_admin(user):
        return True
    return False


def _validate_admin_fields(
    user: User, visibility: Optional[str], editability: Optional[str]
) -> None:
    """Reject non-private editability and 'admins' visibility for non-admin users."""
    is_admin = _user_is_admin(user)
    if visibility == "admins" and not is_admin:
        raise HTTPException(
            status_code=403,
            detail="Only admins can set visibility to 'admins'",
        )
    if editability in ("admins", "public") and not is_admin:
        raise HTTPException(
            status_code=403,
            detail="Only admins can set editability to a shared value",
        )


def _require_list_visible(list_id: int, db: Session, user: Optional[User]) -> TrigList:
    trig_list = trig_list_crud.get_list(db, list_id)
    if trig_list is None:
        raise HTTPException(status_code=404, detail="List not found")
    if not _can_view_list(trig_list, user):
        raise HTTPException(status_code=404, detail="List not found")
    return trig_list


def _require_list_owner(list_id: int, db: Session, user: User) -> TrigList:
    trig_list = trig_list_crud.get_list(db, list_id)
    if trig_list is None:
        raise HTTPException(status_code=404, detail="List not found")
    if trig_list.owner_id != user.id:
        raise HTTPException(status_code=403, detail="Only the list owner can do this")
    return trig_list


def _require_list_item_editable(list_id: int, db: Session, user: User) -> TrigList:
    trig_list = trig_list_crud.get_list(db, list_id)
    if trig_list is None:
        raise HTTPException(status_code=404, detail="List not found")
    if not _can_edit_list_items(trig_list, user):
        raise HTTPException(
            status_code=403,
            detail="You do not have permission to edit items in this list",
        )
    return trig_list


def _list_to_response(
    trig_list: TrigList, db: Session, user: Optional[User] = None
) -> TrigListResponse:
    item_count = trig_list_crud.get_list_item_count(db, trig_list.id)  # type: ignore[arg-type]
    is_default = False
    if user is not None:
        is_default = user.default_list_id == trig_list.id  # type: ignore[assignment]

    owner_name = None
    if user is None or trig_list.owner_id != user.id:
        owner = db.query(User.name).filter(User.id == trig_list.owner_id).first()
        owner_name = owner.name if owner else None

    return TrigListResponse(
        id=trig_list.id,  # type: ignore[arg-type]
        owner_id=trig_list.owner_id,  # type: ignore[arg-type]
        owner_name=owner_name,
        name=trig_list.name,  # type: ignore[arg-type]
        description=trig_list.description,  # type: ignore[arg-type]
        metadata_=trig_list.metadata_,  # type: ignore[arg-type]
        visibility=trig_list.visibility,  # type: ignore[arg-type]
        editability=trig_list.editability,  # type: ignore[arg-type]
        position=trig_list.position,  # type: ignore[arg-type]
        item_count=item_count,
        is_default=is_default,
        created_at=trig_list.created_at,  # type: ignore[arg-type]
        updated_at=trig_list.updated_at,  # type: ignore[arg-type]
    )


def _list_to_summary(trig_list: TrigList, db: Session, user: User) -> TrigListSummary:
    item_count = trig_list_crud.get_list_item_count(db, trig_list.id)  # type: ignore[arg-type]
    return TrigListSummary(
        id=trig_list.id,  # type: ignore[arg-type]
        name=trig_list.name,  # type: ignore[arg-type]
        item_count=item_count,
        is_default=(user.default_list_id == trig_list.id),  # type: ignore[arg-type]
    )


# ---------------------------------------------------------------------------
# List endpoints
# ---------------------------------------------------------------------------


@router.get("", response_model=list[TrigListResponse])
def get_my_lists(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    lists = trig_list_crud.get_user_lists(db, current_user.id)  # type: ignore[arg-type]
    return [_list_to_response(tl, db, current_user) for tl in lists]


@router.get("/editable", response_model=list[TrigListResponse])
def get_editable_lists(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Lists the user can edit but does not own (shared lists)."""
    is_admin = _user_is_admin(current_user)
    lists = trig_list_crud.get_editable_lists(
        db, current_user.id, is_admin  # type: ignore[arg-type]
    )
    return [_list_to_response(tl, db, current_user) for tl in lists]


@router.post("", response_model=TrigListResponse, status_code=201)
def create_list(
    data: TrigListCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _validate_admin_fields(current_user, data.visibility, data.editability)
    try:
        trig_list = trig_list_crud.create_list(
            db,
            owner_id=current_user.id,  # type: ignore[arg-type]
            name=data.name,
            description=data.description,
            metadata=data.metadata,
            visibility=data.visibility,
            editability=data.editability,
        )
        db.commit()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return _list_to_response(trig_list, db, current_user)


# Static paths must appear before /{list_id} to avoid path parameter capture.


@router.post("/reorder", status_code=204)
def reorder_lists(
    data: TrigListReorderRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    trig_list_crud.reorder_lists(db, current_user.id, data.ordering)  # type: ignore[arg-type]
    db.commit()


@router.get("/membership", response_model=TrigListMembershipResponse)
def get_trig_list_membership(
    trig_ids: str = Query(..., description="Comma-separated trig IDs"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Batch query: which of the current user's lists contain these trigs?"""
    parsed_ids = [int(x.strip()) for x in trig_ids.split(",") if x.strip().isdigit()]
    if not parsed_ids:
        return TrigListMembershipResponse(items=[])

    pairs = trig_list_crud.get_trig_list_membership(db, current_user.id, parsed_ids)  # type: ignore[arg-type]
    by_trig: dict[int, list[int]] = {}
    for trig_id_val, list_id_val in pairs:
        by_trig.setdefault(trig_id_val, []).append(list_id_val)

    items = [
        TrigListMembership(trig_id=tid, list_ids=by_trig.get(tid, []))
        for tid in parsed_ids
    ]
    return TrigListMembershipResponse(items=items)


@router.post("/default/toggle/{trig_id}")
def toggle_trig_in_default_list(
    trig_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Toggle a trig in/out of the user's default list (lazy-creates if needed)."""
    default_list = trig_list_crud.ensure_default_list(db, current_user.id)  # type: ignore[arg-type]
    existing = trig_list_crud.get_item_by_list_and_trig(db, default_list.id, trig_id)  # type: ignore[arg-type]
    if existing:
        trig_list_crud.remove_item(db, existing)
        db.commit()
        return {"action": "removed", "list_id": default_list.id, "trig_id": trig_id}
    else:
        trig_list_crud.add_item(db, default_list.id, trig_id, current_user.id)  # type: ignore[arg-type]
        db.commit()
        return {"action": "added", "list_id": default_list.id, "trig_id": trig_id}


@router.post("/{list_id}/set-default", status_code=200)
def set_default_list(
    list_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Set a list as the user's default list for quick-add."""
    trig_list = _require_list_owner(list_id, db, current_user)
    current_user.default_list_id = trig_list.id  # type: ignore[assignment]
    db.commit()
    return {"default_list_id": trig_list.id}


@router.post("/{list_id}/toggle/{trig_id}")
def toggle_trig_in_list(
    list_id: int,
    trig_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Toggle a trig in/out of the specified list."""
    _require_list_item_editable(list_id, db, current_user)
    existing = trig_list_crud.get_item_by_list_and_trig(db, list_id, trig_id)
    if existing:
        trig_list_crud.remove_item(db, existing)
        db.commit()
        return {"action": "removed", "list_id": list_id, "trig_id": trig_id}
    else:
        trig_list_crud.add_item(db, list_id, trig_id, current_user.id)  # type: ignore[arg-type]
        db.commit()
        return {"action": "added", "list_id": list_id, "trig_id": trig_id}


# Parameterised routes below this point.


@router.get("/{list_id}", response_model=TrigListResponse)
def get_list_detail(
    list_id: int,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    trig_list = _require_list_visible(list_id, db, current_user)
    return _list_to_response(trig_list, db, current_user)


@router.patch("/{list_id}", response_model=TrigListResponse)
def update_list(
    list_id: int,
    data: TrigListUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    trig_list = _require_list_owner(list_id, db, current_user)
    _validate_admin_fields(current_user, data.visibility, data.editability)

    kwargs: dict = {}
    if data.name is not None:
        kwargs["name"] = data.name
    if data.description is not None:
        kwargs["description"] = data.description
    elif "description" in (data.model_fields_set or set()):
        kwargs["description"] = data.description
    if data.metadata is not None:
        kwargs["metadata"] = data.metadata
    if data.visibility is not None:
        kwargs["visibility"] = data.visibility
    if data.editability is not None:
        kwargs["editability"] = data.editability

    trig_list = trig_list_crud.update_list(db, trig_list, **kwargs)
    db.commit()
    return _list_to_response(trig_list, db, current_user)


@router.delete("/{list_id}", status_code=204)
def delete_list(
    list_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    trig_list = _require_list_owner(list_id, db, current_user)
    trig_list_crud.delete_list(db, trig_list)
    db.commit()


# ---------------------------------------------------------------------------
# Item endpoints
# ---------------------------------------------------------------------------


def _row_to_item_response(row) -> TrigListItemResponse:
    item = row[0]  # TrigListItem
    return TrigListItemResponse(
        id=item.id,
        list_id=item.list_id,
        trig_id=item.trig_id,
        created_by=item.created_by,
        updated_by=item.updated_by,
        name=item.name,
        description=item.description,
        metadata_=item.metadata_,
        position=item.position,
        created_at=item.created_at,
        updated_at=item.updated_at,
        trig=TrigSummary(
            id=item.trig_id,
            waypoint=row.waypoint,
            name=row.trig_name,
            condition=row.condition,
            osgb_gridref=row.osgb_gridref,
            wgs_lat=str(row.wgs_lat) if row.wgs_lat is not None else None,
            wgs_long=str(row.wgs_long) if row.wgs_long is not None else None,
            wgs_height=float(row.wgs_height) if row.wgs_height is not None else None,
            type_code=row.type_code,
            type_name=row.type_name,
            category_code=row.category_code,
            category_name=row.category_name,
            status_name=row.status_name.strip() if row.status_name else None,
        ),
    )


@router.get("/{list_id}/items", response_model=TrigListItemsPage)
def get_list_items(
    list_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    _require_list_visible(list_id, db, current_user)
    rows, total = trig_list_crud.get_list_items(db, list_id, skip, limit)
    items = [_row_to_item_response(r) for r in rows]
    return TrigListItemsPage(items=items, total=total, has_more=(skip + limit < total))


@router.post("/{list_id}/items", response_model=TrigListItemResponse, status_code=201)
def add_item(
    list_id: int,
    data: TrigListItemCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_list_item_editable(list_id, db, current_user)
    try:
        item = trig_list_crud.add_item(
            db,
            list_id=list_id,
            trig_id=data.trig_id,
            user_id=current_user.id,  # type: ignore[arg-type]
            name=data.name,
            description=data.description,
            metadata=data.metadata,
        )
        db.commit()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return _refetch_item_response(db, list_id, item.id)  # type: ignore[arg-type]


@router.delete("/{list_id}/items/{item_id}", status_code=204)
def remove_item(
    list_id: int,
    item_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_list_item_editable(list_id, db, current_user)
    item = trig_list_crud.get_item(db, item_id)
    if item is None or item.list_id != list_id:
        raise HTTPException(status_code=404, detail="Item not found")
    trig_list_crud.remove_item(db, item)
    db.commit()


@router.patch("/{list_id}/items/{item_id}", response_model=TrigListItemResponse)
def update_item(
    list_id: int,
    item_id: int,
    data: TrigListItemUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_list_item_editable(list_id, db, current_user)
    item = trig_list_crud.get_item(db, item_id)
    if item is None or item.list_id != list_id:
        raise HTTPException(status_code=404, detail="Item not found")

    kwargs: dict = {}
    if data.name is not None:
        kwargs["name"] = data.name
    elif "name" in (data.model_fields_set or set()):
        kwargs["name"] = data.name
    if data.description is not None:
        kwargs["description"] = data.description
    elif "description" in (data.model_fields_set or set()):
        kwargs["description"] = data.description
    if data.metadata is not None:
        kwargs["metadata"] = data.metadata
    if data.position is not None:
        kwargs["position"] = data.position

    item = trig_list_crud.update_item(db, item, user_id=current_user.id, **kwargs)  # type: ignore[arg-type]
    db.commit()
    return _refetch_item_response(db, list_id, item.id)  # type: ignore[arg-type]


@router.post("/{list_id}/items/reorder", status_code=204)
def reorder_items(
    list_id: int,
    data: TrigListItemReorderRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_list_item_editable(list_id, db, current_user)
    trig_list_crud.reorder_items(db, list_id, data.ordering)
    db.commit()


def _refetch_item_response(
    db: Session, list_id: int, item_id: int
) -> TrigListItemResponse:
    """Re-fetch a single item with joined trig data for the response."""
    rows, _ = trig_list_crud.get_list_items(db, list_id, skip=0, limit=1000)
    for r in rows:
        if r[0].id == item_id:
            return _row_to_item_response(r)
    item = trig_list_crud.get_item(db, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Item not found")
    return TrigListItemResponse.model_validate(item)
