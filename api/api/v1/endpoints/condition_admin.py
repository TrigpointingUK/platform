"""
Admin endpoints for managing condition records.
"""

import json

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from api.api.deps import get_db, require_admin
from api.api.lifecycle import openapi_lifecycle
from api.core.logging import get_logger
from api.crud import condition as condition_crud
from api.models.user import User
from api.schemas.condition import (
    ConditionCreate,
    ConditionResponse,
    ConditionUpdate,
    ConditionUsageResponse,
)
from api.services.cache_invalidator import invalidate_patterns

logger = get_logger(__name__)
router = APIRouter()


# ============================================================================
# Condition Admin Endpoints
# ============================================================================


@router.get(
    "/conditions",
    response_model=list[ConditionResponse],
    openapi_extra=openapi_lifecycle(
        "beta", note="Get all conditions for admin management."
    ),
)
def get_all_conditions_admin(
    admin_user: User = Depends(require_admin()),
    db: Session = Depends(get_db),
) -> list[ConditionResponse]:
    """
    Get all condition records for admin editing.

    Returns conditions ordered by sort_order.
    """
    conditions = condition_crud.get_all_conditions(db)
    return [ConditionResponse.model_validate(c) for c in conditions]


@router.post(
    "/conditions",
    response_model=ConditionResponse,
    status_code=status.HTTP_201_CREATED,
    openapi_extra=openapi_lifecycle("beta", note="Create a new condition."),
)
def create_condition(
    condition_data: ConditionCreate,
    admin_user: User = Depends(require_admin()),
    db: Session = Depends(get_db),
) -> ConditionResponse:
    """
    Create a new condition record.

    The code must be a single uppercase letter and must be unique.
    """
    logger.info(
        json.dumps(
            {
                "event": "admin_create_condition",
                "admin_user_id": int(admin_user.id),
                "condition_code": condition_data.code,
                "name": condition_data.name,
            }
        )
    )

    # Check for existing condition with same code
    existing = condition_crud.get_condition_by_code(db, condition_data.code.upper())
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Condition with code '{condition_data.code.upper()}' already exists",
        )

    try:
        new_condition = condition_crud.create_condition(
            db,
            code=condition_data.code,
            name=condition_data.name,
            sort_order=condition_data.sort_order,
            description=condition_data.description,
            icon_file=condition_data.icon_file,
            trig_colour=condition_data.trig_colour,
            log_colour=condition_data.log_colour,
            similar_codes=condition_data.similar_codes,
            wiki_url=condition_data.wiki_url,
        )

        # Invalidate related caches
        invalidate_patterns(["condition:*", "logs:*"])

        return ConditionResponse.model_validate(new_condition)
    except IntegrityError as e:
        db.rollback()
        logger.error(f"IntegrityError creating condition: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to create condition. Please check for duplicate values.",
        ) from e


@router.patch(
    "/conditions/{code}",
    response_model=ConditionResponse,
    openapi_extra=openapi_lifecycle("beta", note="Update an existing condition."),
)
def update_condition(
    code: str,
    condition_data: ConditionUpdate,
    admin_user: User = Depends(require_admin()),
    db: Session = Depends(get_db),
) -> ConditionResponse:
    """
    Update an existing condition record.

    Only provided fields will be updated. The code cannot be changed.
    """
    logger.info(
        json.dumps(
            {
                "event": "admin_update_condition",
                "admin_user_id": int(admin_user.id),
                "condition_code": code,
                "updates": condition_data.model_dump(exclude_none=True),
            }
        )
    )

    try:
        updated_condition = condition_crud.update_condition(
            db,
            code=code.upper(),
            name=condition_data.name,
            description=condition_data.description,
            icon_file=condition_data.icon_file,
            trig_colour=condition_data.trig_colour,
            log_colour=condition_data.log_colour,
            similar_codes=condition_data.similar_codes,
            wiki_url=condition_data.wiki_url,
            sort_order=condition_data.sort_order,
        )

        if not updated_condition:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Condition with code '{code.upper()}' not found",
            )

        # Invalidate related caches
        invalidate_patterns(["condition:*", "logs:*"])

        return ConditionResponse.model_validate(updated_condition)
    except IntegrityError as e:
        db.rollback()
        logger.error(f"IntegrityError updating condition: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to update condition. Please check for duplicate values.",
        ) from e


@router.delete(
    "/conditions/{code}",
    status_code=status.HTTP_204_NO_CONTENT,
    openapi_extra=openapi_lifecycle("beta", note="Delete a condition."),
)
def delete_condition(
    code: str,
    admin_user: User = Depends(require_admin()),
    db: Session = Depends(get_db),
) -> None:
    """
    Delete a condition record.

    This will fail if any logs are using this condition.
    """
    logger.info(
        json.dumps(
            {
                "event": "admin_delete_condition",
                "admin_user_id": int(admin_user.id),
                "condition_code": code,
            }
        )
    )

    # Check if condition is in use
    usage_count = condition_crud.get_condition_usage_count(db, code.upper())
    if usage_count > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot delete condition: it is used by {usage_count} log(s)",
        )

    try:
        deleted = condition_crud.delete_condition(db, code.upper())
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Condition with code '{code.upper()}' not found",
            )

        # Invalidate related caches
        invalidate_patterns(["condition:*", "logs:*"])
    except IntegrityError as e:
        db.rollback()
        logger.error(f"IntegrityError deleting condition: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to delete condition. It may be in use.",
        ) from e


@router.get(
    "/conditions/{code}/usage",
    response_model=ConditionUsageResponse,
    openapi_extra=openapi_lifecycle("beta", note="Get usage count for a condition."),
)
def get_condition_usage(
    code: str,
    admin_user: User = Depends(require_admin()),
    db: Session = Depends(get_db),
) -> ConditionUsageResponse:
    """
    Get the count of logs using a specific condition.

    Useful for determining if a condition can be safely deleted.
    """
    # Verify condition exists
    condition_obj = condition_crud.get_condition_by_code(db, code.upper())
    if not condition_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Condition with code '{code.upper()}' not found",
        )

    usage_count = condition_crud.get_condition_usage_count(db, code.upper())
    return ConditionUsageResponse(code=code.upper(), usage_count=usage_count)
