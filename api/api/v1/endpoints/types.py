"""
Trig type endpoints for type and group queries.
"""

from typing import cast

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from api.api.deps import get_db
from api.api.lifecycle import lifecycle, openapi_lifecycle
from api.crud import trig_type as trig_type_crud
from api.schemas.trig_type import (
    TrigTypeGroupResponse,
    TrigTypeGroupWithTypes,
    TrigTypeResponse,
    TrigTypeWithGroup,
)
from api.utils.cache_decorator import cached

router = APIRouter()


@router.get(
    "/groups",
    response_model=list[TrigTypeGroupWithTypes],
    openapi_extra=openapi_lifecycle(
        "beta", note="List all trig type groups with types"
    ),
)
@cached(
    resource_type="trig_type_groups", ttl=86400
)  # 24 hours - types don't change often
def list_type_groups(
    _lc=lifecycle("beta"),
    db: Session = Depends(get_db),
):
    """
    List all trig type groups with their nested types.

    Groups are ordered by sort_order (used for threshold-based filtering).
    Types within each group are also ordered by their sort_order.

    This endpoint is useful for building filter UIs where users can
    select which types/groups of trigpoints to display.
    """
    groups = trig_type_crud.get_groups_with_types(db)

    result = []
    for g in groups:
        group_data = TrigTypeGroupResponse.model_validate(g).model_dump()
        group_data["types"] = [
            TrigTypeResponse.model_validate(t)
            for t in sorted(g.types, key=lambda x: x.sort_order)
        ]
        result.append(TrigTypeGroupWithTypes.model_validate(group_data))
    return result


@router.get(
    "/groups/{code}",
    response_model=TrigTypeGroupWithTypes,
    openapi_extra=openapi_lifecycle("beta", note="Get a specific type group by code"),
)
@cached(resource_type="trig_type_group", ttl=86400)
def get_type_group(
    code: str,
    _lc=lifecycle("beta"),
    db: Session = Depends(get_db),
):
    """
    Get a specific trig type group by its code.

    The code is case-insensitive (e.g., "pillar", "PILLAR", "Pillar" all work).
    """
    group = trig_type_crud.get_group_by_code(db, code)
    if not group:
        raise HTTPException(status_code=404, detail=f"Type group '{code}' not found")

    types = trig_type_crud.get_types_by_group_id(db, cast(int, group.id))

    group_data = TrigTypeGroupResponse.model_validate(group).model_dump()
    group_data["types"] = [TrigTypeResponse.model_validate(t) for t in types]
    return TrigTypeGroupWithTypes.model_validate(group_data)


@router.get(
    "",
    response_model=list[TrigTypeWithGroup],
    openapi_extra=openapi_lifecycle("beta", note="List all trig types"),
)
@cached(resource_type="trig_types", ttl=86400)
def list_types(
    group: str | None = Query(
        None, description="Filter by group code (case-insensitive)"
    ),
    _lc=lifecycle("beta"),
    db: Session = Depends(get_db),
):
    """
    List all trig types with their parent group information.

    Optionally filter by group code. Types are ordered by group sort_order,
    then by type sort_order within each group.
    """
    if group:
        group_obj = trig_type_crud.get_group_by_code(db, group)
        if not group_obj:
            raise HTTPException(
                status_code=404, detail=f"Type group '{group}' not found"
            )
        types = trig_type_crud.get_types_by_group_id(db, cast(int, group_obj.id))
    else:
        types = trig_type_crud.get_all_types(db)

    result = []
    for t in types:
        type_data = TrigTypeResponse.model_validate(t).model_dump()
        type_data["group"] = TrigTypeGroupResponse.model_validate(t.group)
        result.append(TrigTypeWithGroup.model_validate(type_data))
    return result


@router.get(
    "/{code}",
    response_model=TrigTypeWithGroup,
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
    type_data["group"] = TrigTypeGroupResponse.model_validate(trig_type.group)
    return TrigTypeWithGroup.model_validate(type_data)
