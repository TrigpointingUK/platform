"""
Area endpoints for geographic area queries.
"""

from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from api.api.deps import get_db
from api.api.lifecycle import lifecycle, openapi_lifecycle
from api.crud import area as area_crud
from api.schemas.area import (
    AreaGroupResponse,
    AreaResponse,
    AreasContainingResponse,
    AreaTypeResponse,
)
from api.utils.cache_decorator import cached

router = APIRouter()


@router.get(
    "/containing",
    response_model=AreasContainingResponse,
    openapi_extra=openapi_lifecycle(
        "beta", note="Find areas containing a geographic point"
    ),
)
@cached(
    resource_type="areas_containing", ttl=86400
)  # 24 hours - areas don't change often
def get_areas_containing_point(
    lat: float = Query(..., description="Latitude (WGS84)", ge=-90, le=90),
    lon: float = Query(..., description="Longitude (WGS84)", ge=-180, le=180),
    _lc=lifecycle("beta"),
    db: Session = Depends(get_db),
):
    """
    Find all areas that contain the given geographic point.

    Returns areas grouped by area type (e.g., Historic Counties, OS Landranger Maps).
    Uses PostGIS ST_Covers for efficient spatial containment queries.

    This is useful for filtering trigpoints by area - first get the areas
    containing a location, then use the area_id to filter trigpoints.
    """
    # Get all areas containing this point
    areas = area_crud.get_areas_containing_point(db, lat=lat, lon=lon)

    # Group areas by area_type
    groups_dict: dict[int, list] = defaultdict(list)
    area_types: dict[int, AreaTypeResponse] = {}

    for area in areas:
        area_type = area.area_type
        type_id = int(area_type.id)
        if type_id not in area_types:
            area_types[type_id] = AreaTypeResponse(
                id=type_id,
                code=str(area_type.code),
                name=str(area_type.name),
            )

        groups_dict[type_id].append(
            AreaResponse(
                id=int(area.id),
                name=str(area.name),
                code=str(area.code) if area.code else None,
                area_type=area_types[type_id],
            )
        )

    # Build grouped response
    groups = [
        AreaGroupResponse(
            area_type=area_types[type_id],
            areas=area_list,
        )
        for type_id, area_list in groups_dict.items()
    ]

    # Sort groups by area type name
    groups.sort(key=lambda g: g.area_type.name)

    return AreasContainingResponse(
        lat=lat,
        lon=lon,
        groups=groups,
        total_areas=len(areas),
    )


@router.get(
    "/types",
    response_model=list[AreaTypeResponse],
    openapi_extra=openapi_lifecycle("beta", note="List all area types"),
)
@cached(resource_type="area_types", ttl=86400)  # 24 hours
def list_area_types(
    _lc=lifecycle("beta"),
    db: Session = Depends(get_db),
):
    """
    List all available area types.

    Returns area types ordered by name.
    """
    types = area_crud.list_area_types(db)
    return [
        AreaTypeResponse(id=int(t.id), code=str(t.code), name=str(t.name))
        for t in types
    ]


@router.get(
    "/{area_id}",
    response_model=AreaResponse,
    openapi_extra=openapi_lifecycle("beta", note="Get area by ID"),
)
@cached(resource_type="area", ttl=86400, resource_id_param="area_id")
def get_area(
    area_id: int,
    _lc=lifecycle("beta"),
    db: Session = Depends(get_db),
):
    """
    Get an area by ID.

    Returns the area with its type information.
    """
    area = area_crud.get_area_by_id(db, area_id=area_id)
    if area is None:
        raise HTTPException(status_code=404, detail="Area not found")

    return AreaResponse(
        id=int(area.id),
        name=str(area.name),
        code=str(area.code) if area.code else None,
        area_type=AreaTypeResponse(
            id=int(area.area_type.id),
            code=str(area.area_type.code),
            name=str(area.area_type.name),
        ),
    )
