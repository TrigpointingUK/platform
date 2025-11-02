"""
Location search endpoints for finding trigpoints by various means.
"""

from typing import List

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from api.api.deps import get_db
from api.api.lifecycle import lifecycle, openapi_lifecycle
from api.crud import locations as locations_crud
from api.schemas.locations import LocationSearchResult
from api.utils.cache_decorator import cached

router = APIRouter()


@router.get(
    "/search",
    response_model=List[LocationSearchResult],
    openapi_extra=openapi_lifecycle(
        "beta", note="Unified location search across multiple sources"
    ),
)
@cached(resource_type="location_search", ttl=86400)  # 24 hours
def search_locations(
    q: str = Query(..., description="Search query", min_length=2),
    limit: int = Query(10, ge=1, le=50, description="Maximum results to return"),
    _lc=lifecycle("beta"),
    db: Session = Depends(get_db),
):
    """
    Search for locations across multiple sources.

    Searches:
    - Trigpoint names and waypoints
    - Town names
    - UK postcodes (6 and 8 character)
    - OSGB grid references
    - Lat/lon coordinate strings

    Returns results sorted by relevance/type priority.
    """
    results: List[LocationSearchResult] = []

    # Try to parse as lat/lon first
    latlon = locations_crud.parse_latlon_string(q)
    if latlon:
        lat, lon = latlon
        results.append(
            LocationSearchResult(
                type="latlon",
                name=f"{lat:.5f}, {lon:.5f}",
                lat=lat,
                lon=lon,
                description="Coordinates (WGS84)",
            )
        )

    # Try to parse as OSGB grid reference
    gridref_result = locations_crud.parse_grid_reference(q)
    if gridref_result:
        lat, lon, normalized = gridref_result
        results.append(
            LocationSearchResult(
                type="gridref",
                name=normalized,
                lat=lat,
                lon=lon,
                description="OSGB Grid Reference",
            )
        )

    # Search trigpoints by name or waypoint
    trigs = locations_crud.search_trigpoints_by_name_or_waypoint(
        db, q, limit=min(5, limit)
    )
    for trig in trigs:
        results.append(
            LocationSearchResult(
                type="trigpoint",
                name=str(trig.name),
                lat=float(trig.wgs_lat),
                lon=float(trig.wgs_long),
                description=f"{trig.waypoint} - {trig.physical_type}",
            )
        )

    # Search towns
    towns = locations_crud.search_towns(db, q, limit=min(5, limit))
    for town in towns:
        results.append(
            LocationSearchResult(
                type="town",
                name=str(town.name).title(),
                lat=float(town.wgs_lat),
                lon=float(town.wgs_long),
                description=f"{town.county}",
            )
        )

    # Search postcodes
    pc6_results, pc8_results = locations_crud.search_postcodes(
        db, q, limit=min(5, limit)
    )

    for pc in pc6_results:
        results.append(
            LocationSearchResult(
                type="postcode",
                name=str(pc.code),
                lat=float(pc.wgs_lat),
                lon=float(pc.wgs_long),
                description=f"{pc.postal_town}",
            )
        )

    # For 8-char postcodes, we need to get lat/lon from the 6-char area
    # or calculate from eastings/northings
    for pc in pc8_results:
        # Use OSGB conversion
        lat, lon = locations_crud.osgb_to_wgs84(
            int(pc.osgb_eastings), int(pc.osgb_northings)
        )
        results.append(
            LocationSearchResult(
                type="postcode",
                name=str(pc.code),
                lat=lat,
                lon=lon,
                description="UK Postcode",
            )
        )

    # Return limited results
    return results[:limit]
