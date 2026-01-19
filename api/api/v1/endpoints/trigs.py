"""
Trig endpoints for trigpoint data.
"""

import hashlib
import io
import json
import os
import time
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
from redis.exceptions import ConnectionError as RedisConnectionError
from redis.exceptions import LockError
from redis.lock import Lock
from sqlalchemy.orm import Session

from api.api.deps import get_current_user_optional, get_db
from api.api.lifecycle import lifecycle, openapi_lifecycle
from api.core.logging import get_logger
from api.core.metrics import get_metrics_collector
from api.crud import attr as attr_crud
from api.crud import tlog as tlog_crud
from api.crud import tphoto as tphoto_crud
from api.crud import trig as trig_crud
from api.crud import trigstats as trigstats_crud
from api.models.server import Server
from api.models.trig import Trig
from api.models.trig_type import TrigCategory, TrigType
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

CACHE_VALIDATION_INTERVAL_SECONDS = 60
CACHE_PERSIST_TTL: Optional[int] = None  # Persist until explicitly replaced
CACHE_VERSION = "v2"


def _build_etag(data_timestamp: Optional[str]) -> str:
    """
    Build a stable ETag from the data timestamp stored in the cache wrapper.
    """
    base = data_timestamp or "unknown"
    return f'"{hashlib.md5(base.encode(), usedforsecurity=False).hexdigest()}"'  # nosec B324


def _should_revalidate(last_validation_iso: Optional[str], now: datetime) -> bool:
    if not last_validation_iso:
        return True
    try:
        last_validation = datetime.fromisoformat(last_validation_iso)
    except ValueError:
        return True
    return (now - last_validation).total_seconds() >= CACHE_VALIDATION_INTERVAL_SECONDS


def _current_timestamp_str(db: Session) -> str:
    current_timestamp = _get_max_trig_timestamp(db)
    return current_timestamp.isoformat() if current_timestamp else "never"


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
    - Cached payload persists until the trig data actually changes
    - Revalidates at most once every 60 seconds
    - Serves stale content while a refresh is in progress
    - Supports ETag for HTTP 304 responses
    """
    cache_key = generate_cache_key(
        resource_type="trigs", subresource="export", version="v1"
    )
    lock_key = f"{cache_key}:lock"

    metadata = _get_cache_metadata(cache_key)
    cached_entry, _ = cache_get(cache_key)
    cached_value, cached_timestamp, legacy_last_validation = _extract_cached_payload(
        cached_entry
    )
    last_validation = metadata.get("last_validation") or legacy_last_validation

    cache_status = "HIT"
    if cached_value is None:
        cached_entry = _generate_and_cache_payload(
            cache_key=cache_key,
            lock_key=lock_key,
            db=db,
            generator_fn=_generate_export_payload,
            limit=None,
            log_label="Export cache miss",
        )
        cached_value, cached_timestamp, legacy_last_validation = (
            _extract_cached_payload(cached_entry)
        )
        metadata = _get_cache_metadata(cache_key)
        last_validation = metadata.get("last_validation") or legacy_last_validation
        cache_status = "MISS"

    if cached_value is None:
        payload = _generate_export_data(db)
        timestamp_str = _current_timestamp_str(db)
        etag = _build_etag(timestamp_str)
        from fastapi.responses import JSONResponse

        return JSONResponse(
            content=payload,
            headers={
                "ETag": etag,
                "Cache-Control": "public, max-age=60, stale-while-revalidate=300",
                "X-Cache-Status": "MISS-NO-CACHE",
                "X-Data-Timestamp": timestamp_str,
            },
        )

    now = datetime.utcnow()
    if_none_match = request.headers.get("If-None-Match")

    if cached_entry and _should_revalidate(last_validation, now):
        refreshed_entry, metadata, refresh_status = _maybe_refresh_cache_entry(
            cache_key=cache_key,
            lock_key=lock_key,
            cached_entry=cached_entry,
            db=db,
            generator_fn=_generate_export_payload,
            limit=None,
            log_label="Export cache",
            metadata=metadata,
        )
        if refreshed_entry is not None:
            cached_entry = refreshed_entry
            cached_value, cached_timestamp, legacy_last_validation = (
                _extract_cached_payload(refreshed_entry)
            )
        last_validation = metadata.get("last_validation") or legacy_last_validation
        cache_status = refresh_status

    etag = _build_etag(cached_timestamp)

    if if_none_match == etag:
        from fastapi import Response

        return Response(
            status_code=304,
            headers={
                "ETag": etag,
                "Cache-Control": "public, max-age=60, stale-while-revalidate=300",
                "X-Cache-Status": "NOT-MODIFIED",
            },
        )

    from fastapi.responses import JSONResponse

    data_timestamp_header = _get_entry_timestamp(
        cached_entry if isinstance(cached_entry, dict) else None
    )

    return JSONResponse(
        content=cached_value,
        headers={
            "ETag": etag,
            "Cache-Control": "public, max-age=60, stale-while-revalidate=300",
            "X-Cache-Status": cache_status,
            "X-Data-Timestamp": data_timestamp_header,
        },
    )


def _generate_geojson_data(db: Session, limit: Optional[int] = None) -> dict:
    """
    Generate the expensive GeoJSON export data.

    Only called when data actually changed based on timestamp check.

    Uses a single optimised query joining trig → trig_type → trig_type_group,
    selecting only the columns needed for GeoJSON output.
    """
    # Known group codes that map to the 6 filter buttons
    KNOWN_GROUP_CODES = {
        "PILLAR",
        "FBM",
        "SURVEY_MARK",
        "INTERSECTED",
        "ACTIVE",
        "OTHER",
    }

    # Single optimised query: select only needed columns with 3-way join
    # trig → trig_type → trig_type_group
    query = (
        db.query(
            Trig.id,
            Trig.name,
            Trig.condition,
            Trig.osgb_gridref,
            Trig.wgs_lat,
            Trig.wgs_long,
            TrigType.name.label("type_name"),
            TrigCategory.code.label("category_code"),
            TrigCategory.name.label("category_name"),
            TrigCategory.description.label("category_description"),
        )
        .join(TrigType, Trig.type_id == TrigType.id)
        .join(TrigCategory, TrigType.category_id == TrigCategory.id)
        .filter(Trig.status_id < 90)  # Exclude soft-deleted records
    )

    if limit:
        query = query.limit(limit)

    rows = query.all()

    # Group results by category_code
    categories_data: dict[str, dict[str, Any]] = {}
    unmapped_trigs: list[dict[str, Any]] = []

    for row in rows:
        category_code = row.category_code

        # Check if this category is in our known list
        if category_code not in KNOWN_GROUP_CODES:
            unmapped_trigs.append(
                {
                    "id": row.id,
                    "name": row.name,
                    "category_code": category_code,
                    "category_name": row.category_name,
                }
            )
            continue

        # Initialise category if not seen before
        if category_code not in categories_data:
            categories_data[category_code] = {
                "type": "FeatureCollection",
                "name": row.category_name,
                "description": row.category_description or "",
                "features": [],
            }

        # Add feature to category
        categories_data[category_code]["features"].append(
            {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [float(row.wgs_long), float(row.wgs_lat)],
                },
                "properties": {
                    "id": row.id,
                    "name": row.name,
                    "condition": row.condition,
                    "osgb_gridref": row.osgb_gridref,
                    "physical_type": row.type_name,  # From trig_type.name
                },
            }
        )

    # Build result with categories in consistent order
    result: dict[str, Any] = {}
    for code in KNOWN_GROUP_CODES:
        if code in categories_data:
            result[code] = categories_data[code]

    # Add warning if any trigs were in unmapped categories
    if unmapped_trigs:
        # Group unmapped trigs by their category for the warning
        unmapped_by_category: dict[str, int] = {}
        for trig in unmapped_trigs:
            key = f"{trig['category_code']} ({trig['category_name']})"
            unmapped_by_category[key] = unmapped_by_category.get(key, 0) + 1

        result["_warning"] = {
            "message": "⚠️ Some trigpoints not displayed",
            "reason": "Trigpoints belong to categories not in the standard filter set",
            "unmapped_count": len(unmapped_trigs),
            "unmapped_categories": unmapped_by_category,
            "sample_trigs": unmapped_trigs[:5],  # First 5 as examples
        }

    # Add metadata
    result["generated_at"] = datetime.utcnow().isoformat()

    return result


def _wrap_cache_payload(
    payload: Any, data_timestamp: str, *, last_validation: Optional[str] = None
) -> dict[str, Any]:
    """
    Wrap a cached payload with metadata so we can track data freshness.

    Metadata fields are placed first so they're visible at the top when
    viewing large payloads in Redis debugging tools.
    """
    return {
        "_data_timestamp": data_timestamp,
        "_cache_version": CACHE_VERSION,
        "_payload": payload,
    }


def _extract_cached_payload(
    cached_entry: Any,
) -> tuple[Optional[Any], Optional[str], Optional[str]]:
    """
    Extract the payload and timestamp from a cached entry.

    Supports both the new wrapped format (payload + metadata) and the legacy
    format where only the payload was stored.
    """
    if cached_entry is None:
        return None, None, None

    if isinstance(cached_entry, dict):
        if "_payload" in cached_entry and "_data_timestamp" in cached_entry:
            return (
                cached_entry.get("_payload"),
                cached_entry.get("_data_timestamp"),
                cached_entry.get("_last_validation"),
            )
        # Legacy payload – fall back to using the payload directly, with any
        # generated_at field as a best-effort timestamp.
        return (
            cached_entry,
            cached_entry.get("generated_at"),
            cached_entry.get("_last_validation"),
        )

    # Non-dict payloads (unlikely) – treat as raw payload with no timestamp.
    return cached_entry, None, None


def _generate_export_payload(db: Session, limit: Optional[int] = None) -> dict:
    # limit parameter kept for API symmetry; not used for export payload
    return _generate_export_data(db)


def _generate_geojson_payload(db: Session, limit: Optional[int] = None) -> dict:
    return _generate_geojson_data(db, limit)


def _write_cache_entry(cache_key: str, wrapper: dict[str, Any]) -> None:
    serialize_start = time.perf_counter()
    serializable_wrapper = jsonable_encoder(wrapper)
    serialize_ms = (time.perf_counter() - serialize_start) * 1000

    write_start = time.perf_counter()
    success = cache_set(cache_key, serializable_wrapper, CACHE_PERSIST_TTL)
    write_ms = (time.perf_counter() - write_start) * 1000

    logger.info(
        "Cache write key=%s success=%s serialize_ms=%.2f write_ms=%.2f",
        cache_key,
        success,
        serialize_ms,
        write_ms,
    )


def _metadata_key(cache_key: str) -> str:
    return f"{cache_key}:meta"


def _get_cache_metadata(cache_key: str) -> dict[str, Any]:
    metadata_entry, _ = cache_get(_metadata_key(cache_key))
    if isinstance(metadata_entry, dict):
        return metadata_entry
    return {}


def _set_cache_metadata(cache_key: str, metadata: dict[str, Any]) -> float:
    metadata_key = _metadata_key(cache_key)
    start = time.perf_counter()
    success = cache_set(metadata_key, metadata, CACHE_PERSIST_TTL)
    duration_ms = (time.perf_counter() - start) * 1000
    logger.info(
        "Cache metadata write key=%s success=%s duration_ms=%.2f",
        metadata_key,
        success,
        duration_ms,
    )
    return duration_ms


def _get_entry_timestamp(entry: Optional[dict[str, Any]]) -> str:
    if isinstance(entry, dict):
        ts = entry.get("_data_timestamp")
        if isinstance(ts, str):
            return ts
    return "unknown"


def _generate_and_cache_payload(
    *,
    cache_key: str,
    lock_key: str,
    db: Session,
    generator_fn,
    limit: Optional[int],
    log_label: str,
) -> dict:
    """
    Generate a fresh payload, storing it in cache. Handles locking so that
    only one request populates the cache on a miss.

    Falls back gracefully if Redis is unavailable.
    """
    redis_client = get_redis_client()
    if redis_client is not None:
        try:
            lock = Lock(redis_client, lock_key, timeout=300, blocking_timeout=60)
            with lock:
                cached_entry, _ = cache_get(cache_key)
                if cached_entry:
                    return cached_entry

                payload = generator_fn(db, limit)
                timestamp_str = _current_timestamp_str(db)
                wrapper = _wrap_cache_payload(payload, timestamp_str)
                _write_cache_entry(cache_key, wrapper)
                metadata = {
                    "last_validation": datetime.utcnow().isoformat(),
                    "cache_version": CACHE_VERSION,
                }
                _set_cache_metadata(cache_key, metadata)
                logger.info(f"{log_label}: Cache populated")
                return wrapper
        except (LockError, RedisConnectionError, Exception) as e:
            # Redis unavailable - fall through to generate without caching
            logger.warning(
                f"{log_label}: Redis unavailable ({e}), generating without cache"
            )

    # Generate without Redis caching
    payload = generator_fn(db, limit)
    timestamp_str = _current_timestamp_str(db)
    return _wrap_cache_payload(payload, timestamp_str)


def _maybe_refresh_cache_entry(
    *,
    cache_key: str,
    lock_key: str,
    cached_entry: dict[str, Any],
    db: Session,
    generator_fn,
    limit: Optional[int],
    log_label: str,
    metadata: Optional[dict[str, Any]] = None,
) -> tuple[Optional[dict[str, Any]], dict[str, Any], str]:
    metadata = dict(metadata or {})
    redis_client = get_redis_client()
    if redis_client is None:
        return None, metadata, "STALE"

    lock = Lock(redis_client, lock_key, timeout=300, blocking_timeout=0)
    try:
        with lock:
            db_start = time.perf_counter()
            current_timestamp_str = _current_timestamp_str(db)
            db_duration_ms = (time.perf_counter() - db_start) * 1000
            cached_timestamp = cached_entry.get("_data_timestamp")
            now_iso = datetime.utcnow().isoformat()

            if cached_timestamp == current_timestamp_str:
                metadata["last_validation"] = now_iso
                metadata["cache_version"] = CACHE_VERSION
                meta_duration_ms = _set_cache_metadata(cache_key, metadata)
                logger.info(
                    "%s: Data unchanged; validation timestamp updated (db_ms=%.2f, meta_ms=%.2f)",
                    log_label,
                    db_duration_ms,
                    meta_duration_ms,
                )
                return cached_entry, metadata, "REVALIDATED"

            regen_start = time.perf_counter()
            payload = generator_fn(db, limit)
            regen_duration_ms = (time.perf_counter() - regen_start) * 1000
            wrapper = _wrap_cache_payload(
                payload, current_timestamp_str, last_validation=now_iso
            )
            _write_cache_entry(cache_key, wrapper)
            metadata["last_validation"] = now_iso
            metadata["cache_version"] = CACHE_VERSION
            meta_duration_ms = _set_cache_metadata(cache_key, metadata)
            logger.info(
                "%s: Data changed; cache refreshed (db_ms=%.2f, regen_ms=%.2f, meta_ms=%.2f)",
                log_label,
                db_duration_ms,
                regen_duration_ms,
                meta_duration_ms,
            )
            return wrapper, metadata, "REFRESHED"

    except LockError:
        logger.info(f"{log_label}: Refresh already in progress; serving stale data")
        return None, metadata, "REFRESH_IN_PROGRESS"
    except (RedisConnectionError, Exception) as e:
        # Redis unavailable - serve stale data
        logger.warning(f"{log_label}: Redis unavailable ({e}); serving stale data")
        return None, metadata, "STALE"


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
    - Cached payload persists until the trig data actually changes
    - Revalidates at most once every 60 seconds
    - Serves stale content while a refresh is in progress
    - Supports ETag for HTTP 304 responses
    """
    params = {"limit": limit} if limit is not None else None
    cache_key = generate_cache_key(
        resource_type="trigs", subresource="geojson", params=params, version="v1"
    )
    lock_key = f"{cache_key}:lock"

    metadata = _get_cache_metadata(cache_key)
    cached_entry, _ = cache_get(cache_key)
    cached_value, cached_timestamp, legacy_last_validation = _extract_cached_payload(
        cached_entry
    )
    last_validation = metadata.get("last_validation") or legacy_last_validation

    cache_status = "HIT"
    if cached_value is None:
        cached_entry = _generate_and_cache_payload(
            cache_key=cache_key,
            lock_key=lock_key,
            db=db,
            generator_fn=_generate_geojson_payload,
            limit=limit,
            log_label="GeoJSON cache miss",
        )
        cached_value, cached_timestamp, legacy_last_validation = (
            _extract_cached_payload(cached_entry)
        )
        metadata = _get_cache_metadata(cache_key)
        last_validation = metadata.get("last_validation") or legacy_last_validation
        cache_status = "MISS"

    if cached_value is None:
        payload = _generate_geojson_data(db, limit)
        timestamp_str = _current_timestamp_str(db)
        etag = _build_etag(timestamp_str)
        from fastapi.responses import JSONResponse

        return JSONResponse(
            content=payload,
            headers={
                "ETag": etag,
                "Cache-Control": "public, max-age=60, stale-while-revalidate=300",
                "X-Cache-Status": "MISS-NO-CACHE",
                "X-Data-Timestamp": timestamp_str,
            },
        )

    now = datetime.utcnow()
    if_none_match = request.headers.get("If-None-Match")

    if cached_entry and _should_revalidate(last_validation, now):
        refreshed_entry, metadata, refresh_status = _maybe_refresh_cache_entry(
            cache_key=cache_key,
            lock_key=lock_key,
            cached_entry=cached_entry,
            db=db,
            generator_fn=_generate_geojson_payload,
            limit=limit,
            log_label="GeoJSON cache",
            metadata=metadata,
        )
        if refreshed_entry is not None:
            cached_entry = refreshed_entry
            cached_value, cached_timestamp, legacy_last_validation = (
                _extract_cached_payload(refreshed_entry)
            )
        last_validation = metadata.get("last_validation") or legacy_last_validation
        cache_status = refresh_status

    etag = _build_etag(cached_timestamp)

    if if_none_match == etag:
        from fastapi import Response

        return Response(
            status_code=304,
            headers={
                "ETag": etag,
                "Cache-Control": "public, max-age=60, stale-while-revalidate=300",
                "X-Cache-Status": "NOT-MODIFIED",
            },
        )

    from fastapi.responses import JSONResponse

    data_timestamp_header = _get_entry_timestamp(
        cached_entry if isinstance(cached_entry, dict) else None
    )

    return JSONResponse(
        content=cached_value,
        headers={
            "ETag": etag,
            "Cache-Control": "public, max-age=60, stale-while-revalidate=300",
            "X-Cache-Status": cache_status,
            "X-Data-Timestamp": data_timestamp_header,
        },
    )


@cached(resource_type="trig", ttl=86400, resource_id_param="trig_id")  # 24 hours
def _get_trig_cached(
    trig_id: int,
    include: Optional[str],
    db: Session,
):
    """Internal cached function for fetching trig data."""
    from api.services.grid_system import get_country_info_for_point

    trig = trig_crud.get_trig_by_id(db, trig_id=trig_id)
    if trig is None:
        raise HTTPException(status_code=404, detail="Trigpoint not found")

    # Build minimal response
    minimal_data = TrigMinimal.model_validate(trig).model_dump()

    # Add type information from relationship
    if trig.trig_type:
        minimal_data["type_code"] = trig.trig_type.code
        minimal_data["type_name"] = trig.trig_type.name
        if trig.trig_type.category:
            minimal_data["category_code"] = trig.trig_type.category.code
            minimal_data["category_name"] = trig.trig_type.category.name

    # Add grid system and country classification
    if trig.wgs_lat is not None and trig.wgs_long is not None:
        grid_system, _, country_name = get_country_info_for_point(
            db, float(trig.wgs_lat), float(trig.wgs_long)
        )
        minimal_data["grid_system"] = grid_system
        minimal_data["country_name"] = country_name

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
    from api.services.grid_system import get_country_info_for_point

    trig = trig_crud.get_trig_by_waypoint(db, waypoint=waypoint)
    if trig is None:
        raise HTTPException(status_code=404, detail="Trigpoint not found")

    minimal_data = TrigMinimal.model_validate(trig).model_dump()

    # Add type information from relationship
    if trig.trig_type:
        minimal_data["type_code"] = trig.trig_type.code
        minimal_data["type_name"] = trig.trig_type.name
        if trig.trig_type.category:
            minimal_data["category_code"] = trig.trig_type.category.code
            minimal_data["category_name"] = trig.trig_type.category.name

    # Add grid system and country classification
    if trig.wgs_lat is not None and trig.wgs_long is not None:
        grid_system, _, country_name = get_country_info_for_point(
            db, float(trig.wgs_lat), float(trig.wgs_long)
        )
        minimal_data["grid_system"] = grid_system
        minimal_data["country_name"] = country_name

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
        None, description="Comma-separated physical types to include (legacy)"
    ),
    types: Optional[str] = Query(
        None, description="Comma-separated type codes to include (e.g., 'HOTINE,FBM')"
    ),
    categories: Optional[str] = Query(
        None,
        description="Comma-separated category codes to include (e.g., 'PILLAR,FBM')",
    ),
    exclude_found: Optional[bool] = Query(
        False, description="Exclude trigpoints already logged by authenticated user"
    ),
    only_found: Optional[bool] = Query(
        False, description="Include only trigpoints logged by authenticated user"
    ),
    area_id: Optional[int] = Query(
        None, description="Filter to trigpoints within the specified area"
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
    - physical_types: Filter by physical type (legacy, e.g., "Pillar,Bolt,FBM")
    - types: Filter by type code (e.g., "HOTINE,FBM,BOLT")
    - categories: Filter by category code (e.g., "PILLAR,FBM,SURVEY_MARK")
    - exclude_found: Exclude trigpoints the user has already logged (requires authentication)
    - only_found: Include only trigpoints the user has logged (requires authentication)
    - area_id: Filter to trigpoints within a specific geographic area

    Always excludes soft-deleted records (status_id >= 90).
    """
    # Record trig search metric
    metrics = get_metrics_collector()
    if metrics:
        search_type = "nearby" if (lat and lon and max_km) else "general"
        metrics.record_trig_search(search_type)

    # Parse physical types (legacy)
    physical_types_list = None
    if physical_types:
        physical_types_list = [
            pt.strip() for pt in physical_types.split(",") if pt.strip()
        ]

    # Parse type codes (new system)
    type_codes_list = None
    if types:
        type_codes_list = [t.strip() for t in types.split(",") if t.strip()]

    # Parse category codes (new system)
    category_codes_list = None
    if categories:
        category_codes_list = [c.strip() for c in categories.split(",") if c.strip()]

    # Get user ID for exclude_found filter
    exclude_found_by_user_id = None
    if exclude_found and current_user:
        exclude_found_by_user_id = int(current_user.id)

    # Get user ID for only_found filter
    only_found_by_user_id = None
    if only_found and current_user:
        only_found_by_user_id = int(current_user.id)

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
        type_codes=type_codes_list,
        category_codes=category_codes_list,
        exclude_found_by_user_id=exclude_found_by_user_id,
        only_found_by_user_id=only_found_by_user_id,
        exclude_soft_deleted=True,  # Always exclude status_id >= 90
        area_id=area_id,
    )

    total = trig_crud.count_trigs_filtered(
        db,
        name=name,
        county=county,
        center_lat=lat,
        center_lon=lon,
        max_km=max_km,
        physical_types=physical_types_list,
        type_codes=type_codes_list,
        category_codes=category_codes_list,
        exclude_found_by_user_id=exclude_found_by_user_id,
        only_found_by_user_id=only_found_by_user_id,
        exclude_soft_deleted=True,  # Always exclude status_id >= 90
        area_id=area_id,
    )

    # serialise with type information
    items_serialized = []
    for trig in items:
        data = TrigMinimal.model_validate(trig).model_dump()
        # Add type information from relationship
        if trig.trig_type:
            data["type_code"] = trig.trig_type.code
            data["type_name"] = trig.trig_type.name
            if trig.trig_type.category:
                data["category_code"] = trig.trig_type.category.code
                data["category_name"] = trig.trig_type.category.name
        items_serialized.append(data)

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
    if types:
        params.append(f"types={types}")
    if categories:
        params.append(f"categories={categories}")
    if exclude_found:
        params.append("exclude_found=true")
    if only_found:
        params.append("only_found=true")
    if area_id is not None:
        params.append(f"area_id={area_id}")
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
                            log_id=int(p.tlog_id) if p.tlog_id is not None else 0,
                            user_id=(
                                int(orig.user_id) if orig.user_id is not None else 0
                            ),
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
