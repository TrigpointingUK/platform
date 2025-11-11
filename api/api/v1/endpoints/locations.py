"""
Location search endpoints for finding trigpoints by various means.
"""

from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.exc import DatabaseError
from sqlalchemy.orm import Session

from api.api.deps import get_db
from api.api.lifecycle import lifecycle, openapi_lifecycle
from api.crud import locations as locations_crud
from api.crud import tlog as tlog_crud
from api.crud import trig as trig_crud
from api.crud import user as user_crud
from api.models.user import User
from api.schemas.locations import (
    LocationSearchResult,
    LogSearchResult,
    SearchCategoryResults,
    UnifiedSearchResults,
)
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


@router.get(
    "/search/all",
    response_model=UnifiedSearchResults,
    openapi_extra=openapi_lifecycle(
        "beta", note="Unified search across all categories"
    ),
)
@cached(resource_type="unified_search", ttl=3600)  # 1 hour
def search_all(
    q: str = Query(..., description="Search query", min_length=2),
    limit: int = Query(20, ge=1, le=100, description="Maximum results per category"),
    _lc=lifecycle("beta"),
    db: Session = Depends(get_db),
):
    """
    Unified search across all categories.

    Returns comprehensive results from:
    - Trigpoints (by name/waypoint)
    - Places (towns)
    - Users
    - Postcodes
    - Coordinates (latlon/gridref)
    - Log text (substring)
    - Log text (regex) - only if query looks like a regex pattern
    """

    # Helper function to create truncated excerpt
    def create_excerpt(text: str, max_length: int = 150) -> str:
        if len(text) <= max_length:
            return text
        return text[:max_length] + "..."

    # Coordinate searches
    coordinates_items: List[LocationSearchResult] = []
    latlon = locations_crud.parse_latlon_string(q)
    if latlon:
        lat, lon = latlon
        coordinates_items.append(
            LocationSearchResult(
                type="latlon",
                name=f"{lat:.5f}, {lon:.5f}",
                lat=lat,
                lon=lon,
                description="Coordinates (WGS84)",
                id=None,
            )
        )

    gridref_result = locations_crud.parse_grid_reference(q)
    if gridref_result:
        lat, lon, normalized = gridref_result
        coordinates_items.append(
            LocationSearchResult(
                type="gridref",
                name=normalized,
                lat=lat,
                lon=lon,
                description="OSGB Grid Reference",
                id=None,
            )
        )

    # Trigpoints
    trigs = locations_crud.search_trigpoints_by_name_or_waypoint(db, q, limit=limit)
    trig_total = trig_crud.count_trigs_filtered(db, name=q)
    trigpoint_items: List[LocationSearchResult] = []
    for trig in trigs:
        if not trig.name or trig.wgs_lat is None or trig.wgs_long is None:
            continue
        parts = []
        if trig.waypoint:
            parts.append(str(trig.waypoint))
        if trig.physical_type:
            parts.append(str(trig.physical_type))
        description = " - ".join(parts) if parts else "Trigpoint"
        trigpoint_items.append(
            LocationSearchResult(
                type="trigpoint",
                name=str(trig.name).strip() or "Unnamed Trig",
                lat=float(trig.wgs_lat),
                lon=float(trig.wgs_long),
                description=description,
                id=str(trig.id),
            )
        )

    # Places (Towns)
    towns = locations_crud.search_towns(db, q, limit=limit)
    town_total = db.query(User).filter(User.name.ilike(f"%{q}%")).count()  # Rough count
    place_items: List[LocationSearchResult] = []
    for town in towns:
        if not town.name or town.wgs_lat is None or town.wgs_long is None:
            continue
        place_items.append(
            LocationSearchResult(
                type="town",
                name=str(town.name).strip().title() or "Unknown Town",
                lat=float(town.wgs_lat),
                lon=float(town.wgs_long),
                description="UK Town",
                id=None,
            )
        )

    # Users
    users = user_crud.search_users_by_name(db, q, limit=limit)
    user_total = db.query(User).filter(User.name.ilike(f"%{q}%")).count()
    user_items: List[LocationSearchResult] = []
    for user in users:
        if not user.name or not user.id:
            continue
        user_items.append(
            LocationSearchResult(
                type="user",
                name=str(user.name).strip(),
                lat=54.0,  # UK center
                lon=-2.0,
                description="User",
                id=str(user.id),
            )
        )

    # Postcodes
    pc6_results, postcodes_results = locations_crud.search_postcodes(
        db, q, skip=0, limit=limit
    )
    postcode_items: List[LocationSearchResult] = []
    for pc in pc6_results:
        if not pc.code or pc.osgb_eastings is None or pc.osgb_northings is None:
            continue
        lat, lon = locations_crud.osgb_to_wgs84(
            int(pc.osgb_eastings), int(pc.osgb_northings)
        )
        description = str(pc.postal_town).strip() if pc.postal_town else "Postcode"
        postcode_items.append(
            LocationSearchResult(
                type="postcode",
                name=str(pc.code).strip(),
                lat=lat,
                lon=lon,
                description=description,
                id=None,
            )
        )
    for pc in postcodes_results:
        if not pc.code or pc.lat is None or pc.long is None:
            continue
        postcode_items.append(
            LocationSearchResult(
                type="postcode",
                name=str(pc.code).strip(),
                lat=float(pc.lat),
                lon=float(pc.long),
                description="UK Postcode",
                id=None,
            )
        )
    # Get total counts for both tables
    from api.models.location import Postcode, Postcode6

    query_upper = q.upper().strip()
    query_no_space = query_upper.replace(" ", "")
    query_normalized = " ".join(query_upper.split())
    pc6_total = (
        db.query(Postcode6).filter(Postcode6.code.like(f"{query_no_space}%")).count()
    )
    postcodes_total = (
        db.query(Postcode).filter(Postcode.code.like(f"{query_normalized}%")).count()
    )
    postcode_total = pc6_total + postcodes_total

    # Log substring search
    log_substring_items: List[LogSearchResult] = []
    try:
        logs_text = tlog_crud.search_logs_by_text_with_names(db, q, limit=limit)
        log_substring_total = tlog_crud.count_logs_by_text(db, q)
        for log, trig_name, user_name in logs_text:
            log_substring_items.append(
                LogSearchResult(
                    id=log.id,  # type: ignore[arg-type]
                    trig_id=log.trig_id,  # type: ignore[arg-type]
                    trig_name=trig_name,
                    user_id=log.user_id,  # type: ignore[arg-type]
                    user_name=user_name,
                    date=log.date,  # type: ignore[arg-type]
                    time=log.time,  # type: ignore[arg-type]
                    comment=log.comment,  # type: ignore[arg-type]
                    comment_excerpt=create_excerpt(log.comment),  # type: ignore[arg-type]
                )
            )
    except Exception:
        log_substring_total = 0

    # Log regex search - only attempt if query could be a regex
    log_regex_items: List[LogSearchResult] = []
    log_regex_total = 0
    # Check if query contains regex special chars
    regex_chars = r"[.*+?^${}()|[\]\\]"
    if any(c in q for c in regex_chars):
        try:
            logs_regex = tlog_crud.search_logs_by_regex_with_names(db, q, limit=limit)
            log_regex_total = tlog_crud.count_logs_by_regex(db, q)
            for log, trig_name, user_name in logs_regex:
                log_regex_items.append(
                    LogSearchResult(
                        id=log.id,  # type: ignore[arg-type]
                        trig_id=log.trig_id,  # type: ignore[arg-type]
                        trig_name=trig_name,
                        user_id=log.user_id,  # type: ignore[arg-type]
                        user_name=user_name,
                        date=log.date,  # type: ignore[arg-type]
                        time=log.time,  # type: ignore[arg-type]
                        comment=log.comment,  # type: ignore[arg-type]
                        comment_excerpt=create_excerpt(log.comment),  # type: ignore[arg-type]
                    )
                )
        except (DatabaseError, Exception):
            # Invalid regex or DB error, skip
            log_regex_total = 0

    return UnifiedSearchResults(
        query=q,
        trigpoints=SearchCategoryResults(
            total=trig_total,
            items=trigpoint_items,
            has_more=trig_total > len(trigpoint_items),
            query=q,
        ),
        places=SearchCategoryResults(
            total=town_total,
            items=place_items,
            has_more=town_total > len(place_items),
            query=q,
        ),
        users=SearchCategoryResults(
            total=user_total,
            items=user_items,
            has_more=user_total > len(user_items),
            query=q,
        ),
        postcodes=SearchCategoryResults(
            total=postcode_total,
            items=postcode_items,
            has_more=False,
            query=q,
        ),
        coordinates=SearchCategoryResults(
            total=len(coordinates_items),
            items=coordinates_items,
            has_more=False,
            query=q,
        ),
        log_substring=SearchCategoryResults(
            total=log_substring_total,
            items=log_substring_items,
            has_more=log_substring_total > len(log_substring_items),
            query=q,
        ),
        log_regex=SearchCategoryResults(
            total=log_regex_total,
            items=log_regex_items,
            has_more=log_regex_total > len(log_regex_items),
            query=q,
        ),
    )


@router.get(
    "/search/trigpoints",
    response_model=SearchCategoryResults[LocationSearchResult],
    openapi_extra=openapi_lifecycle("beta", note="Trigpoint search"),
)
@cached(resource_type="search_trigpoints", ttl=3600)  # 1 hour
def search_trigpoints_only(
    q: str = Query(..., description="Search query", min_length=2),
    skip: int = Query(0, ge=0, description="Number of results to skip"),
    limit: int = Query(20, ge=1, le=100, description="Maximum results to return"),
    _lc=lifecycle("beta"),
    db: Session = Depends(get_db),
):
    """Search trigpoints by name or waypoint."""
    trigs = locations_crud.search_trigpoints_by_name_or_waypoint(
        db, q, limit=skip + limit
    )[skip:]
    total = trig_crud.count_trigs_filtered(db, name=q)

    items: List[LocationSearchResult] = []
    for trig in trigs:
        if not trig.name or trig.wgs_lat is None or trig.wgs_long is None:
            continue
        parts = []
        if trig.waypoint:
            parts.append(str(trig.waypoint))
        if trig.physical_type:
            parts.append(str(trig.physical_type))
        description = " - ".join(parts) if parts else "Trigpoint"
        items.append(
            LocationSearchResult(
                type="trigpoint",
                name=str(trig.name).strip() or "Unnamed Trig",
                lat=float(trig.wgs_lat),
                lon=float(trig.wgs_long),
                description=description,
                id=str(trig.id),
            )
        )

    return SearchCategoryResults(
        total=total, items=items, has_more=total > skip + len(items), query=q
    )


@router.get(
    "/search/places",
    response_model=SearchCategoryResults[LocationSearchResult],
    openapi_extra=openapi_lifecycle("beta", note="Place/town search"),
)
@cached(resource_type="search_places", ttl=3600)  # 1 hour
def search_places_only(
    q: str = Query(..., description="Search query", min_length=2),
    skip: int = Query(0, ge=0, description="Number of results to skip"),
    limit: int = Query(20, ge=1, le=100, description="Maximum results to return"),
    _lc=lifecycle("beta"),
    db: Session = Depends(get_db),
):
    """Search places (towns) by name."""
    # Use offset/limit directly in query for efficiency
    from api.models.location import Town

    query_obj = db.query(Town).filter(Town.name.ilike(f"%{q}%"))
    total = query_obj.count()
    towns = query_obj.offset(skip).limit(limit).all()

    items: List[LocationSearchResult] = []
    for town in towns:
        if not town.name or town.wgs_lat is None or town.wgs_long is None:
            continue
        items.append(
            LocationSearchResult(
                type="town",
                name=str(town.name).strip().title() or "Unknown Town",
                lat=float(town.wgs_lat),
                lon=float(town.wgs_long),
                description="UK Town",
                id=None,
            )
        )

    return SearchCategoryResults(
        total=total, items=items, has_more=total > skip + len(items), query=q
    )


@router.get(
    "/search/users",
    response_model=SearchCategoryResults[LocationSearchResult],
    openapi_extra=openapi_lifecycle("beta", note="User search"),
)
@cached(resource_type="search_users", ttl=3600)  # 1 hour
def search_users_only(
    q: str = Query(..., description="Search query", min_length=2),
    skip: int = Query(0, ge=0, description="Number of results to skip"),
    limit: int = Query(20, ge=1, le=100, description="Maximum results to return"),
    _lc=lifecycle("beta"),
    db: Session = Depends(get_db),
):
    """Search users by name."""
    users = user_crud.search_users_by_name(db, q, skip=skip, limit=limit)
    total = db.query(User).filter(User.name.ilike(f"%{q}%")).count()

    items: List[LocationSearchResult] = []
    for user in users:
        if not user.name or not user.id:
            continue
        items.append(
            LocationSearchResult(
                type="user",
                name=str(user.name).strip(),
                lat=54.0,  # UK center
                lon=-2.0,
                description="User",
                id=str(user.id),
            )
        )

    return SearchCategoryResults(
        total=total, items=items, has_more=total > skip + len(items), query=q
    )


@router.get(
    "/search/postcodes",
    response_model=SearchCategoryResults[LocationSearchResult],
    openapi_extra=openapi_lifecycle("beta", note="Postcode search"),
)
@cached(resource_type="search_postcodes", ttl=3600)  # 1 hour
def search_postcodes_only(
    q: str = Query(..., description="Search query", min_length=2),
    skip: int = Query(0, ge=0, description="Number of results to skip"),
    limit: int = Query(20, ge=1, le=100, description="Maximum results to return"),
    _lc=lifecycle("beta"),
    db: Session = Depends(get_db),
):
    """Search postcodes."""
    pc6_results, postcodes_results = locations_crud.search_postcodes(
        db, q, skip=skip, limit=limit
    )

    items: List[LocationSearchResult] = []
    for pc in pc6_results:
        if not pc.code or pc.osgb_eastings is None or pc.osgb_northings is None:
            continue
        lat, lon = locations_crud.osgb_to_wgs84(
            int(pc.osgb_eastings), int(pc.osgb_northings)
        )
        description = str(pc.postal_town).strip() if pc.postal_town else "Postcode"
        items.append(
            LocationSearchResult(
                type="postcode",
                name=str(pc.code).strip(),
                lat=lat,
                lon=lon,
                description=description,
                id=None,
            )
        )

    for pc in postcodes_results:
        if not pc.code or pc.lat is None or pc.long is None:
            continue
        items.append(
            LocationSearchResult(
                type="postcode",
                name=str(pc.code).strip(),
                lat=float(pc.lat),
                lon=float(pc.long),
                description="UK Postcode",
                id=None,
            )
        )

    # Get total counts for both tables
    from api.models.location import Postcode, Postcode6

    query_upper = q.upper().strip()
    query_no_space = query_upper.replace(" ", "")
    query_normalized = " ".join(query_upper.split())
    pc6_total = (
        db.query(Postcode6).filter(Postcode6.code.like(f"{query_no_space}%")).count()
    )
    postcodes_total = (
        db.query(Postcode).filter(Postcode.code.like(f"{query_normalized}%")).count()
    )
    total = pc6_total + postcodes_total

    return SearchCategoryResults(
        total=total, items=items, has_more=total > skip + len(items), query=q
    )


@router.get(
    "/search/logs/substring",
    response_model=SearchCategoryResults[LogSearchResult],
    openapi_extra=openapi_lifecycle("beta", note="Log text substring search"),
)
@cached(resource_type="search_logs_substring", ttl=1800)  # 30 minutes
def search_logs_substring(
    q: str = Query(..., description="Search query", min_length=2),
    skip: int = Query(0, ge=0, description="Number of results to skip"),
    limit: int = Query(20, ge=1, le=100, description="Maximum results to return"),
    _lc=lifecycle("beta"),
    db: Session = Depends(get_db),
):
    """Search log comments by substring."""

    def create_excerpt(text: str, max_length: int = 150) -> str:
        if len(text) <= max_length:
            return text
        return text[:max_length] + "..."

    try:
        logs = tlog_crud.search_logs_by_text_with_names(db, q, skip=skip, limit=limit)
        total = tlog_crud.count_logs_by_text(db, q)

        items: List[LogSearchResult] = []
        for log, trig_name, user_name in logs:
            items.append(
                LogSearchResult(
                    id=log.id,  # type: ignore[arg-type]
                    trig_id=log.trig_id,  # type: ignore[arg-type]
                    trig_name=trig_name,
                    user_id=log.user_id,  # type: ignore[arg-type]
                    user_name=user_name,
                    date=log.date,  # type: ignore[arg-type]
                    time=log.time,  # type: ignore[arg-type]
                    comment=log.comment,  # type: ignore[arg-type]
                    comment_excerpt=create_excerpt(log.comment),  # type: ignore[arg-type]
                )
            )

        return SearchCategoryResults(
            total=total, items=items, has_more=total > skip + len(items), query=q
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@router.get(
    "/search/logs/regex",
    response_model=SearchCategoryResults[LogSearchResult],
    openapi_extra=openapi_lifecycle("beta", note="Log text regex search"),
)
@cached(resource_type="search_logs_regex", ttl=1800)  # 30 minutes
def search_logs_regex(
    q: str = Query(..., description="Regex pattern", min_length=2),
    skip: int = Query(0, ge=0, description="Number of results to skip"),
    limit: int = Query(20, ge=1, le=100, description="Maximum results to return"),
    _lc=lifecycle("beta"),
    db: Session = Depends(get_db),
):
    """Search log comments by regex pattern."""

    def create_excerpt(text: str, max_length: int = 150) -> str:
        if len(text) <= max_length:
            return text
        return text[:max_length] + "..."

    try:
        logs = tlog_crud.search_logs_by_regex_with_names(db, q, skip=skip, limit=limit)
        total = tlog_crud.count_logs_by_regex(db, q)

        items: List[LogSearchResult] = []
        for log, trig_name, user_name in logs:
            items.append(
                LogSearchResult(
                    id=log.id,  # type: ignore[arg-type]
                    trig_id=log.trig_id,  # type: ignore[arg-type]
                    trig_name=trig_name,
                    user_id=log.user_id,  # type: ignore[arg-type]
                    user_name=user_name,
                    date=log.date,  # type: ignore[arg-type]
                    time=log.time,  # type: ignore[arg-type]
                    comment=log.comment,  # type: ignore[arg-type]
                    comment_excerpt=create_excerpt(log.comment),  # type: ignore[arg-type]
                )
            )

        return SearchCategoryResults(
            total=total, items=items, has_more=total > skip + len(items), query=q
        )
    except DatabaseError as e:
        raise HTTPException(status_code=400, detail=f"Invalid regex pattern: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")
