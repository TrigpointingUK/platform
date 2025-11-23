"""
Trig endpoints for trigpoint data.
"""

import io
import json
import os
from datetime import date as date_type
from datetime import datetime
from math import cos, radians, sqrt
from typing import Any, Optional

import numpy as np
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi import Request as FastAPIRequest
from fastapi.encoders import jsonable_encoder
from fastapi.responses import StreamingResponse
from PIL import Image, ImageDraw
from sqlalchemy.orm import Session

from api.api.deps import get_current_user_optional, get_db
from api.api.lifecycle import lifecycle, openapi_lifecycle
from api.core.logging import get_logger
from api.core.metrics import get_metrics_collector
from api.crud import attr as attr_crud
from api.crud import status as status_crud
from api.crud import tlog as tlog_crud
from api.crud import tphoto as tphoto_crud
from api.crud import trig as trig_crud
from api.crud import trigstats as trigstats_crud
from api.models.server import Server
from api.models.trig import Trig
from api.models.user import TLog, User
from api.schemas.tphoto import TPhotoResponse
from api.schemas.trig import (
    TrigAttrsData,
    TrigDetails,
    TrigMinimal,
)
from api.schemas.trig import TrigStats as TrigStatsSchema
from api.schemas.trig import (
    TrigWithIncludes,
)
from api.services.cache_service import (
    cache_get,
    cache_set,
    generate_cache_key,
    get_redis_client,
)
from api.utils.cache_decorator import cached
from api.utils.geocalibrate import CalibrationResult
from api.utils.url import join_url

router = APIRouter()
logger = get_logger(__name__)


def _get_max_trig_timestamp(db: Session) -> Optional[datetime]:
    """
    Get the maximum upd_timestamp from trig table.

    This is a fast query that tells us if ANY trig has been updated
    since last cache generation. Used for smart cache invalidation.

    Returns None if no trigs have timestamps.
    """
    from sqlalchemy import func

    result = db.query(func.max(Trig.upd_timestamp)).scalar()
    return result


def _generate_export_data(db: Session) -> dict:
    """
    Generate the expensive export data for /export endpoint.

    Only called when data actually changed based on timestamp check.
    """
    # Get all trigs (no pagination, no filters)
    items = trig_crud.list_trigs_filtered(
        db,
        skip=0,
        limit=50000,  # Large enough for all trigs
    )

    # Serialize minimally with mode='json' to properly handle Decimal fields
    items_serialized = [
        TrigMinimal.model_validate(i).model_dump(mode="json") for i in items
    ]

    # Attach status_name to each item
    for item, orig in zip(items_serialized, items):
        item["status_name"] = status_crud.get_status_name_by_id(db, int(orig.status_id))

    return {
        "items": items_serialized,
        "total": len(items_serialized),
        "generated_at": datetime.utcnow().isoformat(),
    }


@router.get(
    "/export",
    openapi_extra=openapi_lifecycle("beta", note="Bulk export for offline apps"),
)
def export_trigs(
    request: FastAPIRequest,
    _lc=lifecycle("beta"),
    db: Session = Depends(get_db),
):
    """
    Export all trigpoints for offline use (Android app).

    Returns all ~30,000 trigpoints with minimal fields.

    Uses intelligent caching based on data freshness:
    - Cache TTL: 60 seconds
    - Checks MAX(upd_timestamp) when cache expires
    - Only regenerates if data actually changed
    - Supports ETag for HTTP 304 responses
    """
    import hashlib

    from redis.lock import Lock

    redis_client = get_redis_client()
    if redis_client is None:
        # If Redis is not available, fall back to generating fresh data
        result = _generate_export_data(db)
        from fastapi.responses import JSONResponse

        return JSONResponse(
            content=result,
            headers={
                "Cache-Control": "public, max-age=60",
                "X-Cache-Status": "REDIS-UNAVAILABLE",
            },
        )

    cache_key = generate_cache_key(
        resource_type="trigs", subresource="export", version="v1"
    )
    lock_key = f"{cache_key}:lock"

    # Get cached data and timestamp
    cached_entry, cache_age = cache_get(cache_key)
    cached_value, cached_timestamp = _extract_cached_payload(cached_entry)

    # Get current data timestamp from DB (fast query, ~163ms without index)
    current_timestamp = _get_max_trig_timestamp(db)
    current_timestamp_str = (
        current_timestamp.isoformat() if current_timestamp else "never"
    )

    # Generate ETag from timestamp (consistent across all responses with same data)
    etag = f'"{hashlib.md5(current_timestamp_str.encode(), usedforsecurity=False).hexdigest()}"'  # nosec B324

    # Check If-None-Match for HTTP 304 optimization
    if_none_match = request.headers.get("If-None-Match")
    if if_none_match == etag and cached_value is not None:
        # Client has current version - return 304 Not Modified
        from fastapi import Response

        return Response(
            status_code=304,
            headers={
                "ETag": etag,
                "Cache-Control": "public, max-age=60, stale-while-revalidate=300",
                "X-Cache-Status": "NOT-MODIFIED",
            },
        )

    # Cache is fresh (within 60s) - return immediately
    if cached_value is not None and cache_age is not None and cache_age < 60:
        from fastapi.responses import JSONResponse

        return JSONResponse(
            content=cached_value,
            headers={
                "ETag": etag,
                "Cache-Control": "public, max-age=60, stale-while-revalidate=300",
                "X-Cache-Status": "HIT",
                "X-Cache-Age": str(cache_age),
            },
        )

    # Cache expired or missing - check if data actually changed
    if cached_value is not None and cached_timestamp == current_timestamp_str:
        # Data hasn't changed - extend cache without regenerating!
        logger.info("Export data unchanged, extending cache without regeneration")
        cache_set(
            cache_key,
            jsonable_encoder(_wrap_cache_payload(cached_value, current_timestamp_str)),
            60,
        )

        from fastapi.responses import JSONResponse

        return JSONResponse(
            content=cached_value,
            headers={
                "ETag": etag,
                "Cache-Control": "public, max-age=60, stale-while-revalidate=300",
                "X-Cache-Status": "EXTENDED",
                "X-Data-Unchanged": "true",
            },
        )

    # Data changed or no cache - need to regenerate (with lock for stampede protection)
    lock = Lock(redis_client, lock_key, timeout=300, blocking_timeout=60)

    with lock:
        # Double-check cache (another request may have just populated it)
        cached_entry, _ = cache_get(cache_key)
        cached_value, cached_timestamp = _extract_cached_payload(cached_entry)

        if cached_value is not None and cached_timestamp == current_timestamp_str:
            # Another request just regenerated
            logger.info("Cache populated by another request during lock wait")
            from fastapi.responses import JSONResponse

            return JSONResponse(
                content=cached_value,
                headers={
                    "ETag": etag,
                    "Cache-Control": "public, max-age=60, stale-while-revalidate=300",
                    "X-Cache-Status": "HIT-AFTER-WAIT",
                },
            )

        # Generate fresh data
        logger.info("Regenerating export (data changed or cache empty)")
        result = _generate_export_data(db)

        # Store with both data and timestamp
        cache_set(
            cache_key,
            jsonable_encoder(_wrap_cache_payload(result, current_timestamp_str)),
            60,
        )

        from fastapi.responses import JSONResponse

        return JSONResponse(
            content=result,
            headers={
                "ETag": etag,
                "Cache-Control": "public, max-age=60, stale-while-revalidate=300",
                "X-Cache-Status": "REGENERATED",
                "X-Data-Timestamp": current_timestamp_str,
            },
        )


def _generate_geojson_data(db: Session, limit: Optional[int] = None) -> dict:
    """
    Generate the expensive GeoJSON export data.

    Only called when data actually changed based on timestamp check.
    """
    # Fetch all status types
    all_statuses = status_crud.get_all_statuses(db)

    # Filter to non-deleted statuses only (< 90)
    active_statuses = [s for s in all_statuses if s.id < 90]

    result: dict[str, Any] = {}

    for status in active_statuses:
        # Query trigpoints for this status
        status_id_int = int(status.id)  # Ensure it's an int for type checking
        items = trig_crud.list_trigs_filtered(
            db,
            status_ids=[status_id_int],
            skip=0,
            limit=limit if limit else 50000,
            exclude_soft_deleted=True,  # Ensure we exclude status >= 90
        )

        # Build GeoJSON features
        features = []
        for item in items:
            features.append(
                {
                    "type": "Feature",
                    "geometry": {
                        "type": "Point",
                        "coordinates": [float(item.wgs_long), float(item.wgs_lat)],
                    },
                    "properties": {
                        "id": item.id,
                        "name": item.name,
                        "condition": item.condition,
                        "osgb_gridref": item.osgb_gridref,
                        "physical_type": item.physical_type,
                    },
                }
            )

        # Convert status name to snake_case for dict key
        status_key = status.name.strip().lower().replace(" ", "_")
        result[status_key] = {
            "type": "FeatureCollection",
            "features": features,
        }

    # Add metadata
    result["generated_at"] = datetime.utcnow().isoformat()

    return result


def _wrap_cache_payload(payload: Any, data_timestamp: str) -> dict[str, Any]:
    """
    Wrap a cached payload with metadata so we can track data freshness.

    Metadata fields are placed first so they're visible at the top when
    viewing large payloads in Redis debugging tools.
    """
    return {
        "_data_timestamp": data_timestamp,
        "_cache_version": "v1",
        "_payload": payload,
    }


def _extract_cached_payload(
    cached_entry: Any,
) -> tuple[Optional[Any], Optional[str]]:
    """
    Extract the payload and timestamp from a cached entry.

    Supports both the new wrapped format (payload + metadata) and the legacy
    format where only the payload was stored.
    """
    if cached_entry is None:
        return None, None

    if isinstance(cached_entry, dict):
        if "_payload" in cached_entry and "_data_timestamp" in cached_entry:
            return (
                cached_entry.get("_payload"),
                cached_entry.get("_data_timestamp"),
            )
        # Legacy payload – fall back to using the payload directly, with any
        # generated_at field as a best-effort timestamp.
        return cached_entry, cached_entry.get("generated_at")

    # Non-dict payloads (unlikely) – treat as raw payload with no timestamp.
    return cached_entry, None


@router.get(
    "/geojson",
    openapi_extra=openapi_lifecycle("beta", note="GeoJSON export for map rendering"),
)
def export_trigs_geojson(
    request: FastAPIRequest,
    limit: Optional[int] = Query(
        None, description="Limit results per type (for testing only)"
    ),
    _lc=lifecycle("beta"),
    db: Session = Depends(get_db),
):
    """
    Export trigpoints in GeoJSON format for map display, grouped by status.

    Returns FeatureCollections for each status level (Pillar, Major mark, Minor mark, etc.).
    Each feature contains id, name, condition, osgb_gridref, and physical_type in properties.

    Excludes soft-deleted records (status >= 90).

    Uses intelligent caching based on data freshness:
    - Cache TTL: 60 seconds
    - Checks MAX(upd_timestamp) when cache expires
    - Only regenerates if data actually changed
    - Supports ETag for HTTP 304 responses
    """
    import hashlib

    from redis.lock import Lock

    redis_client = get_redis_client()
    if redis_client is None:
        # If Redis is not available, fall back to generating fresh data
        result = _generate_geojson_data(db, limit)
        from fastapi.responses import JSONResponse

        return JSONResponse(
            content=result,
            headers={
                "Cache-Control": "public, max-age=60",
                "X-Cache-Status": "REDIS-UNAVAILABLE",
            },
        )

    params = {"limit": limit} if limit is not None else None
    cache_key = generate_cache_key(
        resource_type="trigs", subresource="geojson", params=params, version="v1"
    )
    lock_key = f"{cache_key}:lock"

    # Get cached data and timestamp metadata
    cached_entry, cache_age = cache_get(cache_key)
    cached_value, cached_timestamp = _extract_cached_payload(cached_entry)

    # Get current data timestamp from DB (fast query, ~163ms without index)
    current_timestamp = _get_max_trig_timestamp(db)
    current_timestamp_str = (
        current_timestamp.isoformat() if current_timestamp else "never"
    )

    # Generate ETag from timestamp (consistent across all responses with same data)
    etag = f'"{hashlib.md5(current_timestamp_str.encode(), usedforsecurity=False).hexdigest()}"'  # nosec B324

    # Check If-None-Match for HTTP 304 optimization
    if_none_match = request.headers.get("If-None-Match")
    if if_none_match == etag and cached_value is not None:
        # Client has current version - return 304 Not Modified
        from fastapi import Response

        return Response(
            status_code=304,
            headers={
                "ETag": etag,
                "Cache-Control": "public, max-age=60, stale-while-revalidate=300",
                "X-Cache-Status": "NOT-MODIFIED",
            },
        )

    # Cache is fresh (within 60s) - return immediately
    if cached_value is not None and cache_age is not None and cache_age < 60:
        from fastapi.responses import JSONResponse

        return JSONResponse(
            content=cached_value,
            headers={
                "ETag": etag,
                "Cache-Control": "public, max-age=60, stale-while-revalidate=300",
                "X-Cache-Status": "HIT",
                "X-Cache-Age": str(cache_age),
            },
        )

    # Cache expired or missing - check if data actually changed
    if cached_value is not None and cached_timestamp == current_timestamp_str:
        logger.info("GeoJSON data unchanged, extending cache without regeneration")
        cache_set(
            cache_key,
            jsonable_encoder(_wrap_cache_payload(cached_value, current_timestamp_str)),
            60,
        )

        from fastapi.responses import JSONResponse

        return JSONResponse(
            content=cached_value,
            headers={
                "ETag": etag,
                "Cache-Control": "public, max-age=60, stale-while-revalidate=300",
                "X-Cache-Status": "EXTENDED",
                "X-Data-Unchanged": "true",
            },
        )

    # Data changed or no cache - need to regenerate (with lock for stampede protection)
    lock = Lock(redis_client, lock_key, timeout=300, blocking_timeout=60)

    with lock:
        # Double-check cache (another request may have just populated it)
        cached_entry, _ = cache_get(cache_key)
        cached_value, cached_timestamp = _extract_cached_payload(cached_entry)

        if cached_value is not None and cached_timestamp == current_timestamp_str:
            logger.info("Cache populated by another request during lock wait")
            from fastapi.responses import JSONResponse

            return JSONResponse(
                content=cached_value,
                headers={
                    "ETag": etag,
                    "Cache-Control": "public, max-age=60, stale-while-revalidate=300",
                    "X-Cache-Status": "HIT-AFTER-WAIT",
                },
            )

        # Generate fresh data
        logger.info("Regenerating GeoJSON (data changed or cache empty)")
        result = _generate_geojson_data(db, limit)

        # Log the result size for debugging
        logger.info(
            f"Generated GeoJSON with {len(result)} top-level keys, "
            f"wrapping and caching with timestamp {current_timestamp_str}"
        )

        # Store with both data and timestamp metadata
        wrapped_payload = _wrap_cache_payload(result, current_timestamp_str)
        cache_set(
            cache_key,
            jsonable_encoder(wrapped_payload),
            60,
        )

        from fastapi.responses import JSONResponse

        logger.info(
            f"Returning GeoJSON response with {len(result)} keys, "
            f"X-Cache-Status: REGENERATED"
        )

        return JSONResponse(
            content=result,
            headers={
                "ETag": etag,
                "Cache-Control": "public, max-age=60, stale-while-revalidate=300",
                "X-Cache-Status": "REGENERATED",
                "X-Data-Timestamp": current_timestamp_str,
            },
        )


@cached(resource_type="trig", ttl=86400, resource_id_param="trig_id")  # 24 hours
def _get_trig_cached(
    trig_id: int,
    include: Optional[str],
    db: Session,
):
    """Internal cached function for fetching trig data."""
    trig = trig_crud.get_trig_by_id(db, trig_id=trig_id)
    if trig is None:
        raise HTTPException(status_code=404, detail="Trigpoint not found")

    # Build minimal response with status_name
    minimal_data = TrigMinimal.model_validate(trig).model_dump()
    status_name = status_crud.get_status_name_by_id(db, int(trig.status_id))
    minimal_data["status_name"] = status_name

    # Attach includes
    details_obj: Optional[TrigDetails] = None
    stats_obj: Optional[TrigStatsSchema] = None
    attrs_obj: Optional[list[TrigAttrsData]] = None
    if include:
        tokens = {t.strip() for t in include.split(",") if t.strip()}

        # Validate include tokens
        valid_includes = {"details", "stats", "attrs"}
        invalid_tokens = tokens - valid_includes
        if invalid_tokens:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid include parameter(s): {', '.join(sorted(invalid_tokens))}. Valid options: {', '.join(sorted(valid_includes))}",
            )
        if "details" in tokens:
            details_obj = TrigDetails.model_validate(trig)
        if "stats" in tokens:
            stats = trigstats_crud.get_trigstats_by_id(db, trig_id=trig_id)
            if stats:
                stats_obj = TrigStatsSchema.model_validate(stats)
        if "attrs" in tokens:
            attrs_data = attr_crud.get_attrs_for_trig(db, trig_id=trig_id)
            if attrs_data:
                attrs_obj = [TrigAttrsData(**item) for item in attrs_data]

    return TrigWithIncludes(
        **minimal_data, details=details_obj, stats=stats_obj, attrs=attrs_obj
    )


@router.get(
    "/{trig_id}",
    response_model=TrigWithIncludes,
    openapi_extra=openapi_lifecycle(
        "beta", note="Shape may change; fieldset stabilising"
    ),
)
def get_trig(
    trig_id: int,
    request: FastAPIRequest,
    include: Optional[str] = Query(
        None, description="Comma-separated list of includes: details,stats,attrs"
    ),
    _lc=lifecycle("beta", note="Shape may change"),
    db: Session = Depends(get_db),
):
    """
    Get a trigpoint by ID.

    Default: minimal fields. Supports include=details,stats,attrs.
    """
    # Determine cache status by checking if the cached function will return cached data
    # Generate the same cache key that the @cached decorator will use
    from api.utils.cache_decorator import cache_get, generate_cache_key

    cache_key = generate_cache_key(
        resource_type="trig",
        resource_id=str(trig_id),
        params={"include": include} if include else None,
    )

    # Check if we have a cached value
    cached_value, _ = cache_get(cache_key)
    cache_status = "hit" if cached_value is not None else "miss"

    # Check for cache bypass header
    if request and "no-cache" in request.headers.get("cache-control", "").lower():
        cache_status = "bypass"

    # Record trig view metric with cache status
    metrics = get_metrics_collector()
    if metrics:
        metrics.record_trig_view(trig_id, cache_status=cache_status)

    # Call the cached function to get the data
    return _get_trig_cached(trig_id=trig_id, include=include, db=db)


@router.get(
    "/waypoint/{waypoint}",
    response_model=TrigWithIncludes,
    openapi_extra=openapi_lifecycle("beta", note="Returns minimal shape only"),
)
def get_trig_by_waypoint(
    waypoint: str, _lc=lifecycle("beta"), db: Session = Depends(get_db)
):
    """
    Get a trigpoint by waypoint code (e.g., "TP0001").

    Returns minimal data by waypoint.
    """
    trig = trig_crud.get_trig_by_waypoint(db, waypoint=waypoint)
    if trig is None:
        raise HTTPException(status_code=404, detail="Trigpoint not found")

    minimal_data = TrigMinimal.model_validate(trig).model_dump()
    status_name = status_crud.get_status_name_by_id(db, int(trig.status_id))
    minimal_data["status_name"] = status_name
    return TrigWithIncludes(**minimal_data)


# removed deprecated name search endpoint


@router.get(
    "",
    openapi_extra=openapi_lifecycle("beta", note="Filtered collection listing"),
)
@cached(resource_type="trigs", ttl=43200, subresource="list")  # 12 hours
def list_trigs(
    name: Optional[str] = Query(None, description="Filter by trig name (contains)"),
    county: Optional[str] = Query(None, description="Filter by county (exact)"),
    lat: Optional[float] = Query(None, description="Centre latitude (WGS84)"),
    lon: Optional[float] = Query(None, description="Centre longitude (WGS84)"),
    max_km: Optional[float] = Query(
        None, ge=0, description="Max distance from centre (km)"
    ),
    order: Optional[str] = Query(None, description="id | name | distance"),
    physical_types: Optional[str] = Query(
        None, description="Comma-separated physical types to include"
    ),
    status_ids: Optional[str] = Query(
        None, description="Comma-separated status IDs to include (e.g., '10,20,30')"
    ),
    exclude_found: Optional[bool] = Query(
        False, description="Exclude trigpoints already logged by authenticated user"
    ),
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    _lc=lifecycle("beta"),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user_optional),
):
    """
    Filtered collection endpoint for trigs returning envelope with items, pagination, links.

    Filters:
    - physical_types: Filter by physical type (e.g., "Pillar,Bolt,FBM")
    - status_ids: Filter by status IDs (e.g., "10,20,30")
    - exclude_found: Exclude trigpoints the user has already logged (requires authentication)

    If authenticated, applies user's status_max preference to limit visible trigs.
    Always excludes soft-deleted records (status >= 90).
    """
    # Record trig search metric
    metrics = get_metrics_collector()
    if metrics:
        search_type = "nearby" if (lat and lon and max_km) else "general"
        metrics.record_trig_search(search_type)

    # Parse physical types
    physical_types_list = None
    if physical_types:
        physical_types_list = [
            pt.strip() for pt in physical_types.split(",") if pt.strip()
        ]

    # Parse status IDs
    status_ids_list = None
    if status_ids:
        status_ids_list = [
            int(sid.strip()) for sid in status_ids.split(",") if sid.strip()
        ]

    # Apply user's status_max preference if authenticated
    max_status = None
    if current_user and hasattr(current_user, "status_max") and current_user.status_max:
        max_status = int(current_user.status_max)
    else:
        # Default for unauthenticated users
        max_status = 30

    # Get user ID for exclude_found filter
    exclude_found_by_user_id = None
    if exclude_found and current_user:
        exclude_found_by_user_id = int(current_user.id)

    items = trig_crud.list_trigs_filtered(
        db,
        name=name,
        county=county,
        skip=skip,
        limit=limit,
        center_lat=lat,
        center_lon=lon,
        max_km=max_km,
        order=order,
        physical_types=physical_types_list,
        status_ids=status_ids_list,
        max_status=max_status,
        exclude_found_by_user_id=exclude_found_by_user_id,
        exclude_soft_deleted=True,  # Always exclude status >= 90
    )
    total = trig_crud.count_trigs_filtered(
        db,
        name=name,
        county=county,
        center_lat=lat,
        center_lon=lon,
        max_km=max_km,
        physical_types=physical_types_list,
        status_ids=status_ids_list,
        max_status=max_status,
        exclude_found_by_user_id=exclude_found_by_user_id,
        exclude_soft_deleted=True,  # Always exclude status >= 90
    )

    # serialise
    items_serialized = [TrigMinimal.model_validate(i).model_dump() for i in items]

    # Compute distance_km for returned page only (cheap), matching SQL formula
    if lat is not None and lon is not None:
        deg_km = 111.32
        cos_lat = cos(radians(lat))
        for d in items_serialized:
            dlat_km = (float(d["wgs_lat"]) - lat) * deg_km
            dlon_km = (float(d["wgs_long"]) - lon) * deg_km * cos_lat
            d["distance_km"] = round(sqrt(dlat_km * dlat_km + dlon_km * dlon_km), 1)

    has_more = (skip + len(items)) < total
    base = "/v1/trigs"
    params = []
    if name:
        params.append(f"name={name}")
    if county:
        params.append(f"county={county}")
    if lat is not None:
        params.append(f"lat={lat}")
    if lon is not None:
        params.append(f"lon={lon}")
    if max_km is not None:
        params.append(f"max_km={max_km}")
    if order:
        params.append(f"order={order}")
    if physical_types:
        params.append(f"physical_types={physical_types}")
    if status_ids:
        params.append(f"status_ids={status_ids}")
    if exclude_found:
        params.append("exclude_found=true")
    params.append(f"limit={limit}")
    # self link
    self_link = base + "?" + "&".join(params + [f"skip={skip}"])
    next_link = (
        base + "?" + "&".join(params + [f"skip={skip + limit}"]) if has_more else None
    )
    prev_offset = max(skip - limit, 0)
    prev_link = (
        base + "?" + "&".join(params + [f"skip={prev_offset}"]) if skip > 0 else None
    )

    # Serialize items minimally
    # items_serialized = [TrigMinimal.model_validate(i).model_dump() for i in items]
    # Attach status_name to each item
    for item, orig in zip(items_serialized, items):
        item["status_name"] = status_crud.get_status_name_by_id(db, int(orig.status_id))

    response = {
        "items": items_serialized,
        "pagination": {
            "total": total,
            "limit": limit,
            "offset": skip,
            "has_more": has_more,
        },
        "links": {"self": self_link, "next": next_link, "prev": prev_link},
    }
    if lat is not None and lon is not None:
        response["context"] = {
            "centre": {"lat": lat, "lon": lon, "srid": 4326},
            "max_km": max_km,
            "order": order or "distance",
        }
    else:
        response["context"] = {"order": order or "id"}
    return response


# -----------------------------------------------------------------------------
# Map for a single trig
# -----------------------------------------------------------------------------


@router.get(
    "/{trig_id}/map",
    responses={200: {"content": {"image/png": {}}, "description": "PNG map for trig"}},
    openapi_extra=openapi_lifecycle(
        "beta",
        note=(
            "Loads a pre-styled map PNG and draws a single dot at the trig's WGS84 position. "
            "Use scripts/make_styled_map.py to create new map styles."
        ),
    ),
)
@cached(
    resource_type="trig", ttl=14400, resource_id_param="trig_id", subresource="map"
)  # 4 hours
async def get_trig_map(
    trig_id: int,
    style: str = Query(
        "stretched53_default",
        description="Style name (base filename without extension) from res/ directory",
    ),
    dot_colour: str = Query("#0000ff", description="Hex #RRGGBB for the trig dot"),
    dot_diameter: int = Query(
        5, ge=1, le=100, description="Dot diameter in pixels (default 5)"
    ),
    db: Session = Depends(get_db),
):
    """
    Render a map PNG with a dot at the trig location.

    This endpoint loads pre-styled [.png, .json] pairs from res/ directory.
    To create new styles, use scripts/make_styled_map.py.
    """
    # Fetch trig
    trig = trig_crud.get_trig_by_id(db, trig_id=trig_id)
    if trig is None:
        raise HTTPException(status_code=404, detail="Trigpoint not found")

    # Load pre-styled assets
    res_dir = os.path.normpath(
        os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "..",
            "..",
            "res",
        )
    )
    map_path = os.path.join(res_dir, f"{style}.png")
    calib_path = os.path.join(res_dir, f"{style}.json")

    # Validate files exist
    if not os.path.isfile(map_path):
        raise HTTPException(
            status_code=404, detail=f"Map style '{style}' not found (missing PNG)"
        )
    if not os.path.isfile(calib_path):
        raise HTTPException(
            status_code=404, detail=f"Map style '{style}' not found (missing JSON)"
        )

    # Load image and calibration
    base = Image.open(map_path).convert("RGBA")
    with open(calib_path, "r") as f:
        d = json.load(f)
    calib = CalibrationResult(
        affine=np.array(d["affine"], dtype=float),
        inverse=np.array(d["inverse"], dtype=float),
        pixel_bbox=tuple(d.get("pixel_bbox", (0, 0, base.size[0], base.size[1]))),
        bounds_geo=tuple(d.get("bounds_geo", (-11.0, 49.0, 2.5, 61.5))),
    )

    # Draw a single opaque dot at trig location
    x, y = calib.lonlat_to_xy(float(trig.wgs_long), float(trig.wgs_lat))
    draw = ImageDraw.Draw(base)
    r = max(1, int(round(dot_diameter / 2)))

    # Parse dot colour
    s = dot_colour.strip()
    if s.startswith("#"):
        s = s[1:]
    if len(s) >= 6:
        rr = int(s[0:2], 16)
        gg = int(s[2:4], 16)
        bb = int(s[4:6], 16)
        fill = (rr, gg, bb, 255)  # hardcoded 100% alpha
    else:
        fill = (0, 0, 170, 255)  # fallback blue

    bbox = [
        int(round(x - r)),
        int(round(y - r)),
        int(round(x + r)),
        int(round(y + r)),
    ]
    draw.ellipse(bbox, fill=fill, outline=None)

    # Return PNG
    buf = io.BytesIO()
    base.save(buf, format="PNG")
    buf.seek(0)
    return StreamingResponse(buf, media_type="image/png")


@router.get(
    "/{trig_id}/logs",
    openapi_extra=openapi_lifecycle("beta", note="List logs for a trig"),
)
@cached(
    resource_type="trig", ttl=7200, resource_id_param="trig_id", subresource="logs"
)  # 2 hours
def list_logs_for_trig(
    trig_id: int,
    include: Optional[str] = Query(
        None, description="Comma-separated list of includes: photos"
    ),
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
):
    items = tlog_crud.list_logs_filtered(db, trig_id=trig_id, skip=skip, limit=limit)
    total = tlog_crud.count_logs_filtered(db, trig_id=trig_id)

    # Import helper from logs endpoint
    from api.api.v1.endpoints.logs import enrich_logs_with_names

    items_serialized = enrich_logs_with_names(db, items)

    # Handle includes
    if include:
        tokens = {t.strip() for t in include.split(",") if t.strip()}

        # Validate include tokens
        valid_includes = {"photos"}
        invalid_tokens = tokens - valid_includes
        if invalid_tokens:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid include parameter(s): {', '.join(sorted(invalid_tokens))}. Valid options: {', '.join(sorted(valid_includes))}",
            )
        if "photos" in tokens:
            for out, orig in zip(items_serialized, items):
                photos = tphoto_crud.list_all_photos_for_log(db, log_id=int(orig.id))
                out["photos"] = []
                for p in photos:
                    server: Server | None = (
                        db.query(Server).filter(Server.id == p.server_id).first()
                    )
                    base_url = str(server.url) if server and server.url else ""
                    # Handle empty type field by defaulting to 'O' (other)
                    photo_type = str(p.type) if p.type and p.type.strip() else "O"
                    out["photos"].append(
                        TPhotoResponse(
                            id=int(p.id),
                            log_id=int(p.tlog_id),
                            user_id=int(orig.user_id),
                            type=photo_type,
                            filesize=int(p.filesize),
                            height=int(p.height),
                            width=int(p.width),
                            icon_filesize=int(p.icon_filesize),
                            icon_height=int(p.icon_height),
                            icon_width=int(p.icon_width),
                            name=str(p.name),
                            text_desc=str(p.text_desc),
                            public_ind=str(p.public_ind),
                            photo_url=join_url(base_url, str(p.filename)),
                            icon_url=join_url(base_url, str(p.icon_filename)),
                        ).model_dump()
                    )
    has_more = (skip + len(items)) < total
    base = f"/v1/trigs/{trig_id}/logs"
    self_link = base + f"?limit={limit}&skip={skip}"
    next_link = base + f"?limit={limit}&skip={skip + limit}" if has_more else None
    prev_offset = max(skip - limit, 0)
    prev_link = base + f"?limit={limit}&skip={prev_offset}" if skip > 0 else None
    return {
        "items": items_serialized,
        "pagination": {
            "total": total,
            "limit": limit,
            "offset": skip,
            "has_more": has_more,
        },
        "links": {"self": self_link, "next": next_link, "prev": prev_link},
    }


# removed POST /{trig_id}/logs to keep mutations on their resource endpoints


@router.get(
    "/{trig_id}/photos",
    openapi_extra=openapi_lifecycle("beta", note="List photos for a trig"),
)
@cached(
    resource_type="trig", ttl=7200, resource_id_param="trig_id", subresource="photos"
)  # 2 hours
def list_photos_for_trig(
    trig_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
):
    items = tphoto_crud.list_photos_filtered(
        db, trig_id=trig_id, skip=skip, limit=limit
    )
    total = (
        db.query(tphoto_crud.TPhoto)
        .join(tlog_crud.TLog, tlog_crud.TLog.id == tphoto_crud.TPhoto.tlog_id)
        .filter(
            tlog_crud.TLog.trig_id == trig_id, tphoto_crud.TPhoto.deleted_ind != "Y"
        )
        .count()
    )
    result_items = []
    # Get trig info once (for all photos)
    trig = db.query(Trig).filter(Trig.id == trig_id).first()

    for p in items:
        # Defer URLs; provide minimal fields consistent with collection shape
        # Resolve user via TLog join
        tlog = db.query(TLog).filter(TLog.id == p.tlog_id).first()
        user = db.query(User).filter(User.id == tlog.user_id).first() if tlog else None

        server: Server | None = (
            db.query(Server).filter(Server.id == p.server_id).first()
        )
        base_url = str(server.url) if server and server.url else ""
        # Handle empty type field by defaulting to 'O' (other)
        photo_type = str(p.type) if p.type and p.type.strip() else "O"
        result_items.append(
            TPhotoResponse(
                id=int(p.id),
                log_id=int(p.tlog_id),
                user_id=int(tlog.user_id) if tlog else 0,
                type=photo_type,
                filesize=int(p.filesize),
                height=int(p.height),
                width=int(p.width),
                icon_filesize=int(p.icon_filesize),
                icon_height=int(p.icon_height),
                icon_width=int(p.icon_width),
                name=str(p.name),
                text_desc=str(p.text_desc),
                public_ind=str(p.public_ind),
                photo_url=join_url(base_url, str(p.filename)),
                icon_url=join_url(base_url, str(p.icon_filename)),
                user_name=str(user.name) if user else None,
                trig_id=trig_id,
                trig_name=str(trig.name) if trig else None,
                log_date=(
                    date_type(tlog.date.year, tlog.date.month, tlog.date.day)
                    if tlog and tlog.date
                    else None
                ),
            ).model_dump()
        )

    has_more = (skip + len(items)) < total
    base = f"/v1/trigs/{trig_id}/photos"
    self_link = base + f"?limit={limit}&skip={skip}"
    next_link = base + f"?limit={limit}&skip={skip + limit}" if has_more else None
    prev_offset = max(skip - limit, 0)
    prev_link = base + f"?limit={limit}&skip={prev_offset}" if skip > 0 else None
    return {
        "items": result_items,
        "pagination": {
            "total": total,
            "limit": limit,
            "offset": skip,
            "has_more": has_more,
        },
        "links": {"self": self_link, "next": next_link, "prev": prev_link},
    }
