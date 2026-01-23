"""
Trig type endpoints for type and category queries.
"""

from typing import cast

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from api.api.deps import get_db
from api.api.lifecycle import lifecycle, openapi_lifecycle
from api.crud import trig_type as trig_type_crud
from api.schemas.trig_type import (
    TrigCategoryResponse,
    TrigCategoryWithTypes,
    TrigTypeResponse,
    TrigTypeWithCategory,
)
from api.utils.cache_decorator import cached

router = APIRouter()


@router.get(
    "/categories",
    response_model=list[TrigCategoryWithTypes],
    openapi_extra=openapi_lifecycle(
        "beta", note="List all trig type categories with types"
    ),
)
@cached(
    resource_type="trig_type_categories", ttl=86400
)  # 24 hours - types don't change often
def list_type_categories(
    _lc=lifecycle("beta"),
    db: Session = Depends(get_db),
):
    """
    List all trig type categories with their nested types.

    Categories are ordered by sort_order (used for threshold-based filtering).
    Types within each category are also ordered by their sort_order.

    This endpoint is useful for building filter UIs where users can
    select which types/categories of trigpoints to display.
    """
    categories = trig_type_crud.get_categories_with_types(db)

    result = []
    for c in categories:
        category_data = TrigCategoryResponse.model_validate(c).model_dump()
        category_data["types"] = [
            TrigTypeResponse.model_validate(t)
            for t in sorted(c.types, key=lambda x: x.sort_order)
        ]
        result.append(TrigCategoryWithTypes.model_validate(category_data))
    return result


@router.get(
    "/categories/{code}",
    response_model=TrigCategoryWithTypes,
    openapi_extra=openapi_lifecycle(
        "beta", note="Get a specific type category by code"
    ),
)
@cached(resource_type="trig_type_category", ttl=86400)
def get_type_category(
    code: str,
    _lc=lifecycle("beta"),
    db: Session = Depends(get_db),
):
    """
    Get a specific trig type category by its code.

    The code is case-insensitive (e.g., "pillar", "PILLAR", "Pillar" all work).
    """
    category = trig_type_crud.get_category_by_code(db, code)
    if not category:
        raise HTTPException(status_code=404, detail=f"Type category '{code}' not found")

    types = trig_type_crud.get_types_by_category_id(db, cast(int, category.id))

    category_data = TrigCategoryResponse.model_validate(category).model_dump()
    category_data["types"] = [TrigTypeResponse.model_validate(t) for t in types]
    return TrigCategoryWithTypes.model_validate(category_data)


@router.get(
    "",
    response_model=list[TrigTypeWithCategory],
    openapi_extra=openapi_lifecycle("beta", note="List all trig types"),
)
@cached(resource_type="trig_types", ttl=86400)
def list_types(
    category: str | None = Query(
        None, description="Filter by category code (case-insensitive)"
    ),
    _lc=lifecycle("beta"),
    db: Session = Depends(get_db),
):
    """
    List all trig types with their parent category information.

    Optionally filter by category code. Types are ordered by category sort_order,
    then by type sort_order within each category.
    """
    if category:
        category_obj = trig_type_crud.get_category_by_code(db, category)
        if not category_obj:
            raise HTTPException(
                status_code=404, detail=f"Type category '{category}' not found"
            )
        types = trig_type_crud.get_types_by_category_id(db, cast(int, category_obj.id))
    else:
        types = trig_type_crud.get_all_types(db)

    result = []
    for t in types:
        type_data = TrigTypeResponse.model_validate(t).model_dump()
        type_data["category"] = TrigCategoryResponse.model_validate(t.category)
        result.append(TrigTypeWithCategory.model_validate(type_data))
    return result


@router.get(
    "/{code}",
    response_model=TrigTypeWithCategory,
    openapi_extra=openapi_lifecycle("beta", note="Get a specific type by code"),
)
@cached(resource_type="trig_type", ttl=86400)
def get_type(
    code: str,
    _lc=lifecycle("beta"),
    db: Session = Depends(get_db),
):
    """
    Get a specific trig type by its code.

    The code is case-insensitive (e.g., "hotine", "HOTINE", "Hotine" all work).
    """
    trig_type = trig_type_crud.get_type_by_code(db, code)
    if not trig_type:
        raise HTTPException(status_code=404, detail=f"Type '{code}' not found")

    type_data = TrigTypeResponse.model_validate(trig_type).model_dump()
    type_data["category"] = TrigCategoryResponse.model_validate(trig_type.category)
    return TrigTypeWithCategory.model_validate(type_data)
