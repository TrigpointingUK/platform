"""
Admin endpoints for managing the historic use and recent use lookups.

Both lookups share these routes, selected by `kind` ("historic" or
"current"). Recent use is stored in trig.current_use.
"""

import json
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from api.api.deps import get_db, require_admin
from api.api.lifecycle import openapi_lifecycle
from api.core.logging import get_logger
from api.crud import trig_use as trig_use_crud
from api.crud.trig_use import CONFIG, TrigUseKind
from api.models.user import User
from api.schemas.trig_use import (
    TrigUseCreate,
    TrigUseResponse,
    TrigUseUpdate,
    TrigUseUsageResponse,
)
from api.services.cache_invalidator import invalidate_patterns

logger = get_logger(__name__)
router = APIRouter()

# Trig pages, lists, exports and user stats embed the value, so a rename
# clears them too
_RENAME_CACHE_PATTERNS = ["trig:*", "trigs:*", "user:*"]


def _check_name(
    db: Session, kind: TrigUseKind, name: str, exclude_id: Optional[int] = None
) -> str:
    """Strip and validate a name: not blank, fits the trig column, unique."""
    config = CONFIG[kind]
    name = name.strip()
    if not name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Name cannot be blank"
        )
    if len(name) > config.max_length:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{config.label} names are limited to {config.max_length} characters",
        )
    existing = trig_use_crud.get_by_name(db, kind, name)
    if existing and int(existing.id) != exclude_id:  # type: ignore[arg-type]
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f'{config.label} "{name}" already exists',
        )
    return name


def _not_found(kind: TrigUseKind, use_id: int) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"{CONFIG[kind].label} with ID {use_id} not found",
    )


@router.get(
    "/{kind}",
    response_model=list[TrigUseResponse],
    openapi_extra=openapi_lifecycle(
        "beta", note="Get all historic or recent use values for admin management."
    ),
)
def get_all_trig_uses_admin(
    kind: TrigUseKind,
    admin_user: User = Depends(require_admin()),
    db: Session = Depends(get_db),
) -> list[TrigUseResponse]:
    """Get all values of a kind, in display order."""
    return [TrigUseResponse.model_validate(v) for v in trig_use_crud.get_all(db, kind)]


@router.post(
    "/{kind}",
    response_model=TrigUseResponse,
    status_code=status.HTTP_201_CREATED,
    openapi_extra=openapi_lifecycle(
        "beta", note="Create a new historic or recent use value."
    ),
)
def create_trig_use(
    kind: TrigUseKind,
    data: TrigUseCreate,
    admin_user: User = Depends(require_admin()),
    db: Session = Depends(get_db),
) -> TrigUseResponse:
    """Create a new value. Names must be unique within the kind."""
    logger.info(
        json.dumps(
            {
                "event": "admin_create_trig_use",
                "admin_user_id": int(admin_user.id),
                "kind": kind.value,
                "name": data.name,
            }
        )
    )

    name = _check_name(db, kind, data.name)
    try:
        value = trig_use_crud.create(
            db,
            kind,
            name=name,
            description=data.description,
            sort_order=data.sort_order,
        )
    except IntegrityError as e:
        db.rollback()
        logger.error(f"IntegrityError creating {kind.value} use: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to create value. Please check for duplicate values.",
        ) from e

    invalidate_patterns([CONFIG[kind].cache_pattern])
    return TrigUseResponse.model_validate(value)


@router.patch(
    "/{kind}/{use_id}",
    response_model=TrigUseResponse,
    openapi_extra=openapi_lifecycle(
        "beta", note="Update a historic or recent use value."
    ),
)
def update_trig_use(
    kind: TrigUseKind,
    use_id: int,
    data: TrigUseUpdate,
    admin_user: User = Depends(require_admin()),
    db: Session = Depends(get_db),
) -> TrigUseResponse:
    """
    Update a value. Only provided fields are changed; a new name is applied
    to every trig with the old one.
    """
    if not trig_use_crud.get_by_id(db, kind, use_id):
        raise _not_found(kind, use_id)
    name = (
        _check_name(db, kind, data.name, exclude_id=use_id)
        if data.name is not None
        else None
    )

    try:
        value, renamed = trig_use_crud.update(
            db,
            kind,
            use_id,
            name=name,
            description=data.description,
            sort_order=data.sort_order,
        )
    except IntegrityError as e:
        db.rollback()
        logger.error(f"IntegrityError updating {kind.value} use: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to update value. Please check for duplicate values.",
        ) from e
    if value is None:
        raise _not_found(kind, use_id)

    logger.info(
        json.dumps(
            {
                "event": "admin_update_trig_use",
                "admin_user_id": int(admin_user.id),
                "kind": kind.value,
                "use_id": use_id,
                "updates": data.model_dump(exclude_none=True),
                "trigs_renamed": renamed,
            }
        )
    )

    patterns = [CONFIG[kind].cache_pattern]
    if renamed:
        patterns += _RENAME_CACHE_PATTERNS
    invalidate_patterns(patterns)
    return TrigUseResponse.model_validate(value)


@router.delete(
    "/{kind}/{use_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    openapi_extra=openapi_lifecycle(
        "beta", note="Delete a historic or recent use value."
    ),
)
def delete_trig_use(
    kind: TrigUseKind,
    use_id: int,
    admin_user: User = Depends(require_admin()),
    db: Session = Depends(get_db),
) -> None:
    """Delete a value. Fails if any trigs use it."""
    logger.info(
        json.dumps(
            {
                "event": "admin_delete_trig_use",
                "admin_user_id": int(admin_user.id),
                "kind": kind.value,
                "use_id": use_id,
            }
        )
    )

    value = trig_use_crud.get_by_id(db, kind, use_id)
    if not value:
        raise _not_found(kind, use_id)

    usage_count = trig_use_crud.get_usage_count(db, kind, str(value.name))
    if usage_count > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot delete: it is used by {usage_count} trig(s)",
        )

    trig_use_crud.delete(db, kind, use_id)
    invalidate_patterns([CONFIG[kind].cache_pattern])


@router.get(
    "/{kind}/{use_id}/usage",
    response_model=TrigUseUsageResponse,
    openapi_extra=openapi_lifecycle(
        "beta", note="Get the number of trigs using a historic or recent use value."
    ),
)
def get_trig_use_usage(
    kind: TrigUseKind,
    use_id: int,
    admin_user: User = Depends(require_admin()),
    db: Session = Depends(get_db),
) -> TrigUseUsageResponse:
    """Number of trigs using a value - it can only be deleted at zero."""
    value = trig_use_crud.get_by_id(db, kind, use_id)
    if not value:
        raise _not_found(kind, use_id)
    return TrigUseUsageResponse(
        id=use_id,
        usage_count=trig_use_crud.get_usage_count(db, kind, str(value.name)),
    )
