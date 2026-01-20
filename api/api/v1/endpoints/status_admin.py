"""
Admin endpoints for managing status records.
"""

import json

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from api.api.deps import get_db, require_admin
from api.api.lifecycle import openapi_lifecycle
from api.core.logging import get_logger
from api.crud import status as status_crud
from api.models.user import User
from api.schemas.status import (
    StatusCreate,
    StatusResponse,
    StatusUpdate,
    StatusUsageResponse,
)
from api.services.cache_invalidator import invalidate_patterns

logger = get_logger(__name__)
router = APIRouter()


# ============================================================================
# Status Admin Endpoints
# ============================================================================


@router.get(
    "/statuses",
    response_model=list[StatusResponse],
    openapi_extra=openapi_lifecycle(
        "beta", note="Get all statuses for admin management."
    ),
)
def get_all_statuses_admin(
    admin_user: User = Depends(require_admin()),
    db: Session = Depends(get_db),
) -> list[StatusResponse]:
    """
    Get all status records for admin editing.

    Returns statuses ordered by ID.
    """
    statuses = status_crud.get_all_statuses(db)
    return [StatusResponse.model_validate(s) for s in statuses]


@router.post(
    "/statuses",
    response_model=StatusResponse,
    status_code=status.HTTP_201_CREATED,
    openapi_extra=openapi_lifecycle("beta", note="Create a new status."),
)
def create_status(
    status_data: StatusCreate,
    admin_user: User = Depends(require_admin()),
    db: Session = Depends(get_db),
) -> StatusResponse:
    """
    Create a new status record.

    The ID must be provided and must be unique.
    """
    logger.info(
        json.dumps(
            {
                "event": "admin_create_status",
                "admin_user_id": int(admin_user.id),
                "status_id": status_data.id,
                "name": status_data.name,
            }
        )
    )

    # Check for existing status with same ID
    existing = status_crud.get_status_by_id(db, status_data.id)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Status with ID {status_data.id} already exists",
        )

    try:
        new_status = status_crud.create_status(
            db,
            status_id=status_data.id,
            name=status_data.name,
            descr=status_data.descr,
            limit_descr=status_data.limit_descr,
        )

        # Invalidate related caches
        invalidate_patterns(["stats:*", "status:*", "trigs:*"])

        return StatusResponse.model_validate(new_status)
    except IntegrityError as e:
        db.rollback()
        logger.error(f"IntegrityError creating status: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to create status. Please check for duplicate values.",
        ) from e


@router.patch(
    "/statuses/{status_id}",
    response_model=StatusResponse,
    openapi_extra=openapi_lifecycle("beta", note="Update an existing status."),
)
def update_status(
    status_id: int,
    status_data: StatusUpdate,
    admin_user: User = Depends(require_admin()),
    db: Session = Depends(get_db),
) -> StatusResponse:
    """
    Update an existing status record.

    Only provided fields will be updated.
    """
    logger.info(
        json.dumps(
            {
                "event": "admin_update_status",
                "admin_user_id": int(admin_user.id),
                "status_id": status_id,
                "updates": status_data.model_dump(exclude_none=True),
            }
        )
    )

    try:
        updated_status = status_crud.update_status(
            db,
            status_id=status_id,
            name=status_data.name,
            descr=status_data.descr,
            limit_descr=status_data.limit_descr,
        )

        if not updated_status:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Status with ID {status_id} not found",
            )

        # Invalidate related caches
        invalidate_patterns(["stats:*", "status:*", "trigs:*"])

        return StatusResponse.model_validate(updated_status)
    except IntegrityError as e:
        db.rollback()
        logger.error(f"IntegrityError updating status: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to update status. Please check for duplicate values.",
        ) from e


@router.delete(
    "/statuses/{status_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    openapi_extra=openapi_lifecycle("beta", note="Delete a status."),
)
def delete_status(
    status_id: int,
    admin_user: User = Depends(require_admin()),
    db: Session = Depends(get_db),
) -> None:
    """
    Delete a status record.

    This will fail if any trigs are using this status.
    """
    logger.info(
        json.dumps(
            {
                "event": "admin_delete_status",
                "admin_user_id": int(admin_user.id),
                "status_id": status_id,
            }
        )
    )

    # Check if status is in use
    usage_count = status_crud.get_status_usage_count(db, status_id)
    if usage_count > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot delete status: it is used by {usage_count} trig(s)",
        )

    try:
        deleted = status_crud.delete_status(db, status_id)
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Status with ID {status_id} not found",
            )

        # Invalidate related caches
        invalidate_patterns(["stats:*", "status:*", "trigs:*"])
    except IntegrityError as e:
        db.rollback()
        logger.error(f"IntegrityError deleting status: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to delete status. It may be in use.",
        ) from e


@router.get(
    "/statuses/{status_id}/usage",
    response_model=StatusUsageResponse,
    openapi_extra=openapi_lifecycle("beta", note="Get usage count for a status."),
)
def get_status_usage(
    status_id: int,
    admin_user: User = Depends(require_admin()),
    db: Session = Depends(get_db),
) -> StatusUsageResponse:
    """
    Get the count of trigs using a specific status.

    Useful for determining if a status can be safely deleted.
    """
    # Verify status exists
    status_obj = status_crud.get_status_by_id(db, status_id)
    if not status_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Status with ID {status_id} not found",
        )

    usage_count = status_crud.get_status_usage_count(db, status_id)
    return StatusUsageResponse(status_id=status_id, usage_count=usage_count)
