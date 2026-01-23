"""
Admin endpoints for managing trig_type and trig_category records.
"""

import json

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from api.api.deps import get_db, require_admin
from api.api.lifecycle import openapi_lifecycle
from api.core.logging import get_logger
from api.crud import trig_type as trig_type_crud
from api.models.user import User
from api.schemas.trig_type import (
    ReorderRequest,
    ReorderTypesRequest,
    TrigCategoryCreate,
    TrigCategoryResponse,
    TrigCategoryUpdate,
    TrigCategoryWithTypes,
    TrigTypeCreate,
    TrigTypeResponse,
    TrigTypeUpdate,
    TrigTypeWithCategory,
)
from api.services.cache_invalidator import invalidate_patterns

logger = get_logger(__name__)
router = APIRouter()


# ============================================================================
# Category Admin Endpoints
# ============================================================================


@router.get(
    "/categories",
    response_model=list[TrigCategoryWithTypes],
    openapi_extra=openapi_lifecycle(
        "beta", note="Get all categories with types for admin management."
    ),
)
def get_all_categories_admin(
    admin_user: User = Depends(require_admin()),
    db: Session = Depends(get_db),
) -> list[TrigCategoryWithTypes]:
    """
    Get all trig categories with their types for admin editing.

    Returns categories with nested types, ordered by sort_order.
    """
    categories = trig_type_crud.get_categories_with_types(db)
    result = []
    for c in categories:
        category_data = TrigCategoryResponse.model_validate(c).model_dump()
        category_data["types"] = [TrigTypeResponse.model_validate(t) for t in c.types]
        result.append(TrigCategoryWithTypes.model_validate(category_data))
    return result


@router.post(
    "/categories",
    response_model=TrigCategoryResponse,
    status_code=status.HTTP_201_CREATED,
    openapi_extra=openapi_lifecycle("beta", note="Create a new trig category."),
)
def create_category(
    category_data: TrigCategoryCreate,
    admin_user: User = Depends(require_admin()),
    db: Session = Depends(get_db),
) -> TrigCategoryResponse:
    """
    Create a new trig category.

    If sort_order is not provided, it will be auto-assigned as the next value.
    """
    logger.info(
        json.dumps(
            {
                "event": "admin_create_category",
                "admin_user_id": int(admin_user.id),
                "code": category_data.code,
                "name": category_data.name,
            }
        )
    )

    # Check for duplicate code
    existing = trig_type_crud.get_category_by_code(db, category_data.code)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Category with code '{category_data.code}' already exists",
        )

    # Auto-assign sort_order if not provided
    sort_order = category_data.sort_order
    if sort_order is None:
        sort_order = trig_type_crud.get_next_category_sort_order(db)

    try:
        category = trig_type_crud.create_category(
            db,
            code=category_data.code,
            name=category_data.name,
            sort_order=sort_order,
            description=category_data.description,
            wiki_url=category_data.wiki_url,
        )
    except IntegrityError as e:
        db.rollback()
        logger.error(f"Failed to create category: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to create category. Code or sort_order may already be in use.",
        )

    # Invalidate type caches
    invalidate_patterns(["trig_type*"])

    return TrigCategoryResponse.model_validate(category)


@router.patch(
    "/categories/{category_id}",
    response_model=TrigCategoryResponse,
    openapi_extra=openapi_lifecycle("beta", note="Update an existing trig category."),
)
def update_category(
    category_id: int,
    update_data: TrigCategoryUpdate,
    admin_user: User = Depends(require_admin()),
    db: Session = Depends(get_db),
) -> TrigCategoryResponse:
    """
    Update an existing trig category.

    Only provided fields will be updated. Pass empty string to clear optional fields.
    """
    logger.info(
        json.dumps(
            {
                "event": "admin_update_category",
                "admin_user_id": int(admin_user.id),
                "category_id": category_id,
            }
        )
    )

    # Check category exists
    existing = trig_type_crud.get_category_by_id(db, category_id)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Category {category_id} not found",
        )

    # Check for duplicate code if changing
    if update_data.code is not None:
        code_check = trig_type_crud.get_category_by_code(db, update_data.code)
        if code_check and int(code_check.id) != category_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Category with code '{update_data.code}' already exists",
            )

    try:
        category = trig_type_crud.update_category(
            db,
            category_id,
            code=update_data.code,
            name=update_data.name,
            description=update_data.description,
            wiki_url=update_data.wiki_url,
            sort_order=update_data.sort_order,
        )
    except IntegrityError as e:
        db.rollback()
        logger.error(f"Failed to update category: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to update category. Code or sort_order may already be in use.",
        )

    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Category {category_id} not found",
        )

    # Invalidate type caches
    invalidate_patterns(["trig_type*"])

    return TrigCategoryResponse.model_validate(category)


@router.delete(
    "/categories/{category_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    openapi_extra=openapi_lifecycle("beta", note="Delete a trig category."),
)
def delete_category(
    category_id: int,
    admin_user: User = Depends(require_admin()),
    db: Session = Depends(get_db),
):
    """
    Delete a trig category.

    Will fail if any types are assigned to this category.
    """
    logger.info(
        json.dumps(
            {
                "event": "admin_delete_category",
                "admin_user_id": int(admin_user.id),
                "category_id": category_id,
            }
        )
    )

    try:
        success = trig_type_crud.delete_category(db, category_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Category {category_id} not found",
        )

    # Invalidate type caches
    invalidate_patterns(["trig_type*"])

    return None


@router.post(
    "/categories/reorder",
    response_model=list[TrigCategoryResponse],
    openapi_extra=openapi_lifecycle("beta", note="Reorder trig categories."),
)
def reorder_categories(
    reorder_data: ReorderRequest,
    admin_user: User = Depends(require_admin()),
    db: Session = Depends(get_db),
) -> list[TrigCategoryResponse]:
    """
    Reorder trig categories.

    Provide a list of category IDs in the desired order.
    Sort order values will be assigned sequentially starting from 1.
    """
    logger.info(
        json.dumps(
            {
                "event": "admin_reorder_categories",
                "admin_user_id": int(admin_user.id),
                "order": reorder_data.order,
            }
        )
    )

    # Verify all IDs exist
    for cat_id in reorder_data.order:
        if not trig_type_crud.get_category_by_id(db, cat_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Category {cat_id} not found",
            )

    try:
        categories = trig_type_crud.reorder_categories(db, reorder_data.order)
    except IntegrityError as e:
        db.rollback()
        logger.error(f"Failed to reorder categories: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to reorder categories",
        )

    # Invalidate type caches
    invalidate_patterns(["trig_type*"])

    return [TrigCategoryResponse.model_validate(c) for c in categories]


# ============================================================================
# Type Admin Endpoints
# ============================================================================


@router.post(
    "/types",
    response_model=TrigTypeWithCategory,
    status_code=status.HTTP_201_CREATED,
    openapi_extra=openapi_lifecycle("beta", note="Create a new trig type."),
)
def create_type(
    type_data: TrigTypeCreate,
    admin_user: User = Depends(require_admin()),
    db: Session = Depends(get_db),
) -> TrigTypeWithCategory:
    """
    Create a new trig type.

    If sort_order is not provided, it will be auto-assigned as the next value
    within the category.
    """
    logger.info(
        json.dumps(
            {
                "event": "admin_create_type",
                "admin_user_id": int(admin_user.id),
                "category_id": type_data.category_id,
                "code": type_data.code,
                "name": type_data.name,
            }
        )
    )

    # Check category exists
    category = trig_type_crud.get_category_by_id(db, type_data.category_id)
    if not category:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Category {type_data.category_id} not found",
        )

    # Check for duplicate code
    existing = trig_type_crud.get_type_by_code(db, type_data.code)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Type with code '{type_data.code}' already exists",
        )

    # Auto-assign sort_order if not provided
    sort_order = type_data.sort_order
    if sort_order is None:
        sort_order = trig_type_crud.get_next_type_sort_order(db, type_data.category_id)

    try:
        trig_type = trig_type_crud.create_type(
            db,
            category_id=type_data.category_id,
            code=type_data.code,
            name=type_data.name,
            sort_order=sort_order,
            description=type_data.description,
            wiki_url=type_data.wiki_url,
            legacy_physical_type=type_data.legacy_physical_type,
        )
    except IntegrityError as e:
        db.rollback()
        logger.error(f"Failed to create type: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to create type. Code or sort_order may already be in use.",
        )

    # Invalidate type caches
    invalidate_patterns(["trig_type*"])

    # Build response with category
    type_response = TrigTypeResponse.model_validate(trig_type).model_dump()
    type_response["category"] = TrigCategoryResponse.model_validate(trig_type.category)
    return TrigTypeWithCategory.model_validate(type_response)


@router.patch(
    "/types/{type_id}",
    response_model=TrigTypeWithCategory,
    openapi_extra=openapi_lifecycle("beta", note="Update an existing trig type."),
)
def update_type(
    type_id: int,
    update_data: TrigTypeUpdate,
    admin_user: User = Depends(require_admin()),
    db: Session = Depends(get_db),
) -> TrigTypeWithCategory:
    """
    Update an existing trig type.

    Only provided fields will be updated. Pass empty string to clear optional fields.
    """
    logger.info(
        json.dumps(
            {
                "event": "admin_update_type",
                "admin_user_id": int(admin_user.id),
                "type_id": type_id,
            }
        )
    )

    # Check type exists
    existing = trig_type_crud.get_type_by_id(db, type_id)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Type {type_id} not found",
        )

    # Check category exists if changing
    if update_data.category_id is not None:
        category = trig_type_crud.get_category_by_id(db, update_data.category_id)
        if not category:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Category {update_data.category_id} not found",
            )

    # Check for duplicate code if changing
    if update_data.code is not None:
        code_check = trig_type_crud.get_type_by_code(db, update_data.code)
        if code_check and int(code_check.id) != type_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Type with code '{update_data.code}' already exists",
            )

    try:
        trig_type = trig_type_crud.update_type(
            db,
            type_id,
            category_id=update_data.category_id,
            code=update_data.code,
            name=update_data.name,
            description=update_data.description,
            wiki_url=update_data.wiki_url,
            sort_order=update_data.sort_order,
            legacy_physical_type=update_data.legacy_physical_type,
        )
    except IntegrityError as e:
        db.rollback()
        logger.error(f"Failed to update type: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to update type. Code or sort_order may already be in use.",
        )

    if not trig_type:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Type {type_id} not found",
        )

    # Invalidate type caches
    invalidate_patterns(["trig_type*"])

    # Build response with category
    type_response = TrigTypeResponse.model_validate(trig_type).model_dump()
    type_response["category"] = TrigCategoryResponse.model_validate(trig_type.category)
    return TrigTypeWithCategory.model_validate(type_response)


@router.delete(
    "/types/{type_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    openapi_extra=openapi_lifecycle("beta", note="Delete a trig type."),
)
def delete_type(
    type_id: int,
    admin_user: User = Depends(require_admin()),
    db: Session = Depends(get_db),
):
    """
    Delete a trig type.

    Warning: This will NOT check if any trigs are using this type. Use with caution.
    """
    logger.info(
        json.dumps(
            {
                "event": "admin_delete_type",
                "admin_user_id": int(admin_user.id),
                "type_id": type_id,
            }
        )
    )

    # Check how many trigs use this type
    usage_count = trig_type_crud.get_type_usage_count(db, type_id)
    if usage_count > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot delete type: {usage_count} trigpoints are using it",
        )

    success = trig_type_crud.delete_type(db, type_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Type {type_id} not found",
        )

    # Invalidate type caches
    invalidate_patterns(["trig_type*"])

    return None


@router.post(
    "/types/reorder",
    response_model=list[TrigTypeResponse],
    openapi_extra=openapi_lifecycle(
        "beta", note="Reorder trig types within a category."
    ),
)
def reorder_types(
    reorder_data: ReorderTypesRequest,
    admin_user: User = Depends(require_admin()),
    db: Session = Depends(get_db),
) -> list[TrigTypeResponse]:
    """
    Reorder trig types within a category.

    Provide a list of type IDs in the desired order.
    Sort order values will be assigned sequentially starting from 1.
    All types must belong to the specified category.
    """
    logger.info(
        json.dumps(
            {
                "event": "admin_reorder_types",
                "admin_user_id": int(admin_user.id),
                "category_id": reorder_data.category_id,
                "order": reorder_data.order,
            }
        )
    )

    # Verify category exists
    category = trig_type_crud.get_category_by_id(db, reorder_data.category_id)
    if not category:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Category {reorder_data.category_id} not found",
        )

    # Verify all type IDs exist and belong to this category
    for type_id in reorder_data.order:
        trig_type = trig_type_crud.get_type_by_id(db, type_id)
        if not trig_type:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Type {type_id} not found",
            )
        if int(trig_type.category_id) != reorder_data.category_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Type {type_id} does not belong to category {reorder_data.category_id}",
            )

    try:
        types = trig_type_crud.reorder_types(
            db, reorder_data.category_id, reorder_data.order
        )
    except IntegrityError as e:
        db.rollback()
        logger.error(f"Failed to reorder types: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to reorder types",
        )

    # Invalidate type caches
    invalidate_patterns(["trig_type*"])

    return [TrigTypeResponse.model_validate(t) for t in types]


@router.get(
    "/types/{type_id}/usage",
    openapi_extra=openapi_lifecycle("beta", note="Get usage count for a trig type."),
)
def get_type_usage(
    type_id: int,
    admin_user: User = Depends(require_admin()),
    db: Session = Depends(get_db),
):
    """
    Get the number of trigpoints using this type.

    Useful before attempting to delete a type.
    """
    trig_type = trig_type_crud.get_type_by_id(db, type_id)
    if not trig_type:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Type {type_id} not found",
        )

    usage_count = trig_type_crud.get_type_usage_count(db, type_id)

    return {
        "type_id": type_id,
        "type_code": trig_type.code,
        "type_name": trig_type.name,
        "usage_count": usage_count,
    }
