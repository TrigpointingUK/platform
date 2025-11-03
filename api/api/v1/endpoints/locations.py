"""
Location search endpoints for finding trigpoints by various means.
"""

from typing import List

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from api.api.deps import get_db
from api.api.lifecycle import lifecycle, openapi_lifecycle
from api.crud import locations as locations_crud
from api.crud import user as user_crud
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
    - UK postcodes (NSPL dataset and legacy postcode6)
    - OSGB grid references
    - Lat/lon coordinate strings
    - User names

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
                id=None,
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
                id=None,
            )
        )

    # Search trigpoints by name or waypoint
    trigs = locations_crud.search_trigpoints_by_name_or_waypoint(
        db, q, limit=min(5, limit)
    )
    for trig in trigs:
        # Skip if missing required fields
        if not trig.name or trig.wgs_lat is None or trig.wgs_long is None:
            continue

        # Build description safely
        parts = []
        if trig.waypoint:
            parts.append(str(trig.waypoint))
        if trig.physical_type:
            parts.append(str(trig.physical_type))
        description = " - ".join(parts) if parts else "Trigpoint"

        results.append(
            LocationSearchResult(
                type="trigpoint",
                name=str(trig.name).strip() or "Unnamed Trig",
                lat=float(trig.wgs_lat),
                lon=float(trig.wgs_long),
                description=description,
                id=str(trig.id),
            )
        )

    # Search towns
    towns = locations_crud.search_towns(db, q, limit=min(5, limit))
    for town in towns:
        # Skip if missing required fields
        if not town.name or town.wgs_lat is None or town.wgs_long is None:
            continue

        results.append(
            LocationSearchResult(
                type="town",
                name=str(town.name).strip().title() or "Unknown Town",
                lat=float(town.wgs_lat),
                lon=float(town.wgs_long),
                description="UK Town",
                id=None,
            )
        )

    # Search postcodes
    pc6_results, postcodes_results = locations_crud.search_postcodes(
        db, q, limit=min(5, limit)
    )

    # For postcode6, use OSGB eastings/northings as wgs_lat is corrupted
    for pc in pc6_results:
        # Skip if missing required fields
        if not pc.code or pc.osgb_eastings is None or pc.osgb_northings is None:
            continue

        lat, lon = locations_crud.osgb_to_wgs84(
            int(pc.osgb_eastings), int(pc.osgb_northings)
        )
        description = str(pc.postal_town).strip() if pc.postal_town else "Postcode"

        results.append(
            LocationSearchResult(
                type="postcode",
                name=str(pc.code).strip(),
                lat=lat,
                lon=lon,
                description=description,
                id=None,
            )
        )

    # For postcodes table (NSPL), use lat/lon directly
    for pc in postcodes_results:
        # Skip if missing required fields
        if not pc.code or pc.lat is None or pc.long is None:
            continue

        results.append(
            LocationSearchResult(
                type="postcode",
                name=str(pc.code).strip(),
                lat=float(pc.lat),
                lon=float(pc.long),
                description="UK Postcode",
                id=None,
            )
        )

    # Search users by name
    users = user_crud.search_users_by_name(db, q, limit=min(5, limit))
    for user in users:
        # Skip if missing required fields
        if not user.name or not user.id:
            continue

        # For users, use a default UK center point since they don't have a location
        # This allows the result to work with the location-based interface
        results.append(
            LocationSearchResult(
                type="user",
                name=str(user.name).strip(),
                lat=54.0,  # UK center
                lon=-2.0,
                description="User",
                id=str(user.id),
            )
        )

    # Return limited results
    return results[:limit]
